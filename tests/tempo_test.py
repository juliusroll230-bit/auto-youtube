"""Tempo "schnell" (seit 21.11.2026, Julius' Vorbild-Reels): 2 von 15 Cartoon-Shorts mit Schnitt alle ca. 1,3 s."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio
import cartoon
import learn
import make_short

day = [learn.choose_tempo(n, {}) for n in range(15)]
assert day.count("schnell") == 2 and day.count("normal") == 13, day
assert [learn.choose_layout(n, {}) for n in range(15)][7] == "spannung" and day[7] == "normal"   # nicht auf demselben Platz
fs = {"tempo": {"normal": {"score": 1000, "videos": 20}, "schnell": {"score": 1400, "videos": 6}}}
assert [learn.choose_tempo(n, fs) for n in range(15)].count("schnell") == 6
fs["tempo"]["schnell"]["score"] = 1200   # nur 20 % vorn: bleibt beim Test
assert [learn.choose_tempo(n, fs) for n in range(15)].count("schnell") == 2

spec = {"stil": "cartoon", "niche": "Erklären", "title": "X", "segments": [{"text": "a b"}]}
assert learn.features(spec, {"tempo": "schnell"})["tempo"] == "schnell"
assert learn.features({**spec, "stil": None}, {"tempo": "schnell"})["tempo"] is None
assert "tempo" in learn.FEATURE_NAMES

timings = [(0.0, 2.6), (2.6, 4.0), (4.0, 8.1)]
cuts = make_short.fast_cuts(timings, 8.5)
pts = sorted([0.0, 2.6, 4.0, 8.5] + cuts)
gaps = [b - a for a, b in zip(pts, pts[1:])]
assert cuts and min(gaps) >= 0.7 and max(gaps) < 1.9, (cuts, gaps)   # alle 0,7 bis 1,9 s ein Schnitt

s = audio.snap(22050)
assert 0 < len(s) < 22050 and abs(s).max() <= 1.0
v = audio.mix(make_short.np.zeros(22050 * 3, dtype="float32"), 22050, [1.0], 1, snaps=[0.5, 1.6])
assert len(v) == 22050 * 3

assert cartoon.fast({"tempo": "schnell"}) and not cartoon.fast({"tempo": "schnell", "laenge": "lang"})
assert cartoon.validate({"tempo": "turbo", "segments": []})
w = cartoon.word_times([{"text": "Ein *großer* Hund."}], [(0.0, 1.5)])
assert [x["k"] for x in w] == [False, True, False] and w[1]["w"] == "großer"
print("ok")
