"""Spannung (seit 20.11.2026): pro 15 Cartoon-Shorts 1 Spannung, der Rest normal. Kein Split-Screen in Shorts."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio
import entspannung
import learn

day = [learn.choose_layout(n, {}) for n in range(15)]
assert day.count("spannung") == 1 and day.count("normal") == 14 and "split" not in day, day
assert [learn.choose_layout(n, {}) for n in range(15, 30)] == day

fs = {"aufbau": {"normal": {"score": 1000, "videos": 20}, "spannung": {"score": 1400, "videos": 5}}}
assert [learn.choose_layout(n, fs) for n in range(15)].count("spannung") == 3
fs["aufbau"]["spannung"]["score"] = 1200   # nur 20 % vorn: bleibt beim Test
assert [learn.choose_layout(n, fs) for n in range(15)].count("spannung") == 1
fs["aufbau"]["spannung"] = {"score": 5000, "videos": 4}   # zu wenige Videos
assert learn.layout_winner(fs) is None

spec = {"stil": "cartoon", "niche": "Horror", "title": "X", "segments": [{"text": "a b"}]}
assert learn.features(spec, {"aufbau": "spannung"})["aufbau"] == "spannung"
assert learn.features({**spec, "stil": None}, {"aufbau": "spannung"})["aufbau"] is None

b = audio.tension_beats(15.0)
assert b and b[-1] < 15.0 and (b[1] - b[0]) > (b[-1] - b[-2])
assert audio.tension_beats(None) == [] and audio.tension_beats(1.0) == []

for kind in ("regen", "feuer", "pendel"):   # Grund-Geräusche der Entspannungsvideos
    a = audio.ambience(kind, 4.0, 22050, 1, loop=True)
    assert len(a) == 88200 and abs(a).max() <= 1.0
assert entspannung.dauer_text(120) == "2 Stunden" and entspannung.dauer_text(90) == "90 Minuten"
print("ok")
