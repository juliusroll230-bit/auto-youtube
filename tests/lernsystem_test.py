"""Lernsystem seit 25.11.2026: fairer Vergleich mit den Nachbartagen, Thompson-Auswahl, „% sicher“,
neue Vorbild-Taktiken (Musik, Übergang, Dranbleiben) und der Lernmodus von Quiet Corner."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import learn  # noqa: E402

now = dt.datetime(2026, 11, 25, 20, 0)


def vid(day, views, feats, niche="Erklären"):
    return {"posted_at": (now - dt.timedelta(days=day)).isoformat(), "views": views, "niche": niche, "features": feats}


# 1) Fairer Vergleich: Kanal wächst (alte Videos 100, neue 1000). Variante "b" lief nur in der alten Zeit, ist dort aber
#    doppelt so gut wie ihre Nachbarn. Roh hätte "a" (nur neu) gewonnen, fair gewinnt "b".
posted = []
for d in range(30, 20, -1):
    posted += [vid(d, 100, {"x": "a"}), vid(d, 200, {"x": "b"})] if d % 2 else [vid(d, 100, {"x": "c"})]
for d in range(10, 2, -1):
    posted += [vid(d, 1000, {"x": "a"}), vid(d, 1000, {"x": "c"})]
fs = learn.feature_scores(posted, now)["x"]
assert fs["a"]["score"] > fs["b"]["score"], "roh liegt a vorn"
assert fs["b"]["rel"] > fs["a"]["rel"], ("fair liegt b vorn", fs["b"]["rel"], fs["a"]["rel"])

# 2) Ausreißer: ein einzelner Glückstreffer macht einen Wert nicht sofort zum sicheren Sieger
one = [vid(d, 500, {"y": "gut"}) for d in range(12, 2, -1)] + [vid(d, 500, {"y": "glueck"}) for d in range(12, 4, -1)]
one.append(vid(3, 50000, {"y": "glueck"}))
fy = learn.feature_scores(one, now)["y"]
assert fy["glueck"]["score"] > 5 * fy["gut"]["score"]          # der rohe Schnitt springt
assert fy["glueck"]["rel"] < 2.0, fy["glueck"]["rel"]            # der faire Faktor bleibt vernünftig

# 3) Thompson: klarer Gewinner kommt fast immer dran, alle Werte bekommen erst MIN_VIDEOS Videos
clear_win = [vid(d, 3000 if d % 3 == 0 else 1000, {"t": "gut" if d % 3 == 0 else "schwach"}) for d in range(40, 2, -1)]
ft = learn.feature_scores(clear_win, now)["t"]
picks = [learn.choose(("gut", "schwach"), ft, k) for k in range(200)]
assert picks.count("gut") >= 180, picks.count("gut")
assert learn.choose(("gut", "schwach", "neu"), ft, 1) == "neu"   # noch nie getestet: zuerst
ch = learn.chances(ft)
assert ch["gut"] > .95 and abs(sum(ch.values()) - 1) < 1e-9
# knappes Rennen: beide kommen oft dran
close = [vid(d, 1000 + (30 if d % 2 else 0), {"k": "a" if d % 2 else "b"}) for d in range(10, 2, -1)]
fk = learn.feature_scores(close, now)["k"]
pk = [learn.choose(("a", "b"), fk, k) for k in range(200)]
assert 30 <= pk.count("b") <= 170, pk.count("b")

# 4) Zusammenfassung für die Zentrale: Faktor und „% sicher“
rows = {r["key"]: r for r in learn.feature_summary({"musik": ft})}
vals = rows["musik"]["values"]
assert vals[0]["value"] == "gut" and vals[0]["rel"] > 1 and vals[0]["chance"] >= 95
assert rows["musik"]["label"] == "Musik" and "uebergang" in rows and "halten" in rows and "platz" in rows

# 5) Themen-Plan nutzt dieselbe Sicherheit (Lernmodus an), Testplatz bleibt
ns = learn.niche_scores([dict(v, niche="Körper" if v["features"]["t"] == "gut" else "Technik") for v in clear_win], now)
assert learn.favorite(ns) == "Körper" and ns["Körper"]["rel"] > ns["Technik"]["rel"]
queue = [(f"{i}.json", {"niche": "Körper" if i % 2 else "Technik"}) for i in range(12)]
order = learn.plan(queue, ["Körper", "Technik"] * 5, ns, 4)
assert sum(1 for _, s in order[:8] if s["niche"] == "Körper") >= 4
assert learn.summary(ns)["niches"][0]["chance"] is not None

# 6) Neue Merkmale nur bei neuen Cartoon-Shorts
spec = {"stil": "cartoon", "niche": "Erklären", "title": "Warum gähnst du?", "stimmung": "neugierig", "slug": "x",
        "segments": [{"text": "Warum gähnst du so oft?"}]}
f = learn.features(spec, {"musik": "drop", "uebergang": "wisch", "halten": "frage", "transition": "zoom"})
assert f["musik"] == "drop" and f["uebergang"] == "wisch" and f["halten"] == "frage" and f["transition"] is None
assert learn.features({**spec, "laenge": "lang"}, {"musik": "drop"})["musik"] is None
assert learn.choose_music({}, 0, spec) in learn.MUSIC_FOR_MOOD["neugierig"]
assert learn.choose_music({}, 0, {**spec, "stimmung": "gruselig"}) == "dunkel"
assert learn.choose_music({}, 0, {**spec, "niche": "Erzählung", "stimmung": "warm"}) == "warm"
assert {learn.choose_transition({}, k) for k in range(5)} <= set(learn.CARTOON_TRANSITIONS)
assert learn.day_slot(3) == "1. bis 5." and learn.day_slot(12) == "11. bis 15." and learn.day_slot(None) is None
assert learn.hour_group("2026-11-25T08:00:00") == "morgens (bis 11)" and learn.hour_group("2026-11-25T21:00:00") == "abends (ab 19)"

# 7) Cartoon: neue Felder prüfen, Frage für „Frage oben“
import cartoon  # noqa: E402
base = {"stil": "cartoon", "title": "Was passiert, wenn du nie schläfst? 😴",
        "segments": [{"text": f"Satz {i}.", "szene": {"typ": "objekt", "objekt": "😴"}} for i in range(6)]}
assert not cartoon.validate({**base, "musik": "drop", "uebergang": "kreis", "halten": "beides"})
assert len(cartoon.validate({**base, "musik": "techno", "uebergang": "x", "halten": "y"})) == 3
assert cartoon.question(base) == "Was passiert, wenn du nie schläfst?"
assert len(cartoon.question({"title": "Warum " + "sehr " * 20 + "lang?"})) <= 54

# 8) Musik-Stile klingen (selbst erzeugt), drop setzt erst auf der Auflösung ein
import numpy as np  # noqa: E402
import audio  # noqa: E402
r = 22050
for st in ("beat", "spannung", "leicht", "drop", "dunkel", None):
    m = audio.mix(np.zeros(4 * r, dtype=np.float32), r, [1.0], 3, mood="neugierig", style=st, drop=2.5)
    assert len(m) == 4 * r and 0 < np.abs(m).max() <= 1.0, st
d = audio.drop_music(4, r, 1, 2.5)
assert np.abs(d[int(3 * r):]).mean() > np.abs(d[:int(2 * r)]).mean()   # nach dem Drop lauter

# 9) Quiet Corner: Lernmodus mit Sicherheit, Geschichte gegen Szene
import entspannung  # noqa: E402
D = dt.date(2026, 12, 20)
ups = []
for k in range(24):
    sc = list(entspannung.SCENES)[k % 5]
    ups.append({"idea": "x", "scene": sc, "minutes": 300, "at": (D - dt.timedelta(days=3 + k)).isoformat(),
                "views": (900 if sc == "kamin" else 100) * (3 + k), "hour": 6 if k % 2 else 17,
                **({"story": "s"} if k % 2 else {})})
rowz = entspannung.learn_rows(ups, D)
kam = next(x for x in rowz["scene"] if x["key"] == "kamin")
assert kam["chance"] >= 90 and kam["per_day"] > 500
assert {x["key"] for x in rowz["inhalt"]} == {"Geschichte", "Szene"} and rowz["zeit"][0]["n"] > 0
import random  # noqa: E402
picks = [entspannung._pick(list(entspannung.SCENES), ups, "scene", D, random.Random(i)) for i in range(80)]
assert 60 <= picks.count("kamin") <= 79, picks.count("kamin")
assert entspannung.use_story(ups[:4], D, 1)                 # zu wenig Daten: Geschichte
bad = [{**u, "views": 50 * (3 + i) if u.get("story") else 900 * (3 + i)} for i, u in enumerate(ups)]
assert not entspannung.use_story(bad, D, 1) and entspannung.use_story(bad, D, 2)   # Szene klar besser: nur jedes 2.

# 10) Vorbild-Taktiken: jede zeigt auf ein Merkmal, das die Zentrale vergleicht
import vorbilder  # noqa: E402
assert all(t["merkmal"] in learn.FEATURE_NAMES for t in vorbilder.TAKTIKEN) and len(vorbilder.TAKTIKEN) >= 6
print("lernsystem ok")
