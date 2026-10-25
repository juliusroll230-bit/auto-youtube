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
from PIL import Image, ImageDraw, ImageFont

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
        text = seg["text"].replace("*", "")
        samples = np.concatenate([c.audio_float_array for c in tts.synthesize(text, syn_config=cfg)])
        dur = len(samples) / rate
        timings.append((t, t + dur))
        chunks += [samples, np.zeros(int(PAUSE * rate), dtype=np.float32)]
        t += dur + PAUSE
    tail = np.zeros(int(0.6 * rate), dtype=np.float32)  # kurzer Ausklang
    voice = np.concatenate(chunks + [tail])
    track = audio.mix(voice, rate, [s for s, _ in timings[1:]], seed, pops=number_hits(segments, timings))
    pcm = (np.clip(track, -1, 1) * 32767).astype(np.int16)
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm.tobytes())
    return timings, t


def number_hits(segments, timings, gap=0.6):
    """Zeitpunkte, an denen eine Zahl gesprochen wird (für Kamera-Stoß und Klick-Ton)."""
    hits = []
    for (s, e), seg in zip(timings, segments):
        for _, _, words in caption_chunks(seg["text"], s, e):
            for w, ws, _, _ in words:
                if any(c.isdigit() for c in w) and ws - s > 0.4 and (not hits or ws - hits[-1] >= gap):
                    hits.append(ws)
    return hits


def caption_chunks(text, start, end, max_words=3):
    """Teilt einen Satz in kurze Untertitel. Zeit wird nach Zeichenlänge auf die Wörter verteilt.

    Gibt je Untertitel (start, ende, [(wort, wort_start, wort_ende, schluesselwort), ...]) zurück.
    Wörter mit *Sternchen* im Skript sind Schlüsselwörter und werden im Untertitel hervorgehoben.
    """
    import numerals

    raw = text.split()
    words = [w.replace("*", "") for w in raw]
    keys = [w.count("*") > 0 for w in raw]
    weight = [len(w) + 2 for w in words]  # +2: auch kurze Wörter brauchen etwas Zeit
    total = sum(weight)
    timed, t = [], start
    for w, key, k in zip(words, keys, weight):
        d = (end - start) * k / total
        timed.append((numerals.display_word(w), t, t + d, key))  # Zahlen als Ziffern anzeigen
        t += d
    # "1600 Meter" ist keine Jahreszahl: mit Punkt schreiben, wenn eine Einheit folgt
    for i in range(len(timed) - 1):
        w, nxt = timed[i][0], words[i + 1]
        if w.isdigit() and len(w) == 4 and nxt[:1].isupper():
            timed[i] = (f"{w[0]}.{w[1:]}",) + timed[i][1:]
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


class Scene:
    """Zeichnet die Bilder eines Shorts. timings: Start/Ende jedes Satzes in Sekunden.

    Damit Zuschauer dranbleiben, ist immer etwas in Bewegung:
    - Hintergrund passend zum Thema, der sich bei jedem Satz verändert (themes.py, car_scene.py)
    - Kamera zoomt langsam hinein und macht bei jedem neuen Satz einen kurzen Stoß mit Wackeln
    - kurzer heller Blitz als Übergang zwischen den Sätzen
    - Untertitel: jedes Wort fliegt herein, das gesprochene Wort steht auf einem farbigen Kasten (motion.py)
    - Emoji auf leuchtendem Kreis mit kreisenden Funken
    - bei Zahlen ein Zähler mit Ring, der hochzählt und das Emoji ablöst
    """

    def __init__(self, spec, timings, total):
        import motion

        self.timings, self.total = timings, total
        self.accent = spec["accent"]
        self.car = None
        if spec.get("style") == "car":
            from car_scene import CarScene
            self.car = CarScene(hex_rgb(spec["car_color"]), seed=len(spec["slug"]), skies=len(timings))
            self.emojis = []
        else:
            import themes
            self.theme = themes.for_spec(spec, timings, total, PAUSE)
            self.emojis = [render_emoji(seg["emoji"], 400) for seg in spec["segments"]]
        self.cap_y = 640 if self.car else 1180
        self.bar_y = 280 if self.car else H - 210
        self.icon_y = 930 if self.car else 620
        self.chunks, self.numbers = [], []
        for (s, e), seg in zip(timings, spec["segments"]):
            chunks = caption_chunks(seg["text"], s, e)
            self.chunks += chunks
            self.numbers.append(motion.number_events([w[:3] for c in chunks for w in c[2]]))
        self.hits = number_hits(spec["segments"], timings)
        if not self.chunks:
            raise ValueError("Skript ohne Text")
        rgb = hex_rgb(self.accent)
        self.badge = motion.EmojiBadge(rgb)
        self.card = motion.NumberCard(rgb, FONT_BOLD, FONT_SEMI, scale=0.62 if self.car else 1.0)
        self._cap_cache = {}
        self.label_font = font(FONT_SEMI, 46)
        self.label = spec["niche"].upper()

    # --- Bausteine ---------------------------------------------------------

    def caption(self, t):
        """Aktueller Untertitel (motion.Caption), oder None."""
        import motion

        idx = next((i for i, c in enumerate(self.chunks) if c[0] <= t < c[1]), None)
        if idx is None:
            prev = [i for i, c in enumerate(self.chunks) if c[1] <= t]
            if not prev or t - self.chunks[prev[-1]][1] >= PAUSE:
                return None
            idx = prev[-1]
        if idx not in self._cap_cache:
            self._cap_cache = {k: v for k, v in self._cap_cache.items() if k >= idx - 1}
            self._cap_cache[idx] = motion.Caption(self.chunks[idx][2], hex_rgb(self.accent), FONT_BOLD)
        return self._cap_cache[idx]

    def segment_at(self, t):
        return next((i for i, (s, e) in enumerate(self.timings) if t < e + PAUSE), len(self.timings) - 1)

    def punch(self, t):
        """Stärke des Kamera-Stoßes: kurz nach jedem Satzanfang groß, dann schnell weg."""
        p = 0.0
        for i, (s, _) in enumerate(self.timings):
            if s <= t < s + 0.35:
                p = max(p, (1 - (t - s) / 0.35) ** 2 * (1.6 if i == 0 else 1.0))
        for s in self.hits:  # kleiner Stoß, wenn eine Zahl kommt
            if s <= t < s + 0.28:
                p = max(p, 0.75 * (1 - (t - s) / 0.28) ** 2)
        return p

    # --- Bild --------------------------------------------------------------

    def frame(self, t):
        idx = self.segment_at(t)
        if self.car:
            frame = self.car.frame(t, self.timings, PAUSE)
        else:
            frame = self.theme.frame(t)
        frame = frame.convert("RGBA")

        # Emoji des aktuellen Satzes, bei einer Zahl übernimmt der Zähler
        since = t - self.timings[idx][0]
        spoken = [ev for ev in self.numbers[idx] if ev[0] <= t]
        bob = 22 * math.sin(t * 2.2)
        if self.emojis:
            out = (t - spoken[0][0]) / 0.2 if spoken else 0.0
            self.badge.draw(frame, t, W / 2, self.icon_y + bob, self.emojis[idx], max(since, 0), out)
        if spoken:
            self.card.draw(frame, t, W / 2, self.icon_y + bob * 0.5, spoken[-1], appear=spoken[-1][0])

        # Untertitel: Wörter fliegen herein, das gesprochene Wort hat einen farbigen Kasten
        cap = self.caption(t)
        if cap:
            cap.draw(frame, t, self.cap_y)

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
