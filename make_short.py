"""Erzeugt vertikale YouTube Shorts (1080x1920) aus einem Skript.

Aufruf:  python3 make_short.py skripte.json out/   (Datei mit einer Liste oder einem einzelnen Skript)
Braucht: ffmpeg, pillow, numpy, piper-tts und das Piper-Modell de_DE-thorsten-high.
"""
import json
import math
import re
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
TAIL = 0.35       # Stille nach dem letzten Satz: kurz, damit das Video sofort wieder von vorn läuft (Schleife)
# Ton: Brummen weg, Stimme gleichmäßiger (Kompressor), Lautheit auf YouTube-Standard (-14 LUFS)
AUDIO_FILTER = ("highpass=f=70,acompressor=threshold=0.1:ratio=3:attack=5:release=120:makeup=1.5,"
                "loudnorm=I=-14:TP=-1.5:LRA=8,aresample=48000,apad")
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("TTS_MODEL_DIR", os.path.join(HERE, "models", "vits-piper-de_DE-thorsten-high"))
FONT_BOLD = os.path.join(HERE, "fonts", "InterDisplay-Black.otf")
FONT_SEMI = os.path.join(HERE, "fonts", "InterDisplay-SemiBold.otf")
FONT_EMOJI = os.path.join(HERE, "fonts", "NotoColorEmoji.ttf")


# Stimmen für Cartoons: (Tonhöhe, Tempo-Faktor, Hall; Hall bleibt aus). Unter 1 heißt schneller: Cartoons sollen zügig erzählen,
# aber fröhliche Stimmen heller, ernste (unheimlich) kaum tiefer und etwas langsamer; zu tief klang wie ein Brummen.
# Welche am besten ankommt, lernt learn.choose_voice.
VOICES = {
    "froehlich": (1.05, 0.94, 0.0),   # heller und etwas flotter, für Erklärungen und Kurioses
    "klar": (1.02, 0.96, 0.0),        # normal, leicht aufgehellt
    "erzaehler": (0.97, 1.0, 0.0),    # Geschichten-Erzähler
    "unheimlich": (0.97, 1.13, 0.0),  # ernst und gelassen: kaum tiefer, deutlich ruhiger gesprochen, ohne Hall und ohne Brummen
    "freundlich": (1.0, 1.02, 0.0),   # warm und freundlich: Thorsten mit lächelnder Betonung (eigenes Modell, siehe unten)
    "erzaehlerin": (1.0, 1.06, 0.0),  # weibliche Erzählstimme (Kerstin), ruhig, für Geschichten
    "aufgeregt": (1.0, 0.86, 0.0),   # aufgeregt: etwas flotter, mit Betonung (19.11.2026, abends auf Julius' Wunsch etwas zurückgenommen)
}

# Stimmen mit eigenem Piper-Modell (alle CC0): Ordner, Datei, Sprecher-Nummer im Modell.
# Fehlt ein Modell (z. B. Bau ohne Download), spricht die normale Thorsten-Stimme.
VOICE_MODELS = {
    "freundlich": ("vits-piper-de_DE-thorsten_emotional-medium", "de_DE-thorsten_emotional-medium.onnx", 0),  # 0 = amused
    "erzaehlerin": ("vits-piper-de_DE-kerstin-low", "de_DE-kerstin-low.onnx", None),
    "aufgeregt": ("vits-piper-de_DE-thorsten_emotional-medium", "de_DE-thorsten_emotional-medium.onnx", 0),  # 0 = amused
}
# Mehr Schwankung in Tonhöhe und Tempo (noise_scale, noise_w_scale), damit die Stimme lebendiger klingt als Piper-Standard (0.667, 0.8)
VOICE_NOISE = {"aufgeregt": (0.5, 0.7)}  # niedrig = gleichmäßige Satzmelodie
_voice_models = {}


def voice_model(voice):
    """Eigenes Piper-Modell einer Stimme als (PiperVoice, Sprecher) oder None."""
    if voice not in VOICE_MODELS:
        return None
    if voice not in _voice_models:
        folder, name, speaker = VOICE_MODELS[voice]
        path = os.path.join(os.path.dirname(MODEL_DIR), folder, name)
        try:
            _voice_models[voice] = (PiperVoice.load(path), speaker) if os.path.exists(path) else None
        except Exception as e:  # noqa: BLE001  kaputtes Modell: lieber die normale Stimme
            print("Stimme", voice, "nicht ladbar:", e)
            _voice_models[voice] = None
    return _voice_models[voice]


def speak_piper(tts, text, voice=None, length_scale=1.0):
    """Ein Satz mit Piper, mit dem Modell der Stimme (falls eigenes), immer in der Abtastrate von tts."""
    rate = tts.config.sample_rate
    model = voice_model(voice)
    if model:
        m, speaker = model
        ns, nw = VOICE_NOISE.get(voice, (None, None))
        cfg = SynthesisConfig(length_scale=length_scale, speaker_id=speaker, noise_scale=ns, noise_w_scale=nw)
        x = np.concatenate([c.audio_float_array for c in m.synthesize(text, syn_config=cfg)])
        src = m.config.sample_rate
        if src != rate:
            x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * rate / src)), np.arange(len(x)), x).astype(np.float32)
        return x
    cfg = SynthesisConfig(length_scale=length_scale)
    return np.concatenate([c.audio_float_array for c in tts.synthesize(text, syn_config=cfg)])


LIVELY = ("aufgeregt",)   # Stimmen mit Satzmelodie: Satzteile, Betonung auf Schlüsselwörtern (gegen "trocken")


def _repitch(x, factor):
    """Tonhöhe um factor ändern (Strecken); die Dauer ändert sich mit und wird beim Sprechen eingerechnet."""
    if abs(factor - 1) < 1e-3:
        return x
    return np.interp(np.linspace(0, len(x) - 1, int(len(x) / factor)), np.arange(len(x)), x).astype(np.float32)


BASE = 0.94  # Grundtonhöhe der aufgeregten Stimme: tiefer als das Modell von selbst (gegen Quietschen)


def speak_lively(tts, text, voice, length_scale):
    """Spricht den Satz am Stück, gleichmäßig und gut verständlich (Julius 19.11.: nicht so hoch und runter).
    Etwas tiefer als das Modell von selbst, kein Springen zwischen Satzteilen, Betonung auf *Schlüsselwörtern* nur durch Lautstärke."""
    plain = text.replace("*", "")
    x = speak_piper(tts, plain, voice, length_scale=length_scale * BASE)
    return _repitch(x, BASE)


def voice_color(samples, rate, voice, pitch=None):
    """Macht die Stimme tiefer (durch Strecken) und legt bei Bedarf etwas Hall darunter."""
    p, _, echo = VOICES.get(voice or "klar", VOICES["klar"])
    pitch = p if pitch is None else pitch
    if pitch != 1.0:
        n = int(len(samples) / pitch)
        samples = np.interp(np.linspace(0, len(samples) - 1, n), np.arange(len(samples)), samples).astype(np.float32)
    if echo:
        out = np.copy(samples)
        for delay, gain in ((0.09, echo), (0.19, echo * 0.55), (0.31, echo * 0.3)):
            d = int(delay * rate)
            out[d:] += gain * samples[:-d]
        samples = out / max(1.0, np.abs(out).max() / 0.95)
    return samples.astype(np.float32)


def load_tts():
    return PiperVoice.load(f"{MODEL_DIR}/de_DE-thorsten-high.onnx")


def synthesize(tts, segments, wav_path, seed=0, speed=SPEED, voice=None, mood=None, pause=PAUSE, effects=None,
               layout=None):
    """Spricht alle Sätze ein, legt Musik und Effekte darunter und gibt Start/Ende jedes Satzes zurück.

    voice: Stimme aus VOICES (nur Cartoons), mood: Stimmung für die Musik (siehe audio.mix),
    effects: "stark" setzt Riser, Schlag und Musikpause auf die Auflösung (siehe accent_time).
    layout: "spannung" legt einen Herzschlag bis zur Auflösung darunter (Test).
    """
    import audio

    rate = tts.config.sample_rate
    pitch, slower, echo = VOICES.get(voice or "klar", VOICES["klar"])
    spoken = None
    import fishtts
    if isinstance(tts, fishtts.Voice):  # Fish Audio ist eingerichtet
        try:
            # Fish-Stimmen nicht verstellen, nur Tempo und Hall übernehmen
            spoken = [fishtts.speak(seg["text"].replace("*", ""), tts.key, tts.pick(mood, voice), rate,
                                    speed=SPEED / (speed * slower)) for seg in segments]
            if echo:
                spoken = [voice_color(x, rate, voice, pitch=1.0) for x in spoken]
            tts.error = None
        except Exception as e:  # Schlüssel, Guthaben oder Netz: dann spricht Piper
            tts.error = str(e)
            print("Fish Audio nicht erreichbar, nehme Piper:", e)
            spoken = None
    if spoken is None:
        spoken = []
        for seg in segments:
            # tiefer heißt beim Strecken auch länger, darum vorher entsprechend schneller sprechen
            text = seg["text"].replace("*", "")
            if voice in LIVELY:
                samples = speak_lively(tts, seg["text"], voice, length_scale=speed * slower * pitch)
            else:
                samples = speak_piper(tts, text, voice, length_scale=speed * slower * pitch)
            spoken.append(voice_color(samples, rate, voice) if voice else samples)

    chunks, timings, t = [], [], 0.0
    for samples in spoken:
        dur = len(samples) / rate
        timings.append((t, t + dur))
        chunks += [samples, np.zeros(int(pause * rate), dtype=np.float32)]
        t += dur + pause
    tail = np.zeros(int(TAIL * rate), dtype=np.float32)  # kurzer Ausklang
    voice_track = np.concatenate(chunks + [tail])
    track = audio.mix(voice_track, rate, [s for s, _ in timings[1:]], seed, pops=number_hits(segments, timings), mood=mood,
                      accent=accent_time(timings) if effects in ("stark", "voll") else None,
                      keys=key_hits(segments, timings) if effects == "voll" else (), sticker=effects == "voll",
                      beats=audio.tension_beats(accent_time(timings)) if layout == "spannung" else ())
    pcm = (np.clip(track, -1, 1) * 32767).astype(np.int16)
    with wave.open(wav_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(pcm.tobytes())
    return timings, t


def accent_time(timings):
    """Start des vorletzten Satzes: dort steht die Auflösung bzw. der Aha-Moment. Kurze Videos haben keinen."""
    return round(timings[-2][0], 3) if len(timings) >= 4 else None


def key_hits(segments, timings, gap=0.9, limit=5):
    """Zeitpunkte der *Sternchen*-Schlüsselwörter (Ton und kurzer Zoom bei stufe "voll"), höchstens `limit`."""
    hits = []
    for (s, e), seg in zip(timings, segments):
        for _, _, words in caption_chunks(seg["text"], s, e):
            for w, ws, _, key in words:
                if key and ws - s > 0.25 and (not hits or ws - hits[-1] >= gap):
                    hits.append(round(ws, 3))
    return hits[:limit]


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
    - Übergang zwischen den Sätzen (Blitz, Wischen, Zoom oder Glitch, je Video anders)
    - Untertitel: jedes Wort fliegt herein, das gesprochene Wort ist hervorgehoben (Stil je Video anders, motion.py)
    - Grafik zum Satz, wenn das Skript eine hat (Zeitstrahl, Vergleich, Liste, Anteil, großes Wort; visuals.py)
    - sonst bei Zahlen ein Zähler mit Ring, sonst das Emoji auf leuchtendem Kreis
    """

    TRANSITIONS = ("blitz", "wischen", "zoom", "glitch")

    def __init__(self, spec, timings, total, stock=None):
        import random

        import motion
        import visuals

        self.timings, self.total = timings, total
        self.accent = spec["accent"]
        self.car = None
        self.stock = stock  # echte Videoclips als Hintergrund (stock.py), sonst Animation
        has_emoji = all(seg.get("emoji") for seg in spec["segments"])
        self.emojis = [render_emoji(seg["emoji"], 400) for seg in spec["segments"]] if has_emoji else []
        if stock:
            pass
        elif spec.get("style") == "car":
            from car_scene import CarScene
            self.car = CarScene(hex_rgb(spec["car_color"]), seed=len(spec["slug"]), skies=len(timings))
            self.emojis = []
        else:
            import themes
            self.theme = themes.for_spec(spec, timings, total, PAUSE)
        self.cap_y = 560 if self.car else 1180
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
        # Jedes Video bekommt seinen eigenen Look, damit nicht alle gleich aussehen
        rng = random.Random(sum(map(ord, spec["slug"])) * 7919)
        self.cap_style = spec.get("caption_style") or rng.choice(motion.Caption.STYLES)
        self.transition = spec.get("transition") or rng.choice(self.TRANSITIONS)
        self.visuals = [visuals.build(seg.get("visual"), rgb, (FONT_BOLD, FONT_SEMI)) for seg in spec["segments"]]
        self.badge = motion.EmojiBadge(rgb)
        self.card = motion.NumberCard(rgb, FONT_BOLD, FONT_SEMI, scale=0.62 if self.car else 1.0)
        self._cap_cache = {}
        self.label_font = font(FONT_SEMI, 46)
        self.label = spec["niche"].upper()
        # Kopfzeile: der Titel steht vom ersten Bild an oben (macht neugierig, auch ohne Ton)
        self.headline = headline_sprite(spec.get("title", ""), rgb) if spec.get("kopfzeile") == "mit" else None
        if self.headline and self.car:
            self.bar_y = HEAD_Y + self.headline.height + 26
        elif self.headline:
            self.icon_y += 45  # Platz zwischen Kopfzeile und Grafik

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
            self._cap_cache[idx] = motion.Caption(self.chunks[idx][2], hex_rgb(self.accent), FONT_BOLD,
                                                  self.cap_style)
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

    def transition_fx(self, frame, dt):
        """Effekt kurz nach einem Satzwechsel. dt: Sekunden seit Satzanfang."""
        kind = self.transition
        if kind in ("blitz", "zoom") and 0 <= dt < 0.12:
            return Image.blend(frame, Image.new("RGB", (W, H), (255, 255, 255)), 0.32 * (1 - dt / 0.12))
        if kind == "wischen" and 0 <= dt < 0.3:
            # farbiges Band fegt schräg über das Bild
            k = ease_out_cubic(dt / 0.3)
            x = -700 + (W + 1400) * k
            d = ImageDraw.Draw(frame, "RGBA")
            acc = hex_rgb(self.accent)
            d.polygon([(x - 260, 0), (x + 40, 0), (x - 260 + 600, H), (x - 560 + 600, H)], fill=acc + (150,))
            d.polygon([(x + 70, 0), (x + 130, 0), (x + 130 + 600, H), (x + 70 + 600, H)], fill=(255, 255, 255, 120))
            return frame
        if kind == "glitch" and 0 <= dt < 0.16:
            # Farbkanäle verrutschen, Streifen springen zur Seite
            amt = int(26 * (1 - dt / 0.16))
            r, g, b = frame.split()
            r = r.transform(r.size, Image.AFFINE, (1, 0, -amt, 0, 1, 0))
            b = b.transform(b.size, Image.AFFINE, (1, 0, amt, 0, 1, 0))
            frame = Image.merge("RGB", (r, g, b))
            for i in range(4):
                y = int((H * ((i * 0.37 + dt * 3.1) % 1)))
                band = frame.crop((0, y, W, min(H, y + 50)))
                frame.paste(band, ((i % 2 * 2 - 1) * amt * 2, y))
            return frame
        return frame

    # --- Bild --------------------------------------------------------------

    def frame(self, t):
        idx = self.segment_at(t)
        if self.stock:
            frame = self.stock.frame(t)
        elif self.car:
            frame = self.car.frame(t, self.timings, PAUSE)
        else:
            frame = self.theme.frame(t)
        frame = frame.convert("RGBA")

        # Grafik zum Satz, sonst Emoji; bei einer Zahl übernimmt der Zähler
        since = t - self.timings[idx][0]
        spoken = [ev for ev in self.numbers[idx] if ev[0] <= t]
        bob = 22 * math.sin(t * 2.2)
        vis = self.visuals[idx]
        if vis:
            s, e = self.timings[idx]
            y = 950 if self.car else self.icon_y
            vis.draw(frame, t, s, e, W / 2, y + bob * 0.4, scale=0.8 if self.car else 1.0)
        elif self.emojis:
            out = (t - spoken[0][0]) / 0.2 if spoken else 0.0
            self.badge.draw(frame, t, W / 2, self.icon_y + bob, self.emojis[idx], max(since, 0), out)
        if spoken and not vis:
            self.card.draw(frame, t, W / 2, self.icon_y + bob * 0.5, spoken[-1], appear=spoken[-1][0])

        # Untertitel: Wörter fliegen herein, das gesprochene Wort hat einen farbigen Kasten
        cap = self.caption(t)
        if cap:
            cap.draw(frame, t, self.cap_y)

        # Kamera: langsamer Zoom über das ganze Video plus Stoß mit Wackeln bei jedem Satz
        p = self.punch(t)
        s = self.timings[idx][0]
        zoom = 1.0 + 0.06 * (t / self.total) + 0.07 * p
        if self.transition == "zoom" and idx > 0 and 0 <= t - s < 0.3:
            zoom += 0.22 * (1 - ease_out_cubic((t - s) / 0.3))
        shake_x = p * 14 * math.sin(t * 61)
        shake_y = p * 10 * math.cos(t * 47)
        cw, ch = W / zoom, H / zoom
        x0 = (W - cw) / 2 + shake_x
        y0 = (H - ch) / 2 + shake_y
        frame = frame.convert("RGB").resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

        # Übergang zwischen zwei Sätzen
        if idx > 0:
            frame = self.transition_fx(frame, t - s)

        # Feste Elemente (bewegen sich nicht mit der Kamera): Themen-Label und Fortschrittsbalken
        d = ImageDraw.Draw(frame, "RGBA")
        if self.headline:
            frame.paste(self.headline, (int(W / 2 - self.headline.width / 2), HEAD_Y), self.headline)
        else:
            tw = d.textlength(self.label, font=self.label_font)
            d.rounded_rectangle((W / 2 - tw / 2 - 36, 150, W / 2 + tw / 2 + 36, 236), radius=43, fill=(0, 0, 0, 120))
            d.text((W / 2, 193), self.label, font=self.label_font, anchor="mm", fill=(255, 255, 255))
        bar_y = self.bar_y
        d.rounded_rectangle((90, bar_y, W - 90, bar_y + 14), radius=7, fill=(255, 255, 255, 70))
        d.rounded_rectangle((90, bar_y, 90 + (W - 180) * min(1, t / self.total), bar_y + 14), radius=7,
                            fill=hex_rgb(self.accent))
        return frame


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


HEAD_Y = 140  # Oberkante der Kopfzeile (darüber liegen bei Shorts die Knöpfe der App)


def headline_sprite(title, accent):
    """Titel ohne Emoji als Kasten mit bis zu 2 Zeilen, oder None ohne Text."""
    import unicodedata

    text = "".join(c for c in title if unicodedata.category(c)[0] in "LNPZ" or unicodedata.category(c) in ("Sm", "Sc"))
    text = " ".join(text.split())
    if not text:
        return None
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    max_w = W - 220
    for size in (60, 56, 52, 48):
        f = font(FONT_BOLD, size)
        lines, cur = [], ""
        for w in text.split():
            test = (cur + " " + w).strip()
            if cur and probe.textlength(test, font=f) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = test
        lines.append(cur)
        if len(lines) <= 2 and all(probe.textlength(ln, font=f) <= max_w for ln in lines):
            break
    lines = lines[:2]
    lh = int(size * 1.2)
    pad_x, pad_y = 40, 24
    tw = max(probe.textlength(ln, font=f) for ln in lines)
    img = Image.new("RGBA", (int(tw + 2 * pad_x), lh * len(lines) + 2 * pad_y), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=30, fill=(0, 0, 0, 165),
                        outline=accent + (255,), width=4)
    for i, ln in enumerate(lines):
        d.text((img.width / 2, pad_y + lh * i + lh / 2), ln, font=f, anchor="mm", fill=(255, 255, 255))
    return img


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
    if spec.get("stil") == "cartoon":
        import cartoon
        return cartoon.render_thumbnail(spec, path, width)
    timings, total = estimated_timings(spec)
    scene = Scene(spec, timings, total)
    img = scene.frame(0.9)
    img.resize((width, int(width * H / W)), Image.LANCZOS).save(path, "JPEG", quality=84)


def build_video(spec, out_dir, tts, stock_key=None, info=None):
    """info (dict, optional) bekommt "stock": die Pexels-Clips, falls welche benutzt wurden."""
    if spec.get("stil") == "cartoon":  # Strichmännchen-Szenen aus dem Cartoon-Baukasten
        import cartoon
        return cartoon.build_video(spec, out_dir, tts, stock_key=stock_key, info=info)
    os.makedirs(out_dir, exist_ok=True)
    wav = os.path.join(out_dir, f"{spec['slug']}.wav")
    mp4 = os.path.join(out_dir, f"{spec['slug']}.mp4")
    timings, total = synthesize(tts, spec["segments"], wav, seed=sum(map(ord, spec["slug"])),
                                speed=spec.get("voice_speed") or SPEED)
    total += TAIL
    bg, credits = None, []
    if stock_key and spec.get("hintergrund") == "clips":
        import stock
        cache = os.path.join(os.path.dirname(os.path.abspath(out_dir)), "stock")
        bg, credits = stock.prepare(spec, timings, total, PAUSE, stock_key, cache)
    if info is not None:
        info["stock"] = credits
    scene = Scene(spec, timings, total, stock=bg)

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high", "-g", str(FPS * 2),
        "-pix_fmt", "yuv420p", "-af", AUDIO_FILTER, "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", mp4,
    ], stdin=subprocess.PIPE)
    for f in range(int(total * FPS)):
        ff.stdin.write(scene.frame(f / FPS).tobytes())
    ff.stdin.close()
    if bg:
        bg.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg konnte das Video nicht erstellen")
    os.remove(wav)
    return mp4, total, timings


def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else None
    tts = load_tts()
    data = json.load(open(src, encoding="utf-8"))
    for spec in data if isinstance(data, list) else [data]:
        if only and spec["slug"] != only:
            continue
        path, dur, _ = build_video(spec, out_dir, tts)
        print(f"{path}  {dur:.1f}s")


if __name__ == "__main__":
    main()
