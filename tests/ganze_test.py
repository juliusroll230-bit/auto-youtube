"""„Die ganze Geschichte“ (ganze.py): Skripte in seed-long/ (Kapitel, 15 bis 40 Minuten), Titel und Kapitel mit echter
Minutenzahl, 5 Ausschnitte mit Hook-Prüfung (echtes ffmpeg), Ablauf am Samstag (6 Uhr rendern, 19 Uhr hochladen, langes
Video entfällt), 1 Ausschnitt pro Tag ab 12 Uhr, Fehler: normales langes Video, Lernmerkmal und Karte. Läuft ohne Netz."""
import datetime as dt
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import cartoon  # noqa: E402
import ganze  # noqa: E402
import hookcheck  # noqa: E402
import learn  # noqa: E402
import store  # noqa: E402

store.init()
TZ = store.now().tzinfo
SAT = dt.datetime(2026, 11, 28, 6, 10, tzinfo=TZ)
assert SAT.weekday() == 5

# 1. Skripte: gültig, 15 bis 40 Minuten, Kapitel, Quellen, keine KI-Floskeln
items = ganze.scripts()
assert items, "seed-long/ ist leer"
for name, spec in items:
    assert cartoon.validate(spec) == [], (name, cartoon.validate(spec))
    assert 2700 <= ganze.words(spec) <= 7500 and len(spec["_chapters"]) >= 3, name
    assert "{min}" in spec["title"] and spec["title"].startswith("Die GANZE Geschichte"), spec["title"]
    assert len(spec.get("quellen") or []) >= 2 and spec.get("thema") and spec["stimme"] == "klar", name
    assert hookcheck.tells(spec) == [] and hookcheck.check(spec)["score"] >= 7, name
    assert "Sage" in spec["description"] or "Sagen" in spec["description"], "Sagen als Sagen kennzeichnen"
name, spec = items[0]
n = len(spec["segments"])
timings = [(6.0 * i, 6.0 * i + 5.6) for i in range(n)]

# 2. Nach dem Rendern: echte Minutenzahl, Kapitel ab 0:00, Thumbnail Thema + Minuten
total = timings[-1][1] + 2
fin = ganze.finish_spec(spec, total, timings)
m = round(total / 60)
assert fin["title"].startswith("Die GANZE Geschichte") and f"in {m} Minuten" in fin["title"] and "{min}" not in fin["title"], fin["title"]
assert "\nKapitel:\n0:00 " in fin["description"] and ganze.DISCLOSURE in fin["description"], fin["description"]
ts = [t for t, _ in fin["_chapter_times"]]
assert ts[0] == 0 and all(b - a >= 10 for a, b in zip(ts, ts[1:])), ts
assert fin["thumb_text"][0] == f"{spec['thema']} | in {m} Minuten", fin["thumb_text"]

# 3. Ausschnitte: die 5 besten Momente, je 18 bis 42 s, aus verschiedenen Kapiteln
ms = ganze.moments(spec, timings)
assert len(ms) == 5 and len({x["chapter"] for x in ms}) == 5, ms
assert all(18 <= x["end"] - x["start"] <= 42 for x in ms) and all(x["hook"] >= 6 for x in ms), ms
cs = ganze.cut_spec(fin, ms[0], "LONGID", 0)
assert "https://youtu.be/LONGID" in cs["description"] and cs["ausschnitt"] and len(cs["title"]) <= 60, cs

# 4. Schneiden: echtes ffmpeg, Querformat wird 1080x1920 mit Hinweis
tmp = tempfile.mkdtemp()
src = os.path.join(tmp, "lang.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=size=320x180:rate=2:duration={int(total) + 2}",
                "-f", "lavfi", "-i", f"sine=frequency=300:duration={int(total) + 2}", "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", src], check=True)
out = ganze.cut_video(src, 12.0, 34.0, os.path.join(tmp, "cut.mp4"), "Zeus wächst heimlich auf")
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of",
                        "csv=p=0", out], capture_output=True, text=True).stdout.strip()
assert probe == "1080,1920", probe

# 5. Ablauf am Samstag mit vorgetäuschtem Rendern und Upload
renders, ups, thumbs = [], [], []


def render(s):
    renders.append(s["slug"])
    v = os.path.join(store.path(ganze.WORK), "lang.mp4")
    os.makedirs(os.path.dirname(v), exist_ok=True)
    subprocess.run(["cp", src, v], check=True)
    return {"video": v, "total": total, "timings": timings, "look": {"stimme": "klar"}, "spec": s}


def upload(path, s):
    ups.append((path, s))
    return f"vid{len(ups)}"


assert not ganze.due(SAT.replace(hour=5)) and ganze.active(SAT.replace(hour=5)), "vor 6 Uhr nichts rendern, aber der Tag gehört ihr"
assert not ganze.due(SAT - dt.timedelta(days=1)), "nur samstags"
d = ganze.run(now=SAT, render=render, upload=upload)
assert d["status"] == "fertig" and renders == [spec["slug"]] and not ups, d
assert ganze.run(now=SAT.replace(hour=18), render=render, upload=upload)["status"] == "fertig" and len(renders) == 1
assert ganze.active(SAT.replace(hour=19)), "um 19 Uhr wartet das normale lange Video"
d = ganze.run(now=SAT.replace(hour=19, minute=5), render=render, upload=upload, thumbs=lambda s, v: thumbs.append(v) or "A")
assert d["status"] == "hochgeladen" and len(ups) == 1 and thumbs == ["vid1"], d
up_spec = ups[0][1]
assert f"in {m} Minuten" in up_spec["title"] and "Kapitel:" in up_spec["description"], up_spec["title"]
st = store.state()
rec = st["uploads"][-1]
assert rec["ganze"] and rec["lang"] and rec["video_id"] == "vid1" and "2026-11-28" in st["long_slots"], rec
assert store.due_long(7, at=SAT.replace(hour=19, minute=30)) is None, "das normale lange Video entfällt heute"
assert not ganze.active(SAT.replace(hour=20)) and not os.path.exists(renders and store.path(ganze.WORK, "lang.mp4"))
assert len(d["cuts"]) == 5 and all(os.path.exists(c["file"]) for c in d["cuts"]), d["cuts"]

# 6. Ausschnitte: nicht am selben Tag, danach 1 pro Tag ab 12 Uhr
assert ganze.cut_due(SAT.replace(hour=21)) is None
SUN = SAT + dt.timedelta(days=1)
assert ganze.cut_due(SUN.replace(hour=11)) is None
cut_ups = []
assert ganze.post_cut("2026-11-29-12", lambda p, s: cut_ups.append(s) or "cut1", now=SUN.replace(hour=12, minute=2))
assert cut_ups[0]["ausschnitt"] and "https://youtu.be/vid1" in cut_ups[0]["description"]
st = store.state()
assert st["uploads"][-1]["ausschnitt"] and "2026-11-29-12" in st["done_slots"], st["uploads"][-1]
assert ganze.cut_due(SUN.replace(hour=15)) is None, "nur 1 pro Tag"
assert ganze.cut_due((SUN + dt.timedelta(days=1)).replace(hour=12)) is not None

# 7. Nächster Samstag ohne neues Skript oder mit Fehler: das normale lange Video läuft
NEXT = SAT + dt.timedelta(days=7)
if len(items) == 1:
    assert not ganze.active(NEXT), "kein neues Skript: normales langes Video"
else:
    def broken(s):
        raise RuntimeError("Renderer kaputt")
    d = ganze.run(now=NEXT, render=broken, upload=upload)
    assert d["status"] == "fehler" and not ganze.active(NEXT.replace(hour=19))
ganze.save(on=False)
assert not ganze.active(SAT + dt.timedelta(days=14))
ganze.save(on=True)

# 8. Lernmerkmal, Vergleich, Karte
posted = store.posted_items()
it = next(x for x in posted if x.get("video_id") == "vid1")
assert it["features"]["ganze"] == "Ganze Geschichte" and "ganze" in learn.FEATURE_NAMES, it.get("features")
cmp_ = ganze.compare([{"lang": True, "ganze": True, "views": 900, "avg_dur": 300}, {"lang": True, "views": 300},
                      {"lang": True, "views": 500, "avg_dur": 120}, {"lang": True, "zusammenschnitt": True, "views": 9}])
assert cmp_["ganze"] == {"n": 1, "views": 900, "watch_min": 5.0} and cmp_["normal"]["n"] == 2 and cmp_["normal"]["views"] == 400, cmp_
ov = ganze.overview(posted=posted, now=SUN)
assert ov["on"] and ov["last"]["video_id"] == "vid1" and ov["cuts_posted"] == 1 and ov["cuts_waiting"] == 4, ov
assert ov["next"].startswith("2026-12-05T19:00"), ov["next"]
assert "ganze" in store.dashboard()

print("ganze ok")
