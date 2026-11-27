"""Sleep History für Quiet Corner (sleephistory.py): Skripte (Kapitel 400 bis 900 Wörter, zwei Quellen), Häufigkeit mit
Lernmodus (alle 3 Tage, sicherer Gewinner alle 2, sicherer Verlierer alle 7), Sprechspur mit Kapiteln auf vollen Minuten,
Kapitel-Karten über der Szene (echtes ffmpeg), Titel und Kapitel mit Zeitmarken. Läuft ohne Netz und ohne Stimme."""
import datetime as dt
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import entspannung  # noqa: E402
import sleephistory as sh  # noqa: E402

# 1. Skripte: gültig, Titel „The Entire Story of …“, ruhig (keine Schlacht-Details), Ende mit Goodnight
hs = sh.scripts()
assert hs, "sleep-history/ ist leer"
ids = set()
for h in hs:
    assert sh.validate(h, entspannung.SCENES) == [], (h["id"], sh.validate(h, entspannung.SCENES))
    assert h["id"] not in ids
    ids.add(h["id"])
    text = " ".join(c["text"] for c in h["chapters"]).lower()
    assert not any(w in text for w in ("blood", "slaughter", "massacre", "beheaded", "corpse")), h["id"]
    assert h["chapters"][-1]["text"].rstrip().endswith("Goodnight.") and "legend" in text, h["id"]
assert sh.validate({"title": "Rome", "chapters": [{"title": "a", "icon": "x", "text": "word " * 100}]})

# 2. Häufigkeit: ohne Sleep History sofort, sonst alle 3 Tage
today = dt.date(2026, 12, 10)
day = lambda k: (today - dt.timedelta(days=k)).isoformat()   # noqa: E731
assert sh.due([], today)
assert not sh.due([{"idea": "x", "history": "a", "at": day(1)}], today)
assert sh.due([{"idea": "x", "history": "a", "at": day(3)}], today)


def ups(hist_views, story_views, scene_views):
    out = []
    for k in range(5):
        out += [{"idea": "x", "history": f"h{k}", "at": day(10 + k), "views": hist_views},
                {"idea": "x", "story": f"s{k}", "at": day(10 + k), "views": story_views},
                {"idea": "x", "at": day(10 + k), "views": scene_views}]
    return out


assert sh.gap_days(ups(2000, 200, 200), today) == sh.FAST_GAP, "klarer Gewinner: öfter"
assert sh.gap_days(ups(100, 2000, 300), today) == sh.SLOW_GAP, "klarer Verlierer: nur noch 1 pro Woche"
assert sh.gap_days(ups(500, 520, 480), today) == sh.GAP_DAYS, "knapp: bleibt bei 3 Tagen"
assert sh.gap_days(ups(2000, 200, 200)[:6], today) == sh.GAP_DAYS, "unter 4 Videos je Seite: nichts ändern"
rows = entspannung.learn_rows(ups(2000, 200, 200), today)["inhalt"]
assert [r["key"] for r in rows] == ["History", "Geschichte", "Szene"] and rows[0]["n"] == 5, rows

# 3. Sprechspur: Kapitel beginnen auf vollen Minuten (Stimme vorgetäuscht)
spoken = []


def fake_narrate(text, path, rate):
    spoken.append(text)
    secs = 50 if len(spoken) % 2 else 70
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.sin(np.arange(int(rate * secs)) / 9) * 3000).astype("<i2").tobytes())


tmp = tempfile.mkdtemp()
h = {**hs[0], "chapters": hs[0]["chapters"][:3]}
narr = os.path.join(tmp, "n.wav")
chapters, story_min = sh.narrate(h, narr, tmp, narrate_fn=fake_narrate)
assert [c[0] for c in chapters] == [0, 2, 4] and [c[2] for c in chapters] == [2, 2, 2] and story_min == 6, chapters
assert spoken[0].startswith("Chapter one. " + h["chapters"][0]["title"].rstrip(".")), spoken[0][:60]
with wave.open(narr) as w:
    assert abs(w.getnframes() / w.getframerate() - 360) < 0.5
assert sh.total_minutes(6) == 60 and sh.total_minutes(65) == 120 and sh.total_minutes(400) == 180

# 4. Bild: Karte und Kapitel-Video aus kopierten Stücken (kurze Schleife statt 60 s, damit der Test schnell bleibt)
png = sh.card_png(os.path.join(tmp, "card.png"), (640, 360), 2, 10, "The Republic", "🏛️")
from PIL import Image  # noqa: E402
im = Image.open(png)
assert im.size == (640, 360) and im.mode == "RGBA" and im.getpixel((5, 5))[3] == 0 and im.getpixel((60, 290))[3] > 100
loop = os.path.join(tmp, "loop.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=10:duration=6",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", loop], check=True)
vid = sh.chapter_video(loop, h, [(0, "A", 1), (1, "B", 1), (2, "C", 1)], 4, os.path.join(tmp, "video.mp4"), tmp)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vid],
                           capture_output=True, text=True).stdout)
assert 238 <= dur <= 241, dur

# 5. Text: Titel, Kapitel ab 0:00 mit Zeitmarken, Quellen, Hinweis auf synthetische Stimme
long_ch = [(0, "The Seven Hills", 6), (6, "The Kings", 55), (61, "The Republic", 7)]
meta = sh.meta(hs[0], "bibliothek-regen", 120, long_ch)
assert meta["title"].startswith("The Entire Story of Ancient Rome to Fall Asleep To") and len(meta["title"]) <= 100, meta["title"]
assert "\nChapters:\n0:00 The Seven Hills\n6:00 The Kings\n1:01:00 The Republic\n1:08:00 Quiet" in meta["description"], meta["description"]
assert "Sources: " in meta["description"] and sh.DISCLOSURE in meta["description"] and "synthetic" in meta["description"]
assert meta["thumb_text"] and len(meta["thumb_text"].split()) <= 3

print("sleephistory ok")
