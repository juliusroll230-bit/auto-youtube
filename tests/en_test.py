"""Englischer Kanal (en.py): Skripte in seed-en/, Sendeplätze 21 und 1 Uhr, Vorlagen (ab 1.500 Aufrufen oder beste 10 %,
ohne Ich-Geschichten), eigener Lernmodus, Hinweis auf synthetische Stimme, Ablauf ohne YouTube (rendern, hochladen,
nichts ohne Kanal), englische Untertitel. Läuft ohne Netz."""
import datetime as dt
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import cartoon  # noqa: E402
import en  # noqa: E402
import hookcheck  # noqa: E402
import learn  # noqa: E402
import store  # noqa: E402

store.init()
TZ = store.now().tzinfo

# 1. Alle Skripte in seed-en/ sind gültig, englisch und haben Quelle und Thumbnail-Text
items = en.scripts()
assert items, "seed-en/ ist leer"
slugs = set()
for name, spec in items:
    assert cartoon.validate(spec) == [], (name, cartoon.validate(spec))
    assert spec["language"] == "en" and spec.get("quelle") and spec.get("thumb_text"), name
    assert spec["slug"] not in slugs, "doppelter slug " + spec["slug"]
    slugs.add(spec["slug"])
    words = " ".join(s["text"] for s in spec["segments"]).lower().split()
    assert not {"und", "der", "das", "nicht", "du", "ist", "wenn"} & set(words), (name, "klingt deutsch")
    assert len(spec["title"]) <= 60 and "–" not in json.dumps(spec, ensure_ascii=False), name
    assert "abonn" not in json.dumps(spec, ensure_ascii=False).lower() and "subscribe" not in " ".join(words), name

# 2. Englische Untertitel: Zahlwörter bleiben Wörter (deutsch: „elf“ wird 11)
segs = [{"text": "An elf stayed awake for eleven days."}]
de = [w["w"] for w in cartoon.word_times(segs, [(0.0, 2.0)])]
en_words = [w["w"] for w in cartoon.word_times(segs, [(0.0, 2.0)], "en")]
assert "11" in de and "elf" in en_words and "11" not in en_words, (de, en_words)

# 3. Sendeplätze: 21 Uhr und 1 Uhr (Berlin), je 3 Stunden offen
cfg = {**store.config(), "en_token": "tok", "en_hours": [21, 1]}
day = dt.datetime(2026, 11, 27, 0, 0, tzinfo=TZ)
assert en.due_slot(cfg, day.replace(hour=20)) is None
assert en.due_slot(cfg, day.replace(hour=21, minute=5)) == "2026-11-27-21"
assert en.due_slot(cfg, day.replace(hour=1, minute=30)) == "2026-11-27-01"
assert en.due_slot(cfg, day.replace(hour=5)) is None
assert en.next_slot(cfg, day.replace(hour=10)).hour == 21

# 4. Vorlagen: ab 1.500 Aufrufen oder beste 10 %, keine Ich-Geschichten, keine Clips, nicht doppelt
spec_of = {
    "a": {"slug": "a", "title": "Was passiert, wenn du nie schläfst?", "niche": "Erklären", "stil": "cartoon"},
    "b": {"slug": "b", "title": "Warum Mama mir zwei Brote einpackt", "niche": "Erzählung", "stil": "cartoon"},
    "c": {"slug": "c", "title": "Das Schiff ohne Crew", "niche": "Mystery", "stil": "cartoon"},
    "d": {"slug": "d", "title": "Firmen-Folge", "niche": "Erklären", "format": "firma"},
}
for i in range(20):
    spec_of[f"x{i}"] = {"slug": f"x{i}", "title": f"Thema {i}", "niche": "Horror", "stil": "cartoon"}
rated = [{"slug": "a", "title": "A", "views": 2600}, {"slug": "b", "title": "B", "views": 2800},
         {"slug": "c", "title": "C", "views": 900}, {"slug": "d", "title": "D", "views": 5000},
         {"slug": "clip", "title": "Clip", "views": 9000, "kind": "clip"}]
rated += [{"slug": f"x{i}", "title": f"X{i}", "views": 100 + i} for i in range(20)]
src = en.sources(rated, lambda v: spec_of.get(v.get("slug")), used=())
got = [x["slug"] for x in src]
assert got[0] == "a" and "b" not in got and "d" not in got and "clip" not in got, got
assert "c" in got, "900 Aufrufe liegt unter den besten 10 % dieser Liste"
assert "x0" not in got, got
assert "a" not in [x["slug"] for x in en.sources(rated, lambda v: spec_of.get(v.get("slug")), used={"a"})]

# 5. Upload-Text: englisch, Hinweis auf synthetische Stimme
up = en.upload_spec(items[0][1])
assert up["language"] == "en" and en.DISCLOSURE in up["description"] and "synthetic" in up["description"]
assert up["footer"] == en.FOOTER and "Abonn" not in up["footer"]

# 6. Ablauf mit vorgetäuschtem Rendern und Upload (Server)
import make_short  # noqa: E402
import server  # noqa: E402

clock = [day.replace(hour=20)]
store.now = lambda: clock[0]
renders, ups, thumbs = [], [], []


def fake_build(spec, out_dir, tts, stock_key=None, info=None):
    os.makedirs(out_dir, exist_ok=True)
    renders.append(spec)
    p = os.path.join(out_dir, spec["slug"] + ".mp4")
    open(p, "wb").write(b"mp4")
    return p, 21.0, [(0.0, 2.0), (2.0, 4.0)]


make_short.build_video = fake_build
make_short.voice_model = lambda v: None
store.save_config(en_token="en-token", client_id="cid", client_secret="sec")
server.en_step()
assert not renders and en.load()["error"] == en.NO_VOICE, "ohne englische Stimme nichts rendern (sonst liest die deutsche)"
store.save_config(en_token="")
make_short.voice_model = lambda v: object()
server.tts = lambda: None
server.yt.upload = lambda c, path, spec: (ups.append((c["refresh_token"], spec)), f"en{len(ups)}")[1]
server.yt.set_thumbnail = lambda c, vid, path: thumbs.append((c["refresh_token"], vid))
server.make_thumbs = lambda spec: {"A": "a.jpg", "B": "b.jpg"}
main_before = len(store.state()["uploads"])

server.en_step()
assert not renders, "ohne verbundenen Kanal passiert nichts"
assert not en.wants_render(store.config())
store.save_config(en_token="en-token", client_id="cid", client_secret="sec")
assert en.wants_render(store.config()), "Vorrat des Hauptkanals wartet, bis der EN-Short gerendert ist"

server.en_step()   # 20 Uhr: rendern
assert len(renders) == 1 and not ups
r = renders[0]
assert r["stimme"] == "english" and r["abo"] == "ohne" and r["language"] == "en", r
assert r["effekte"] in learn.EFFECTS and r["uebergang"] in learn.CARTOON_TRANSITIONS and r["halten"] in learn.HOLDS
assert not en.wants_render(store.config()), "fertig gerendert: Hauptkanal darf wieder"

clock[0] = day.replace(hour=21, minute=4)
server.en_step()   # 21 Uhr: hochladen mit dem EN-Token
assert len(ups) == 1 and ups[0][0] == "en-token" and ups[0][1]["language"] == "en", ups
assert thumbs and thumbs[0][0] == "en-token"
d = en.load()
assert d["uploads"][0]["video_id"] == "en1" and d["uploads"][0]["channel"] == "en" and "2026-11-27-21" in d["done"]
assert len(store.state()["uploads"]) == main_before, "EN-Uploads zählen nicht zum Hauptkanal"

server.en_step()   # gleicher Abend: nächstes Skript vorrendern, nicht nochmal hochladen
assert len(renders) == 2 and len(ups) == 1
clock[0] = (day + dt.timedelta(days=1)).replace(hour=1, minute=10)
server.en_step()
assert len(ups) == 2 and "2026-11-28-01" in en.load()["done"]

# Keine Skripte mehr: Platz wird ausgelassen (Hinweis), nichts kaputt
if len(items) == 2:
    clock[0] = (day + dt.timedelta(days=1)).replace(hour=21, minute=1)
    server.en_step()
    assert "2026-11-28-21" in en.load()["done"] and len(ups) == 2

# 7. Eigener Lernmodus: nur EN-Uploads, Aufrufe vom EN-Kanal
en.set_stats({"en1": {"views": 4000}, "en2": {"views": 300}})
ps = en.posted()
assert [p.get("views") for p in ps] == [4000, 300] and all("features" in p for p in ps)
look = en.choose_look(items[0][1])
assert look["stimme"] == "english"

# 8. Pausiert: nichts
store.save_config(en_on=False)
n = len(renders)
clock[0] = (day + dt.timedelta(days=2)).replace(hour=21, minute=1)
server.en_step()
assert len(renders) == n and not en.wants_render(store.config())
store.save_config(en_on=True)

# 9. Karte im Dashboard
ov = en.overview(store.config(), [])
assert ov["connected"] and ov["total"] == 2 and ov["hours"] == [21, 1] and ov["views"] == 4300, ov
assert "en" in store.dashboard()

# 10. hookcheck bleibt deutsch: EN-Skripte gehen nicht durch die deutsche Warteschlange
assert not any(os.path.basename(f).startswith("0001-sleep") for f in store.queue_files())
assert hookcheck  # wird nur für den Hauptkanal benutzt

print("en ok")
