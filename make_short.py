"""Erzeugt vertikale YouTube Shorts (1080x1920) aus einem Skript.

Aufruf:  python3 make_short.py skripte.json out/   (Datei mit einer Liste oder einem einzelnen Skript)
Braucht: ffmpeg, pillow, numpy, piper-tts und das Piper-Modell de_DE-thorsten-high.
"""
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np
from piper import PiperVoice, SynthesisConfig
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
PAUSE = 0.18      # Sekunden Stille nach jedem Satz (kurz halten: Pausen kosten Zuschauer)
SPEED = 0.88      # Sprechtempo der Stimme (kleiner = schneller)
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("TTS_MODEL_DIR", os.path.join(HERE, "models", "vits-piper-de_DE-thorsten-high"))
FONT_BOLD = os.path.join(HERE, "fonts", "InterDisplay-Black.otf")
FONT_SEMI = os.path.join(HERE, "fonts", "InterDisplay-SemiBold.otf")
FONT_EMOJI = os.path.join(HERE, "fonts", "NotoColorEmoji.ttf")


def load_tts():
    return PiperVoice.load(f"{MODEL_DIR}/de_DE-thorsten-high.onnx")


def synthesize(tts, segments, wav_path, seed=0):
    """Spricht alle Sätze ein, legt Musik und Effekte darunter und gibt Start/Ende jedes Satzes zurück."""
    import audio

    chunks, timings, t = [], [], 0.0
    rate = tts.config.sample_rate
    for seg in segments:
        cfg = SynthesisConfig(length_scale=SPEED)
        samples = np.concatenate([c.audio_float_array for c in tts.synthesize(seg["text"], syn_config=cfg)])
        dur = len(samples) / rate
        timings.append((t, t + dur))
        chunks += [samples, np.zeros(int(PAUSE * rate), dtype=np.float32)]
        t += dur + PAUSE
    tail = np.zeros(int(0.6 * rate), dtype=np.float32)  # kurzer Ausklang
    voice = np.concatenate(chunks + [tail])
    track = audio.mix(voice, rate, [s for s, _ in timings[1:]], seed)
    pcm = (np.clip(track, -1, 1) * 32767).astype(np.int16)
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm.tobytes())
    return timings, t


def caption_chunks(text, start, end, max_words=3):
    """Teilt einen Satz in kurze Untertitel. Zeit wird nach Zeichenlänge auf die Wörter verteilt.

    Gibt je Untertitel (start, ende, [(wort, wort_start, wort_ende), ...]) zurück.
    """
    words = text.split()
    weight = [len(w) + 2 for w in words]  # +2: auch kurze Wörter brauchen etwas Zeit
    total = sum(weight)
    timed, t = [], start
    for w, k in zip(words, weight):
        d = (end - start) * k / total
        timed.append((w, t, t + d))
        t += d
    groups, cur = [], []
    for item in timed:
        cur.append(item)
        if len(cur) >= max_words or item[0][-1] in ".,?!:":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return [(g[0][1], g[-1][2], g) for g in groups]


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def make_background(c1, c2):
    """Großer diagonaler Farbverlauf, aus dem pro Frame ein Ausschnitt genommen wird."""
    bw, bh = W + 400, H + 800
    y = np.linspace(0, 1, bh)[:, None]
    x = np.linspace(0, 1, bw)[None, :]
    t = (0.5 + 0.5 * np.sin((y * 1.6 + x * 0.6) * math.pi))[..., None]
    a, b = np.array(hex_rgb(c1)), np.array(hex_rgb(c2))
    return Image.fromarray((a * (1 - t) + b * t).astype(np.uint8), "RGB")


def soft_blob(size, color, alpha):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((size * 0.2, size * 0.2, size * 0.8, size * 0.8), fill=color + (alpha,))
    return img.filter(ImageFilter.GaussianBlur(size * 0.12))


def render_emoji(ch, size):
    font = ImageFont.truetype(FONT_EMOJI, 109)
    img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((80, 80), ch, font=font, embedded_color=True, anchor="mm")
    img = img.crop(img.getbbox() or (0, 0, 160, 160))
    return img.resize((size, int(size * img.height / img.width)), Image.LANCZOS)


_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def render_caption(words, active, accent):
    """Untertitel als Bild, Wort für Wort: Das gerade gesprochene Wort ist größer und farbig.

    words: Liste der Wörter, active: Index des gesprochenen Worts (oder -1).
    """
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    up = [w.upper() for w in words]
    size = 112
    while size > 60:
        f, big = font(FONT_BOLD, size), font(FONT_BOLD, int(size * 1.14))
        space = probe.textlength(" ", font=f) * 1.1
        lines, cur, cur_w = [], [], 0.0
        for i, w in enumerate(up):
            ww = probe.textlength(w, font=big)  # Platz wie für das große Wort, damit nichts springt
            if cur and cur_w + space + ww > W - 170:
                lines.append(cur)
                cur, cur_w = [], 0.0
            cur.append((i, ww))
            cur_w += (space if len(cur) > 1 else 0) + ww
        lines.append(cur)
        if len(lines) <= 2 and all(sum(x[1] for x in ln) + space * (len(ln) - 1) <= W - 170 for ln in lines):
            break
        size -= 6
    f, big = font(FONT_BOLD, size), font(FONT_BOLD, int(size * 1.14))
    lh = int(size * 1.22)
    img = Image.new("RGBA", (W, lh * len(lines) + 60), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(img), ImageDraw.Draw(shadow)
    for row, ln in enumerate(lines):
        line_w = sum(x[1] for x in ln) + space * (len(ln) - 1)
        x = W / 2 - line_w / 2
        y = 30 + row * lh + lh / 2
        for i, ww in ln:
            cx = x + ww / 2
            is_num = any(c.isdigit() for c in up[i])
            on = i == active
            color = hex_rgb(accent) if (on or is_num) else (255, 255, 255)
            ds.text((cx + 6, y + 8), up[i], font=big if on else f, anchor="mm", fill=(0, 0, 0, 150))
            d.text((cx, y), up[i], font=big if on else f, anchor="mm", fill=color,
                   stroke_width=11 if on else 10, stroke_fill=(12, 12, 20))
            x += ww + space
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    shadow.alpha_composite(img)
    return shadow


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def scaled(img, s):
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


class Scene:
    """Zeichnet die Bilder eines Shorts. timings: Start/Ende jedes Satzes in Sekunden.

    Damit Zuschauer dranbleiben, ist immer etwas in Bewegung:
    - Kamera zoomt langsam hinein und macht bei jedem neuen Satz einen kurzen Stoß mit Wackeln
    - kurzer heller Blitz als Übergang zwischen den Sätzen
    - Untertitel Wort für Wort, das gesprochene Wort ist größer und farbig
    - Emoji springt herein, wippt und dreht sich leicht, Partikel schweben nach oben
    """

    def __init__(self, spec, timings, total):
        self.timings, self.total = timings, total
        self.accent = spec["accent"]
        self.car = None
        if spec.get("style") == "car":
            from car_scene import CarScene
            self.car = CarScene(hex_rgb(spec["car_color"]), seed=len(spec["slug"]))
            self.blobs, self.emojis = [], []
        else:
            self.bg = make_background(*spec["colors"])
            self.blobs = [(soft_blob(520, hex_rgb(self.accent), 60), 0.11, 0.0),
                          (soft_blob(700, (255, 255, 255), 40), 0.07, 2.0),
                          (soft_blob(420, hex_rgb(spec["colors"][1]), 120), 0.15, 4.0)]
            self.emojis = [render_emoji(seg["emoji"], 400) for seg in spec["segments"]]
        self.cap_y = 640 if self.car else 1180
        self.bar_y = 280 if self.car else H - 210
        self.chunks = []
        for (s, e), seg in zip(timings, spec["segments"]):
            self.chunks += caption_chunks(seg["text"], s, e)
        if not self.chunks:
            raise ValueError("Skript ohne Text")
        self._cap_cache = {}
        self.label_font = font(FONT_SEMI, 46)
        self.label = spec["niche"].upper()
        rnd = np.random.default_rng(len(spec["slug"]))
        self.particles = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(40, 140), rnd.uniform(3, 9),
                           rnd.uniform(0, 6.28), int(rnd.uniform(50, 150))) for _ in range(26)]

    # --- Bausteine ---------------------------------------------------------

    def caption(self, t):
        """Aktueller Untertitel als Bild plus Startzeit, oder None."""
        idx = next((i for i, c in enumerate(self.chunks) if c[0] <= t < c[1]), None)
        if idx is None:
            prev = [i for i, c in enumerate(self.chunks) if c[1] <= t]
            if not prev or t - self.chunks[prev[-1]][1] >= PAUSE:
                return None
            idx = prev[-1]
        start, _, words = self.chunks[idx]
        active = next((j for j, (_, ws, we) in enumerate(words) if ws <= t < we), -1)
        key = (idx, active)
        if key not in self._cap_cache:
            self._cap_cache = {k: v for k, v in self._cap_cache.items() if k[0] >= idx - 1}
            self._cap_cache[key] = render_caption([w for w, _, _ in words], active, self.accent)
        return self._cap_cache[key], start

    def segment_at(self, t):
        return next((i for i, (s, e) in enumerate(self.timings) if t < e + PAUSE), len(self.timings) - 1)

    def punch(self, t):
        """Stärke des Kamera-Stoßes: kurz nach jedem Satzanfang groß, dann schnell weg."""
        p = 0.0
        for i, (s, _) in enumerate(self.timings):
            if s <= t < s + 0.35:
                p = max(p, (1 - (t - s) / 0.35) ** 2 * (1.6 if i == 0 else 1.0))
        return p

    # --- Bild --------------------------------------------------------------

    def frame(self, t):
        if self.car:
            frame = self.car.frame(t)
        else:
            ox = int(200 + 200 * math.sin(t * 0.35))
            oy = int(400 + 400 * math.sin(t * 0.22))
            frame = self.bg.crop((ox, oy, ox + W, oy + H)).convert("RGBA")
        for blob, speed, phase in self.blobs:
            bx = int(W / 2 + 380 * math.sin(t * speed * 6 + phase) - blob.width / 2)
            by = int(H / 2 + 700 * math.cos(t * speed * 4 + phase) - blob.height / 2)
            frame.paste(blob, (bx, by), blob)

        # Partikel, die langsam nach oben schweben
        d = ImageDraw.Draw(frame, "RGBA")
        for x0, y0, speed, r, ph, a in self.particles:
            y = (y0 - speed * t) % (H + 40) - 20
            x = x0 + 24 * math.sin(t * 0.8 + ph)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, a))

        # Emoji des aktuellen Satzes: springt herein, wippt und dreht sich leicht
        idx = self.segment_at(t)
        if self.emojis:
            since = t - self.timings[idx][0]
            pop = ease_out_back(min(1, max(0, since / 0.32))) if since >= 0 else 1
            em = scaled(self.emojis[idx], max(0.05, pop * (1 + 0.04 * math.sin(t * 5))))
            em = em.rotate(7 * math.sin(t * 2.6), resample=Image.BICUBIC, expand=True)
            bob = int(22 * math.sin(t * 2.2))
            frame.alpha_composite(em, (int(W / 2 - em.width / 2), int(620 - em.height / 2 + bob)))

        # Untertitel Wort für Wort
        cap = self.caption(t)
        if cap:
            img, start = cap
            k = min(1, (t - start) / 0.14)
            ci = scaled(img, 0.82 + 0.18 * ease_out_back(k))
            frame.alpha_composite(ci, (int(W / 2 - ci.width / 2), int(self.cap_y - ci.height / 2)))

        # Kamera: langsamer Zoom über das ganze Video plus Stoß mit Wackeln bei jedem Satz
        p = self.punch(t)
        zoom = 1.0 + 0.06 * (t / self.total) + 0.07 * p
        shake_x = p * 14 * math.sin(t * 61)
        shake_y = p * 10 * math.cos(t * 47)
        cw, ch = W / zoom, H / zoom
        x0 = (W - cw) / 2 + shake_x
        y0 = (H - ch) / 2 + shake_y
        frame = frame.convert("RGB").resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

        # Heller Blitz als Übergang zwischen zwei Sätzen
        s = self.timings[idx][0]
        if idx > 0 and 0 <= t - s < 0.12:
            frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 255, 255)), 0.32 * (1 - (t - s) / 0.12))

        # Feste Elemente (bewegen sich nicht mit der Kamera): Themen-Label und Fortschrittsbalken
        d = ImageDraw.Draw(frame, "RGBA")
        tw = d.textlength(self.label, font=self.label_font)
        d.rounded_rectangle((W / 2 - tw / 2 - 36, 150, W / 2 + tw / 2 + 36, 236), radius=43, fill=(0, 0, 0, 120))
        d.text((W / 2, 193), self.label, font=self.label_font, anchor="mm", fill=(255, 255, 255))
        bar_y = self.bar_y
        d.rounded_rectangle((90, bar_y, W - 90, bar_y + 14), radius=7, fill=(255, 255, 255, 70))
        d.rounded_rectangle((90, bar_y, 90 + (W - 180) * min(1, t / self.total), bar_y + 14), radius=7,
                            fill=hex_rgb(self.accent))
        return frame


def estimated_timings(spec):
    """Grobe Satz-Zeiten ohne Sprachausgabe (für Vorschaubilder)."""
    t, out = 0.0, []
    for seg in spec["segments"]:
        dur = len(seg["text"].split()) / 2.8
        out.append((t, t + dur))
        t += dur + PAUSE
    return out, t


def render_thumbnail(spec, path, width=360):
    """Speichert ein Vorschaubild: der erste Satz, kurz nachdem er eingeblendet wurde."""
    timings, total = estimated_timings(spec)
    scene = Scene(spec, timings, total)
    img = scene.frame(0.9)
    img.resize((width, int(width * H / W)), Image.LANCZOS).save(path, "JPEG", quality=84)


def build_video(spec, out_dir, tts):
    os.makedirs(out_dir, exist_ok=True)
    wav = os.path.join(out_dir, f"{spec['slug']}.wav")
    mp4 = os.path.join(out_dir, f"{spec['slug']}.mp4")
    timings, total = synthesize(tts, spec["segments"], wav, seed=sum(map(ord, spec["slug"])))
    total += 0.6
    scene = Scene(spec, timings, total)

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-af", "apad", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4,
    ], stdin=subprocess.PIPE)
    for f in range(int(total * FPS)):
        ff.stdin.write(scene.frame(f / FPS).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg konnte das Video nicht erstellen")
    os.remove(wav)
    return mp4, total


def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else None
    tts = load_tts()
    data = json.load(open(src, encoding="utf-8"))
    for spec in data if isinstance(data, list) else [data]:
        if only and spec["slug"] != only:
            continue
        path, dur = build_video(spec, out_dir, tts)
        print(f"{path}  {dur:.1f}s")


if __name__ == "__main__":
    main()
