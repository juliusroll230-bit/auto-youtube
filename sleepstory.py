"""Einschlaf-Geschichten für Quiet Corner (seit 24.11.2026, Julius' Entscheidung nach der Nischen-Recherche).

Eine ruhige englische Erzählstimme (Piper, en_GB northern_english_male, Lizenz frei) liest eine ausgedachte Geschichte vor,
darunter läuft leise die Quiet-Corner-Szene (Regen, Kamin, Café …). Nach der Geschichte läuft die Szene weiter, bis das Video
eine volle Stunde (oder mehr) lang ist. Die Geschichten liegen als JSON in `sleep/` (Feld text, Absätze mit Leerzeile).

Zum Testen: python sleepstory.py sleep/0001-....json ordner   (baut nur die Sprachspur als wav)
"""
import glob
import json
import os
import re
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STORY_DIR = os.path.join(HERE, "sleep")
MODEL_DIR = os.environ.get("SLEEP_VOICE_DIR", os.path.join(HERE, "models", "vits-piper-en_GB-northern_english_male-medium"))
MODEL = "en_GB-northern_english_male-medium.onnx"
LENGTH = 1.5          # >1 = langsamer sprechen
SENT_PAUSE = 1.2      # Sekunden nach jedem Satz
PARA_PAUSE = 3.4      # Sekunden nach jedem Absatz
LEAD_S = 12           # Sekunden Szene allein, bevor die Stimme beginnt
TAIL_S = 600          # mindestens so lange läuft die Szene nach der Geschichte weiter
BG_VOL = 0.22         # Lautstärke der Szene unter der Stimme (die Szene selbst ist schon auf 0,5 gemischt)
DISCLOSURE = "Narrated with a synthetic voice. The story is invented."


def stories():
    """Alle Geschichten aus sleep/ (sortiert nach Dateiname)."""
    out = []
    for p in sorted(glob.glob(os.path.join(STORY_DIR, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            if d.get("id") and d.get("title") and d.get("text"):
                out.append(d)
        except (OSError, ValueError):
            continue
    return out


def pick(used_ids):
    """Nächste Geschichte, die noch nie lief (None, wenn alle gelaufen sind). Doppelte Geschichten gibt es nie."""
    used = set(used_ids or [])
    return next((s for s in stories() if s["id"] not in used), None)


def _sentences(par):
    parts = re.split(r"(?<=[.!?])\s+", par.strip())
    return [p for p in parts if p]


def available():
    return os.path.exists(os.path.join(MODEL_DIR, MODEL))


def narrate(text, wav_path, rate_out=48000):
    """Sprechspur als wav (mono, rate_out). Gibt die Länge in Sekunden zurück."""
    from piper import PiperVoice, SynthesisConfig
    voice = PiperVoice.load(os.path.join(MODEL_DIR, MODEL))
    cfg = SynthesisConfig(length_scale=LENGTH, noise_scale=0.4, noise_w_scale=0.5)
    chunks, rate = [], 22050
    for par in [p for p in text.split("\n") if p.strip()]:
        for sent in _sentences(par):
            for c in voice.synthesize(sent, syn_config=cfg):
                chunks.append(np.frombuffer(c.audio_int16_bytes, dtype=np.int16))
                rate = c.sample_rate
            chunks.append(np.zeros(int(rate * SENT_PAUSE), dtype=np.int16))
        chunks.append(np.zeros(int(rate * (PARA_PAUSE - SENT_PAUSE)), dtype=np.int16))
    raw = wav_path + ".raw.wav"
    with wave.open(raw, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.concatenate(chunks).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-ar", str(rate_out), "-ac", "1", wav_path], check=True)
    os.remove(raw)
    with wave.open(wav_path) as w:
        return w.getnframes() / w.getframerate()


def total_minutes(narration_s, floor=60):
    """Länge des Videos in Minuten: Geschichte plus mindestens TAIL_S Szene, auf volle Stunden aufgerundet."""
    need = LEAD_S + narration_s + TAIL_S
    hours = max(1, int(-(-need // 3600)))
    return max(floor, hours * 60)


def mux(video_loop, scene_wav, narration_wav, minutes, out_mp4, rate=48000):
    """Schleifenbild + leise Szene + Stimme (nach LEAD_S) zu einem Video. Stimme laut, Szene leise, am Ende weiches Ausblenden."""
    total = minutes * 60
    delay = int(LEAD_S * 1000)
    # Szene leise (Julius 24.11.: „Hintergrund muss leiser sein“) und zusätzlich noch leiser, solange die Stimme spricht.
    fc = (f"[1:a]volume={BG_VOL}[bg];[2:a]adelay={delay}|{delay},volume=1.3,asplit=2[v][sc];"
          f"[bg][sc]sidechaincompress=threshold=0.01:ratio=10:attack=80:release=900:makeup=1[duck];"
          f"[duck][v]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={total - 8}:d=8[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", video_loop,
                    "-stream_loop", "-1", "-i", scene_wav, "-i", narration_wav, "-t", str(total),
                    "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-ar", str(rate), "-movflags", "+faststart", out_mp4], check=True)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        story = json.load(f)
    os.makedirs(sys.argv[2], exist_ok=True)
    out = os.path.join(sys.argv[2], story["id"] + ".wav")
    s = narrate(story["text"], out)
    print(f"{out}: {s / 60:.1f} Minuten Sprache, Video wäre {total_minutes(s)} Minuten lang")
