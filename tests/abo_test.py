"""Abo-Aufruf am Ende der Cartoon-Shorts (Test seit 22.11.2026): gesprochen / eingeblendet / ohne, gelernt nach Abos pro 1.000 Aufrufe."""
import datetime as dt
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio
import cartoon
import hookcheck
import learn
import make_short

# erst reihum, damit der Vergleich fair ist; beim Loop nie gesprochen
first = [learn.choose_abo(n, {}) for n in range(6)]
assert first.count("gesprochen") == first.count("eingeblendet") == first.count("ohne") == 2, first
assert "gesprochen" not in [learn.choose_abo(n, {}, loop=True) for n in range(6)]

# mit genug Abo-Zahlen: 3 von 4 die Variante mit den meisten Abos pro 1.000 Aufrufe
fs = {"abo": {"gesprochen": {"abo_1k": 4.0, "sn": 6}, "eingeblendet": {"abo_1k": 2.0, "sn": 6}, "ohne": {"abo_1k": 1.0, "sn": 6}}}
picks = [learn.choose_abo(n, fs) for n in range(8)]
assert picks.count("gesprochen") >= 6, picks
fs["abo"]["ohne"]["sn"] = 2   # zu wenig Daten: bleibt reihum
assert [learn.choose_abo(n, fs) for n in range(3)] == list(learn.ABO_MODES)

# Sätze: kurz, keine Gedankenstriche oder KI-Floskeln, je Typ mindestens 2, damit sie wechseln
for typ, lines in learn.ABO_LINES.items():
    assert len(lines) >= 2 and len(set(lines)) == len(lines), typ
    for line in lines:
        assert len(line.split()) <= 7 and "–" not in line and "—" not in line, line
        assert hookcheck.polish(line, "post") == line, line
spec = {"stil": "cartoon", "niche": "Horror", "title": "X", "segments": [{"text": "a b"}]}
assert learn.abo_lines(spec) == learn.ABO_LINES["Horror"]
assert learn.abo_lines({**spec, "niche": "Erklären", "title": "Was passiert, wenn"}) == learn.ABO_LINES["Erklärvideo"]

# Lern-Merkmal: nur neue Cartoon-Shorts, nicht lange Videos oder das Firmen-Spiel
f = learn.features(spec, {"abo": "gesprochen", "abo_text": "Noch eine Geschichte? Abonnier."})
assert f["abo"] == "gesprochen" and f["abo_text"] == "Noch eine Geschichte? Abonnier."
assert learn.features(spec, {"abo": "ohne"})["abo_text"] is None
assert learn.features({**spec, "laenge": "lang"}, {"abo": "gesprochen"})["abo"] is None
assert learn.features({**spec, "format": "firma"}, {"abo": "gesprochen"})["abo"] is None
assert learn.features(spec, {})["abo"] is None   # alte Videos zählen nicht mit
assert "abo" in learn.FEATURE_NAMES and "abo_text" in learn.FEATURE_NAMES

# Abos pro 1.000 Aufrufe aus YouTube Analytics
now = dt.datetime(2026, 11, 25, 12)
old = (now - dt.timedelta(days=2)).isoformat()
posted = [{"views": 1000, "a_views": 1000, "subs_gained": 5, "posted_at": old, "features": {"abo": "gesprochen"}},
          {"views": 1000, "a_views": 1000, "subs_gained": 1, "posted_at": old, "features": {"abo": "ohne"}},
          {"views": 500, "posted_at": old, "features": {"abo": "ohne"}}]   # noch keine Abo-Zahl
sc = learn.feature_scores(posted, now)
assert sc["abo"]["gesprochen"]["abo_1k"] == 5.0 and sc["abo"]["ohne"]["abo_1k"] == 1.0 and sc["abo"]["ohne"]["sn"] == 1
row = [r for r in learn.feature_summary(sc) if r["key"] == "abo"][0]
assert row["values"][0]["value"] == "gesprochen" and row["values"][0]["abo_1k"] == 5.0

# Bild: Knopf mit Satz; beim Loop nur eingeblendet; lange Videos nie
timings = [(0.0, 2.0), (2.0, 4.0), (4.0, 6.0), (6.0, 8.0)]
s2 = {**spec, "abo": "gesprochen", "abo_text": "Folge, wenn du dich traust."}
p = cartoon.abo_plan(s2, timings, 10.5, cta_at=8.06)
assert p["mode"] == "gesprochen" and p["start"] == 8.06 and p["text"] == "Folge, wenn du dich traust"
p = cartoon.abo_plan({**s2, "ende": "loop"}, timings, 8.35)
assert p["mode"] == "eingeblendet" and p["loop"] and 6.0 < p["start"] < 8.35
assert cartoon.abo_plan({**s2, "laenge": "lang"}, timings, 10.5) is None
assert cartoon.abo_plan({**s2, "abo": "ohne"}, timings, 10.5) is None
assert cartoon.validate({"abo": "laut", "segments": []})
assert make_short.badge_time(timings, 8.35) == 6.4 and make_short.badge_time(timings, 12.0) == round(12.0 - make_short.BADGE_SHOW, 3)

# Ton: Klick und Glocke, wenn der Knopf erscheint
v = audio.mix(make_short.np.zeros(22050 * 3, dtype="float32"), 22050, [1.0], 1, bell=2.0)
assert len(v) == 22050 * 3 and abs(v[int(2.0 * 22050):]).max() > 0
print("ok")
