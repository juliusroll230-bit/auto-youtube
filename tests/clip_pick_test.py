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

# Content-Rewards-Clips (Kampagne mit program) dürfen nie automatisch auf einem Sendeplatz laufen,
# weil der Link 30 Minuten nach dem Posten eingereicht werden muss.
_camps = [{"id": "cr", "program": "96d61823", "clips": [{"n": 1, "status": "freigegeben"}]},
          {"id": "frei", "clips": [{"n": 1, "status": "freigegeben"}]}]
clips.all_campaigns = lambda: _camps
clips.clip_path = lambda c, clip: os.path.abspath(__file__)
assert [c["id"] for c, _ in clips.ready_clips(auto=True)] == ["frei"]
_camps.pop()
assert clips.choose_for_slot("2026-11-07-9", [9], 2, [], scripts_left=False) is None
print("ok: Content-Rewards-Clips werden nicht automatisch gepostet")

# Bewertung: ganzer Gedanke und Informationsdichte (Ideen aus AutoClip, selbst geschrieben)
full = clips.sentences(words("Warum scheitern Firmen an Autos? Weil Fabriken Milliarden kosten.", 0))
cut = clips.sentences(words("und dann haben wir halt so gemacht", 0))
assert clips.completeness_points(full) > clips.completeness_points(cut)
rich = clips.sentences(words("Tesla produziert Batterien günstiger durch Gigafabriken in Nevada.", 0))
thin = clips.sentences(words("ja das ist auch so und das ist dann halt so ja", 0))
assert clips.density_points(rich) > clips.density_points(thin)
print("ok: Bewertung")
