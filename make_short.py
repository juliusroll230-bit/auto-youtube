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
PAUSE = 0.3  # Sekunden Stille nach jedem Satz
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("TTS_MODEL_DIR", os.path.join(HERE, "models", "vits-piper-de_DE-thorsten-high"))
FONT_BOLD = os.path.join(HERE, "fonts", "InterDisplay-Black.otf")
FONT_SEMI = os.path.join(HERE, "fonts", "InterDisplay-SemiBold.otf")
FONT_EMOJI = os.path.join(HERE, "fonts", "NotoColorEmoji.ttf")


def load_tts():
    return PiperVoice.load(f"{MODEL_DIR}/de_DE-thorsten-high.onnx")


def synthesize(tts, segments, wav_path):
    """Spricht alle Sätze ein und gibt Start/Ende jedes Satzes zurück."""
    chunks, timings, t = [], [], 0.0
    rate = None
    for seg in segments:
        cfg = SynthesisConfig(length_scale=0.92)
        samples = np.concatenate([c.audio_float_array for c in tts.synthesize(seg["text"], syn_config=cfg)])
        rate = tts.config.sample_rate
        dur = len(samples) / rate
        timings.append((t, t + dur))
        chunks += [samples, np.zeros(int(PAUSE * rate), dtype=np.float32)]
        t += dur + PAUSE
    pcm = (np.clip(np.concatenate(chunks), -1, 1) * 32767).astype(np.int16)
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm.tobytes())
    return timings, t


def caption_chunks(text, start, end, max_words=3):
    """Teilt einen Satz in kurze Untertitel und verteilt die Zeit nach Zeichenlänge."""
    words = text.split()
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w[-1] in ".,?!:":
            groups.append(" ".join(cur))
            cur = []
    if cur:
        groups.append(" ".join(cur))
    total = sum(len(g) for g in groups)
    out, t = [], start
    for g in groups:
        d = (end - start) * len(g) / total
        out.append((t, t + d, g))
        t += d
    return out


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


def render_caption(text, accent):
    """Untertitel als Bild: große weiße Schrift mit dunkler Kontur, Zahlen in Akzentfarbe."""
    font = ImageFont.truetype(FONT_BOLD, 104)
    lines, line = [], ""
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for word in text.split():
        test = (line + " " + word).strip()
        if probe.textlength(test.upper(), font=font) > W - 160 and line:
            lines.append(line)
            line = word
        else:
            line = test
    lines.append(line)
    # Zu lange Zeilen verkleinern, damit nichts aus dem Bild ragt
    widest = max(probe.textlength(ln.upper(), font=font) for ln in lines)
    size = max(60, min(104, int(104 * (W - 140) / widest)))
    font = ImageFont.truetype(FONT_BOLD, size)
    lh = int(size * 1.2)
    img = Image.new("RGBA", (W, lh * len(lines) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        has_digit = any(c.isdigit() for c in ln) or ln.lower().startswith("nummer")
        d.text((W // 2, 20 + i * lh + lh // 2), ln.upper(), font=font, anchor="mm",
               fill=hex_rgb(accent) if has_digit else (255, 255, 255),
               stroke_width=10, stroke_fill=(15, 15, 25))
    return img


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def scaled(img, s):
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)


def build_video(spec, out_dir, tts):
    os.makedirs(out_dir, exist_ok=True)
    wav = os.path.join(out_dir, f"{spec['slug']}.wav")
    mp4 = os.path.join(out_dir, f"{spec['slug']}.mp4")
    timings, total = synthesize(tts, spec["segments"], wav)
    total += 0.4

    car = None
    if spec.get("style") == "car":
        from car_scene import CarScene
        car = CarScene(hex_rgb(spec["car_color"]), seed=len(spec["slug"]))
    else:
        bg = make_background(*spec["colors"])
    accent = spec["accent"]
    blobs = [] if car else [(soft_blob(520, hex_rgb(accent), 60), 0.11, 0.0), (soft_blob(700, (255, 255, 255), 40), 0.07, 2.0),
             (soft_blob(420, hex_rgb(spec["colors"][1]), 120), 0.15, 4.0)]
    emojis = [render_emoji(s["emoji"], 400) for s in spec["segments"]] if not car else []
    cap_y = 640 if car else 1180
    bar_y = 280 if car else H - 210
    caps = []
    for (s, e), seg in zip(timings, spec["segments"]):
        for cs, ce, txt in caption_chunks(seg["text"], s, e):
            caps.append((cs, ce, render_caption(txt, accent)))
    if not caps:
        raise ValueError("Skript ohne Text")

    label_font = ImageFont.truetype(FONT_SEMI, 46)
    label = spec["niche"].upper()

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-af", "apad", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4,
    ], stdin=subprocess.PIPE)

    n = int(total * FPS)
    for f in range(n):
        t = f / FPS
        if car:
            frame = car.frame(t)
            blobs_now = []
        else:
            ox = int(200 + 200 * math.sin(t * 0.35))
            oy = int(400 + 400 * math.sin(t * 0.22))
            frame = bg.crop((ox, oy, ox + W, oy + H)).convert("RGBA")
            blobs_now = blobs

        for blob, speed, phase in blobs_now:
            bx = int(W / 2 + 380 * math.sin(t * speed * 6 + phase) - blob.width / 2)
            by = int(H / 2 + 700 * math.cos(t * speed * 4 + phase) - blob.height / 2)
            frame.paste(blob, (bx, by), blob)  # paste schneidet am Rand sauber ab

        d = ImageDraw.Draw(frame)
        # Nischen-Label oben
        tw = d.textlength(label, font=label_font)
        d.rounded_rectangle((W / 2 - tw / 2 - 36, 150, W / 2 + tw / 2 + 36, 236), radius=43, fill=(0, 0, 0, 110))
        d.text((W / 2, 193), label, font=label_font, anchor="mm", fill=(255, 255, 255))

        # Emoji des aktuellen Satzes mit Pop-in und leichtem Schweben
        idx = next((i for i, (s, e) in enumerate(timings) if t < e + PAUSE), len(timings) - 1)
        since = t - timings[idx][0]
        pop = ease_out_back(min(1, max(0, since / 0.35))) if since >= 0 else 1
        if emojis:
            em = scaled(emojis[idx], max(0.05, pop))
            bob = int(18 * math.sin(t * 2.2))
            frame.alpha_composite(em, (int(W / 2 - em.width / 2), int(620 - em.height / 2 + bob)))

        # Untertitel
        cap = next((c for c in caps if c[0] <= t < c[1]), None)
        if cap is None:
            prev = [c for c in caps if c[1] <= t]
            cap = prev[-1] if prev and t - prev[-1][1] < PAUSE else None
        if cap:
            k = min(1, (t - cap[0]) / 0.12)
            s = 0.85 + 0.15 * ease_out_back(k)
            ci = scaled(cap[2], s)
            frame.alpha_composite(ci, (int(W / 2 - ci.width / 2), int(cap_y - ci.height / 2)))

        # Fortschrittsbalken
        d.rounded_rectangle((90, bar_y, W - 90, bar_y + 14), radius=7, fill=(255, 255, 255, 70))
        d.rounded_rectangle((90, bar_y, 90 + (W - 180) * min(1, t / total), bar_y + 14), radius=7, fill=hex_rgb(accent))

        ff.stdin.write(frame.convert("RGB").tobytes())

    ff.stdin.close()
    ff.wait()
    os.remove(wav)
    meta = {k: spec[k] for k in ("title", "description", "tags")}
    with open(os.path.join(out_dir, f"{spec['slug']}.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
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
