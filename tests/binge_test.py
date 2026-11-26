"""Mehr Videos am Stück (binge.py): Frage-Kommentar, Geschichten-Playlist, Gewinner, Lernmerkmal Gewinner-Nachbau."""
import datetime as dt
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import binge  # noqa: E402
import learn  # noqa: E402
import store  # noqa: E402

story = {"slug": "zwei-brote", "niche": "Erzählung", "stil": "cartoon", "title": "Warum Mama mir zwei Brote einpackt",
         "segments": [{"text": "Plötzlich packt Mama zwei Brote ein."}]}
horror = {"slug": "leerer-server", "niche": "Horror", "stil": "cartoon", "title": "Der leere Server", "segments": []}
expl = {"slug": "schlaf", "niche": "Erklärvideo", "stil": "cartoon", "title": "Was passiert, wenn du nicht schläfst?",
        "segments": [], "frage": "Wie lange warst du schon mal wach?"}
firma = {"slug": "abo-motors-7", "format": "firma", "stil": "cartoon", "title": "Jeder Abonnent", "segments": []}
lang = {"slug": "nebra", "niche": "Erklärvideo", "laenge": "lang", "title": "Himmelsscheibe", "segments": []}
specs = {s["slug"]: s for s in (story, horror, expl, firma, lang)}

# Fragen: reihum je Video-Typ, eigene Frage aus dem Skript, Playlist-Hinweis nur bei Geschichten
q0 = binge.question(story, "Erzählte Geschichte", 0)
q1 = binge.question(story, "Erzählte Geschichte", 1)
assert q0 != q1 and q0.endswith("?"), (q0, q1)
assert binge.PLAYLIST_HINT in binge.question(story, "Erzählte Geschichte", 0, playlist=True)
assert binge.PLAYLIST_HINT not in binge.question(horror, "Horror", 0, playlist=True)
assert binge.question(expl, learn.video_type(expl), 5) == "Wie lange warst du schon mal wach?"
assert binge.question(horror, "Horror", 0) in binge.QUESTIONS["Horror"]
assert binge.question({}, "Normal (Fakten)", 0) in binge.QUESTIONS[""]
assert binge.clean_question("Schau auf www.x.de?") is None
assert binge.clean_question("Abonniere uns?") is None
assert binge.clean_question("Was meinst du – echt?") == "Was meinst du, echt?"
for group, options in binge.QUESTIONS.items():
    for o in options:
        assert "http" not in o and "–" not in o and "—" not in o and len(o) < 80 and o.rstrip(" 👻🥹🤔🤯").endswith("?"), o
        assert sum(1 for ch in o if ord(ch) > 0x2600) <= 1, o

# Wer bekommt eine Frage: nur Uploads ab dem Einschalten, nach ein paar Minuten, nicht Firmen-Spiel, nicht Clip-Kanal
now = store.now()
iso = lambda **kw: (now - dt.timedelta(**kw)).isoformat(timespec="seconds")  # noqa: E731
d = binge.load()
d["since"] = iso(hours=10)
uploads = [
    {"slug": "zwei-brote", "video_id": "vidStory01", "posted_at": iso(minutes=10), "title": "Brote"},
    {"slug": "leerer-server", "video_id": "vidHorror1", "posted_at": iso(minutes=1), "title": "Server"},   # zu frisch
    {"slug": "schlaf", "video_id": "vidSchlaf1", "posted_at": iso(hours=11), "title": "Schlaf"},          # vor dem Einschalten
    {"slug": "abo-motors-7", "video_id": "vidFirma01", "posted_at": iso(minutes=20), "title": "Firma"},
    {"slug": "zwei-brote", "video_id": "vidClip001", "posted_at": iso(minutes=20), "channel": "clips"},
    {"slug": "nebra", "video_id": "vidLang001", "posted_at": iso(minutes=30), "title": "Nebra", "lang": True},
]
todo = [u["video_id"] for u, _ in binge.pending_questions(d, uploads, specs)]
assert todo == ["vidLang001", "vidStory01"], todo
d["asked"]["vidStory01"] = {"at": iso(minutes=1)}
assert [u["video_id"] for u, _ in binge.pending_questions(d, uploads, specs)] == ["vidLang001"]
d["since"] = iso(days=5)
old = [{"slug": "schlaf", "video_id": "vidAlt0001", "posted_at": iso(hours=40)}]
assert not binge.pending_questions(d, old, specs), "zu alte Uploads bekommen keine Frage"

# Playlist: nur Geschichten, meistgesehene oben
uploads2 = [{"slug": "zwei-brote", "video_id": "s1", "posted_at": iso(days=3)},
            {"slug": "leerer-server", "video_id": "h1", "posted_at": iso(days=3)},
            {"slug": "zwei-brote", "video_id": "s2", "posted_at": iso(days=2)},
            {"slug": "zwei-brote", "video_id": "s3", "posted_at": iso(days=1)},
            {"slug": "zwei-brote", "video_id": "c1", "posted_at": iso(days=1), "channel": "clips"}]
ids = binge.story_ids(uploads2, specs)
assert ids == ["s1", "s2", "s3"], ids
assert binge.wanted_order(ids, {"s1": 100, "s2": 2800, "s3": 400}) == ["s2", "s3", "s1"]
assert binge.wanted_order(ids, {}) == ids

# Gewinner je Video-Typ, frische Videos (unter 20 Stunden) zählen noch nicht
uploads3 = uploads2 + [{"slug": "schlaf", "video_id": "e1", "posted_at": iso(days=2)},
                       {"slug": "schlaf", "video_id": "e2", "posted_at": iso(hours=3)}]
w = binge.winners(uploads3, specs, {"s1": 300, "s2": 2800, "h1": 900, "e1": 2600, "e2": 9999})
assert [r["video_id"] for r in w] == ["s2", "e1", "h1"], w
assert w[0]["type"] == "Erzählte Geschichte"

# Lernmerkmal Gewinner-Nachbau
assert learn.features({**story, "nachbau": "geschichte-zwei-brote"}, {})["nachbau"] == "Gewinner nachgebaut"
assert learn.features(story, {})["nachbau"] == "eigener Aufbau"
assert learn.features(lang, {})["nachbau"] is None
assert learn.FEATURE_NAMES["nachbau"] == "Gewinner-Nachbau"

# Einstellungen und Übersicht
assert binge.set_settings(fragen=False)["fragen"] is False
o = binge.overview({"analytics_token": "x", "analytics_scopes": "youtube.force-ssl"}, uploads3, specs, {"s2": 2800})
assert o["can_ask"] and o["settings"]["playlist"] and o["winners"][0]["video_id"] == "s2"
assert o["playlist"]["url"] is None
print("binge ok")
