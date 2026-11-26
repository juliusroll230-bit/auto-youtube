"""Sonntags-Zusammenschnitt (zusammenschnitt.py): Auswahl mit learn.relative (nur eigene KI-Shorts, mind. 8, bis ca.
8 Minuten), Aufbewahren und Aufräumen, Bauen mit ffmpeg (Querformat ohne schwarze Balken, Kapitel), Ablauf am Sonntag
(14 Uhr bauen, 17 Uhr hochladen, langes Video entfällt), Lern-Merkmal. Läuft ohne Netz und ohne YouTube."""
import datetime as dt
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import learn  # noqa: E402
import store  # noqa: E402
import zusammenschnitt as zs  # noqa: E402

store.init()
TZ = store.now().tzinfo
SUN = dt.datetime(2026, 11, 29, 14, 5, tzinfo=TZ)   # Sonntag
assert SUN.weekday() == 6


def short(i, days_ago, views, **extra):
    at = SUN - dt.timedelta(days=days_ago, hours=i % 5)
    return {"video_id": f"vid{i:03d}", "slug": f"s{i}", "title": f"Short Nummer {i}", "views": views,
            "posted_at": at.isoformat(timespec="seconds"), "duration": 24.0, **extra}


# 30 Shorts dieser Woche (Aufrufe steigen mit i), dazu Dinge, die nie hinein dürfen
posted = [short(i, 1 + i % 6, 300 + 40 * i) for i in range(30)]
posted += [short(100, 2, 99999, kind="clip"), short(101, 2, 99999, channel="clips"),
           short(102, 2, 99999, abgabe=True), short(103, 2, 99999, lang=True),
           short(104, 2, 99999),                      # Firmen-Folge (format firma)
           short(105, 9, 99999)]                      # älter als eine Woche
specs = {p["slug"]: {"slug": p["slug"], "title": p["title"]} for p in posted}
specs["s104"]["format"] = "firma"
find = specs.get
have = lambda vid: True   # noqa: E731

# 1. Auswahl: beste zuerst, nichts Fremdes, mindestens 8, bis ca. 8 Minuten
items, why = zs.pick(posted, SUN, have=have, find=find)
assert why is None and items, why
ids = [x["video_id"] for x in items]
assert not {"vid100", "vid101", "vid102", "vid103", "vid104", "vid105"} & set(ids), ids
assert len(items) >= zs.MIN_CLIPS
total = sum(x["duration"] + 2.5 for x in items)
assert 8 * 60 - 12 <= total <= zs.MAX_S, total
rel = {v["video_id"]: lr for v, _, lr, _ in learn.relative(posted, SUN)}
assert all(rel[a] >= rel[b] for a, b in zip(ids, ids[1:])), "beste zuerst (fair nach learn.relative)"
few, why = zs.pick(posted[:5], SUN, have=have, find=find)
assert few is None and "mindestens 8" in why, why
short_ones = [dict(p, duration=8.0) for p in posted[:12]]
few, why = zs.pick(short_ones, SUN, have=have, find=find)
assert few is None and "Minuten" in why, why
assert zs.pick(posted, SUN, have=lambda vid: False, find=find)[0] is None, "ohne aufbewahrte Datei geht es nicht"

# 2. Text: Titel, Kapitel ab 0:00, Hinweis auf synthetische Stimme
t = zs.text_for(items[:8], [(0, "Intro"), (8.4, "Platz 8: A"), (35, "Platz 7: B"), (75.2, "Platz 1: C")], SUN)
assert t["title"] == "Die 8 besten Shorts der Woche (KW 48)", t["title"]
assert "\n0:00 Intro\n0:08 Platz 8: A\n0:35 Platz 7: B\n1:15 Platz 1: C\n" in t["description"], t["description"]
assert "synthetisch" in t["description"] and len(t["title"]) < 60

# 3. Aufbewahren und Aufräumen
src = os.path.join(tempfile.mkdtemp(), "x.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=270x480:rate=30:duration=2",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", src], check=True)
zs.keep(src, "vid001", {"slug": "s1"})
zs.keep(src, "vid002", {"slug": "s2"})
zs.keep(src, "lang1", {"slug": "l", "laenge": "lang"})
zs.keep(src, "firma1", {"slug": "f", "format": "firma"})
assert sorted(os.listdir(store.path(zs.DIR))) == ["vid001.mp4", "vid002.mp4"]
old = (SUN - dt.timedelta(days=9)).timestamp()
os.utime(zs.clip_path("vid001"), (old, old))
zs.prune(now=SUN, posted=[])
assert os.listdir(store.path(zs.DIR)) == ["vid002.mp4"], "älter als 8 Tage wird gelöscht"
zs.KEEP_TOP = 20
for i in range(35):   # zu viele: von den bewerteten bleiben nur die 20 besten, noch nicht bewertete bleiben
    open(zs.clip_path(f"vid{i:03d}"), "wb").write(b"x")
zs.prune(now=SUN, posted=posted)
left = {f[:-4] for f in os.listdir(store.path(zs.DIR))}
assert len(left) == 26 and "vid029" in left and "vid034" in left and "vid001" not in left, sorted(left)  # vid000 ist erst genau 1 Tag alt
zs.KEEP_TOP = 30

# 4. Bauen: Querformat 1920x1080, Platz 1 am Schluss, Kapitel passen zur Länge
for vid in ("vid001", "vid002", "vid003"):
    subprocess.run(["cp", src, zs.clip_path(vid)], check=True)
spoken = []


def speak(text):
    spoken.append(text)
    rate = 22050
    return (0.2 * np.sin(np.linspace(0, 2 * np.pi * 300, int(rate * 0.6)))).astype(np.float32), rate


three = [{"video_id": f"vid00{i}", "title": f"Titel {i}"} for i in (1, 2, 3)]
out = os.path.join(tempfile.mkdtemp(), "zs.mp4")
path, chapters, secs = zs.build(three, speak, out, now=SUN)
info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                       "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
assert info == "1920,1080", info
assert [c[1] for c in chapters] == ["Intro", "Platz 3: Titel 3", "Platz 2: Titel 2", "Platz 1: Titel 1"], chapters
assert chapters[0][0] == 0 and all(b[0] - a[0] >= 4 for a, b in zip(chapters, chapters[1:])), chapters
assert chapters[-1][0] < secs and 3 * 2 + 5 < secs < 40, secs
assert spoken[0].startswith("Das sind die drei beliebtesten") and "Platz drei." in spoken and spoken[-1] == zs.OUTRO, spoken

# 5. Ablauf am Sonntag (Bauen und Upload vorgetäuscht)
built, ups = [], []


def fake_build(items_, speak_, out_, now=None):
    built.append(len(items_))
    open(out_, "wb").write(b"video")
    return out_, [(0, "Intro")] + [(10 + 26 * i, f"Platz {len(items_) - i}: x") for i in range(len(items_))], 500.0


zs.build = fake_build
real_find = store.find_spec
store.find_spec = lambda slug, index=None: specs.get(slug)
for p in posted:
    open(zs.clip_path(p["video_id"]), "wb").write(b"x")
upload = lambda path, spec: (ups.append((path, spec)), "zsVID")[1]   # noqa: E731
assert not zs.due(SUN.replace(hour=13)), "vor 14 Uhr nichts"
assert not zs.due(SUN - dt.timedelta(days=1)), "nur sonntags"
d = zs.run(now=SUN, speak=speak, upload=upload, posted=posted)
assert d["status"] == "fertig" and built and not ups, "um 14 Uhr bauen, noch nicht hochladen"
assert not zs.due(SUN.replace(hour=16)), "fertig gebaut: bis 17 Uhr warten"
assert zs.run(now=SUN.replace(hour=16), speak=speak, upload=upload, posted=posted) is None
d = zs.run(now=SUN.replace(hour=17, minute=1), speak=speak, upload=upload, thumbs=lambda s, v: "A: Wort + Satz",
           posted=posted)
assert d["status"] == "hochgeladen" and len(built) == 1 and len(ups) == 1, (d, built)
spec = ups[0][1]
assert spec["laenge"] == "lang" and "#shorts" not in spec["title"].lower() and "Kapitel:" in spec["description"]
assert spec["thumb_text"][0].startswith("TOP "), spec["thumb_text"]
st = store.state()
rec = st["uploads"][-1]
assert rec["zusammenschnitt"] and rec["lang"] and rec["video_id"] == "zsVID" and len(rec["sources"]) == built[0], rec
assert "2026-11-29" in st["long_slots"], "das normale lange Video entfällt heute"
assert store.due_long(7, at=SUN.replace(hour=19, minute=5)) is None
assert not os.path.exists(store.path(zs.DIR, "zusammenschnitt-2026-11-29.mp4")), "fertige Datei wird gelöscht"
assert not zs.due(SUN.replace(hour=18)), "nur einmal pro Sonntag"

# 6. Nicht genug Shorts: übersprungen, langes Video läuft normal
NEXT = SUN + dt.timedelta(days=7)
d = zs.run(now=NEXT, speak=speak, upload=upload, posted=posted[:3])
assert d["status"] == "übersprungen" and "mindestens 8" in d["reason"], d
assert store.due_long(7, at=NEXT.replace(hour=19)) == "2026-12-06"
# Langes Video lief schon: übersprungen
zs.save(week=None, status=None)
st = store.state()
st["long_slots"].append("2026-12-13")
store.write("state.json", st)
d = zs.run(now=NEXT + dt.timedelta(days=7), speak=speak, upload=upload, posted=posted)
assert d["status"] == "übersprungen" and "lief heute schon" in d["reason"], d
# Aus: nichts
zs.save(on=False)
assert not zs.due(NEXT + dt.timedelta(days=14))
zs.save(on=True)

# 7. Lern-Merkmal und Karte
store.find_spec = real_find
items_all = store.posted_items()
zrec = next(x for x in items_all if x.get("video_id") == "zsVID")
assert zrec["features"]["zusammenschnitt"] == "Zusammenschnitt", zrec.get("features")
assert "zusammenschnitt" in learn.FEATURE_NAMES
ov = zs.overview(posted=items_all, now=SUN.replace(hour=18))
assert ov["on"] and ov["last"]["video_id"] == "zsVID" and ov["next"].startswith("2026-12-06T17:00"), ov
dash = store.dashboard()
assert "wochenschnitt" in dash and dash["wochenschnitt"]["last"]["video_id"] == "zsVID", dash.get("wochenschnitt")

print("zusammenschnitt ok")
