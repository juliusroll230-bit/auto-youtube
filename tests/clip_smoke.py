"""Schnelltest für den Video-Clipper: KI-Stimme + Testbild als "langes Video", dann echt mitschreiben und schneiden.

Läuft in GitHub Actions im fertigen Docker-Image (dort ist das Whisper-Modell eingebaut):
    python tests/clip_smoke.py
"""
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="clip-smoke-")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agents  # noqa: E402
import clips  # noqa: E402
import make_short  # noqa: E402
import store  # noqa: E402
from piper import SynthesisConfig  # noqa: E402

SENTENCES = [
    "Hallo und willkommen zurück auf dem Kanal.",
    "Warum sparen die meisten Menschen eigentlich falsch?",
    "Der größte Fehler ist, dass sie erst am Ende des Monats sparen.",
    "Stell dir vor, du legst jeden Monat zuerst hundert Euro zur Seite.",
    "Nach zehn Jahren hast du über fünfzehntausend Euro.",
    "Jetzt kurz zu etwas anderem.",
    "Wusstest du, dass eine neue Gewohnheit sechsundsechzig Tage braucht?",
    "Nicht einundzwanzig, wie alle sagen.",
    "Am Ende zählt nur, dass du dranbleibst.",
]


def make_video(path):
    tts = make_short.load_tts()
    rate = tts.config.sample_rate
    parts = [np.zeros(int(0.5 * rate), np.float32)]
    for sent in SENTENCES:
        parts.append(np.concatenate([c.audio_float_array for c in tts.synthesize(sent, syn_config=SynthesisConfig())]))
        parts.append(np.zeros(int(0.6 * rate), np.float32))
    audio = np.concatenate(parts)
    wav = path + ".wav"
    with wave.open(wav, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    dur = len(audio) / rate
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30:duration={dur:.2f}",
                    "-i", wav, "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", path], check=True)
    os.remove(wav)
    return dur


def main():
    store.init()
    src = os.path.join(os.environ["DATA_DIR"], "Test Podcast.mp4")
    dur = make_video(src)
    print("Testvideo:", round(dur, 1), "Sekunden")
    c = clips.add_file(src, "upload", rights=True, name="Test Podcast")
    assert c["status"] == "wartet", c["status"]
    settings = agents.settings({"agents": {"clipper": {"min_len": 8, "max_len": 25, "clips": 2}}})["clipper"]
    c = clips.process(c["id"], settings, task=print)
    with open(clips.camp_dir(c["id"], "transcript.json"), encoding="utf-8") as f:
        words = json.load(f)["words"]
    heard = " ".join(w["w"] for w in words).lower()
    print("Mitschrift:", heard[:200])
    assert len(words) > 30, "Zu wenig erkannt"
    assert "sparen" in heard or "gewohnheit" in heard, "Mitschrift passt nicht zum Text"
    assert c["status"] == "fertig" and c["clips"], c
    for x in c["clips"]:
        size = os.path.getsize(clips.clip_path(c, x))
        assert size > 100_000, (x["n"], size)
        assert os.path.getsize(clips.clip_path(c, x, "jpg")) > 5_000
        print(f"Clip {x['n']}: {x['duration']} s, Hook {x['score']}, „{x['title']}“")
    print("Clipper ok")


if __name__ == "__main__":
    main()
