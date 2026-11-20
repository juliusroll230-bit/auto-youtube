"""Test Bildaufbau (seit 20.11.2026): pro 15 Cartoon-Shorts 1 Split-Screen und 1 Spannung, der Rest normal."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio
import learn

day = [learn.choose_layout(n, {}) for n in range(15)]
assert day.count("split") == 1 and day.count("spannung") == 1 and day.count("normal") == 13, day
assert [learn.choose_layout(n, {}) for n in range(15, 30)] == day

# Läuft Split-Screen klar besser (mind. 5 Videos je Seite, 30 % vorn), bekommt es 2 Plätze mehr, Spannung bleibt
fs = {"aufbau": {"normal": {"score": 1000, "videos": 20}, "split": {"score": 1400, "videos": 5},
                 "spannung": {"score": 900, "videos": 5}}}
day = [learn.choose_layout(n, fs) for n in range(15)]
assert day.count("split") == 3 and day.count("spannung") == 1, day
fs["aufbau"]["split"]["score"] = 1200   # nur 20 % vorn: bleibt beim Test
assert [learn.choose_layout(n, fs) for n in range(15)].count("split") == 1
fs["aufbau"]["split"] = {"score": 5000, "videos": 4}   # zu wenige Videos
assert learn.layout_winner(fs) is None

assert learn.choose_ambient({}, 0) in learn.AMBIENTS

spec = {"stil": "cartoon", "niche": "Horror", "title": "X", "segments": [{"text": "a b"}]}
f = learn.features(spec, {"aufbau": "split", "unten": "feuer"})
assert f["aufbau"] == "split" and f["unten"] == "feuer"
f = learn.features(spec, {"aufbau": "spannung"})
assert f["aufbau"] == "spannung" and f["unten"] is None
assert learn.features({**spec, "stil": None}, {"aufbau": "split"})["aufbau"] is None
assert "aufbau" in learn.FEATURE_NAMES and "unten" in learn.FEATURE_NAMES

# Herzschlag: beginnt ruhig, wird schneller, hört vor der Auflösung auf
b = audio.tension_beats(15.0)
assert b and b[-1] < 15.0 and (b[1] - b[0]) > (b[-1] - b[-2])
assert audio.tension_beats(None) == [] and audio.tension_beats(1.0) == []
for kind in learn.AMBIENTS:
    a = audio.ambience(kind, 2.0, 22050, 1)
    assert len(a) == 44100 and abs(a).max() <= 1.0
print("ok")
