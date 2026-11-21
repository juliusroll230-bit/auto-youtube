"""Entspannungskanal: Planung (einmal pro Tag ab Uhrzeit), Reihenfolge der Arten, Upload-Felder."""
import datetime as dt
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import entspannung

cfg = {"relax_token": "t", "relax_on": True, "relax_hour": 17, "relax_per_day": 1}
at = lambda h, d=20: dt.datetime(2026, 11, d, h, 30)
assert not entspannung.is_due(cfg, None, at(16))                      # zu früh
assert entspannung.is_due(cfg, None, at(17))                          # ab der Uhrzeit
assert entspannung.is_due(cfg, "2026-11-19", at(18))                  # gestern war das letzte
assert not entspannung.is_due(cfg, "2026-11-20", at(18))              # heute schon eins
assert not entspannung.is_due({**cfg, "relax_token": ""}, None, at(18))
assert not entspannung.is_due({**cfg, "relax_on": False}, None, at(18))
tried = at(18).replace(minute=0).isoformat()
assert not entspannung.is_due(cfg, None, at(18), tried)               # Versuch vor weniger als 1 Stunde
assert entspannung.is_due(cfg, None, at(19), tried)
assert entspannung.MINUTES == (180, 300, 480, 600)
# 2 Videos am Tag (Standard): ab 6 und ab 17 Uhr
c2 = {**cfg, "relax_per_day": 2}
assert entspannung.slots(c2) == [6, 17] and entspannung.slots({**cfg, "relax_per_day": 1}) == [17]
assert entspannung.slots({**cfg, "relax_per_day": 3}) == [6, 11, 17]
assert entspannung.is_due(c2, None, at(7))                                     # erster Platz offen
assert not entspannung.is_due(c2, "2026-11-20", at(7), None, 1)                # Morgen-Video schon da
assert entspannung.is_due(c2, "2026-11-20", at(18), None, 1)                   # Abend-Platz offen
assert not entspannung.is_due(c2, "2026-11-20", at(18), None, 2)               # beide da

# Quiet Corner: Ideen, Texte, Lernmodus
import audio
D = dt.date(2026, 11, 30)
assert len(entspannung.IDEAS) >= 15 and set(i["scene"] for i in entspannung.IDEAS) == set(entspannung.SCENES)
for i in entspannung.IDEAS:
    assert len(i["thumb"].split()) <= 3, i["thumb"]                      # Thumbnail höchstens 3 Wörter
    for m in entspannung.MINUTES:
        mt = entspannung.meta(i["id"], m, 3)
        assert len(mt["title"]) <= 100 and "Hours" in mt["title"] and "|" in mt["title"], mt["title"]
        assert 12 <= len(mt["tags"]) and sum(len(t) + 3 for t in mt["tags"]) <= 500 and i["sounds"].split()[0].lower() in mt["description"].lower()
        assert "—" not in mt["title"] + mt["description"] and "!" not in mt["title"]
    a = audio.soundscape(i["recipe"], 3.0, 22050, 1)
    assert len(a) == 66150 and 0 < abs(a).max() <= 1.0
assert "youtu.be/abc" in entspannung.teaser_meta("regen-fenster", 120, "abc")["description"]
# erst jede Szene und jede Länge einmal
seen, ups = [], []
for k in range(5):
    idea, mins = entspannung.choose(ups, "auto", D, k)
    seen.append(entspannung.IDEA[idea]["scene"])
    ups.append({"idea": idea, "scene": entspannung.IDEA[idea]["scene"], "minutes": mins, "at": "2026-11-01", "views": 10})
assert sorted(seen) == sorted(entspannung.SCENES) and {u["minutes"] for u in ups} >= {180, 300, 480, 600}
assert entspannung.choose(ups, "300", D, 9)[1] == 300                     # feste Länge
assert entspannung.choose(ups, "120", D, 9)[1] in entspannung.MINUTES     # alte Länge -> automatisch
# danach meist die Szene mit den meisten Aufrufen pro Tag
ups = [{**u, "views": 5000 if u["scene"] == "cafe" else 50} for u in ups]
ups += [{**u, "at": "2026-11-10"} for u in ups]
picks = [entspannung.IDEA[entspannung.choose(ups, "auto", D, k)[0]]["scene"] for k in range(40)]
assert 20 <= picks.count("cafe") <= 38, picks.count("cafe")
assert entspannung._per_day({"at": "2026-11-29", "views": 9}, D) is None   # zu frisch
p = entspannung.plan([], "auto", D, 0, 7, [6, 17])
assert len(p) == 7 and len({x["scene"] for x in p[:5]}) == 5 and [x["hour"] for x in p[:3]] == [6, 17, 6]

import yt
src = open(os.path.join(os.path.dirname(yt.__file__), "yt.py")).read()
assert 'spec.get("footer", FOOTER)' in src and 'spec.get("chunksize", -1)' in src
print("ok")
