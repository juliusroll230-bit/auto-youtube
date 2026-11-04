"""Prüft, dass der Clipper auch aus kurzen Videos (Trailern) genug Clips macht. Ohne Whisper/ffmpeg:
    python tests/clip_pick_test.py
"""
import os
import sys
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="clip-pick-"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import clips  # noqa: E402

S = {"clips": 5, "min_len": 20, "max_len": 45, "keywords": ""}


def words(text, t0, step=0.35):
    out = []
    for i, w in enumerate(text.split()):
        out.append({"w": w, "s": t0 + i * step, "e": t0 + i * step + 0.3})
    return out


def check(chosen, count, duration):
    assert len(chosen) == count, (len(chosen), chosen)
    for a, b in zip(chosen, chosen[1:]):
        assert a["end"] <= b["start"], ("Clips überlappen", a, b)
    assert all(0 <= c["start"] < c["end"] <= duration + 0.01 for c in chosen)


# 1) Trailer: 70 s, kaum Sprache, laute Stellen verteilt
dur = 70
rms = [0.2 + (0.8 if (k // 10) % 3 == 0 else 0) for k in range(dur * 2)]
sents = clips.sentences(words("Er kommt zurück.", 3) + words("Wer hält ihn auf?", 40))
check(clips.choose_parts(sents, rms, dur, S), 5, dur)

# 2) Trailer ohne Ton
check(clips.choose_parts([], [], 60, S), 5, 60)

# 3) Langes Video mit viel Sprache: Längen bleiben wie eingestellt
lo, hi = clips.clip_lengths(1800, 5, 20, 45)
assert (lo, hi) == (20, 45), (lo, hi)

# 4) Kurzes Video: kürzere Clips, aber nie unter MIN_CLIP
lo, hi = clips.clip_lengths(60, 5, 20, 45)
assert clips.MIN_CLIP <= hi <= 12 and lo <= hi, (lo, hi)
print("ok")
