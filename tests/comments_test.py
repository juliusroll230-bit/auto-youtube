"""Kommentar-Antworten: Einsortieren (antworten, für dich, überspringen), Tageslimit, Freigabe-Modus."""
import datetime as dt
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import comments  # noqa: E402
import store  # noqa: E402

C = comments.classify
assert C("Krasses Video 🔥") == ("reply", "praise")
assert C("😂😂😂") == ("reply", "praise")
assert C("Wusste ich nicht, danke!") == ("reply", "learned")
assert C("Ich hab jetzt Gänsehaut", "Horror") == ("reply", "scared")
assert C("Ist das echt passiert?", "Horror") == ("reply", "real_fiction")
assert C("Ist das echt passiert?", "Erzählte Geschichte") == ("reply", "real_story")
assert C("War das wirklich so?", "Mystery")[0] in ("reply", "todo")
assert C("Ist das wirklich passiert?", "Mystery") == ("reply", "real_mystery")
assert C("Ist das echt?", "Erklärvideo: Warum/Rätsel")[0] == "todo"
assert C("Das stimmt nicht, der Aufzug hat Bremsen")[0] == "todo"
assert C("Quelle?")[0] == "todo"
assert C("Wie lange dauert das genau?")[0] == "todo"
assert C("Teil 2 bitte!!") == ("reply", "part2")
assert C("Mach mal ein Video über schwarze Löcher") == ("reply", "wish")
assert C("Ist das eine KI Stimme") == ("reply", "ai")
assert C("Erster") == ("reply", "first")
assert C("Abonniere meinen Kanal") == ("skip", "Link oder Werbung")
assert C("schau hier www.gewinn.de") == ("skip", "Link oder Werbung")
assert C("du bist ein idiot") == ("skip", "Beleidigung")
assert C("so ein müll") == ("skip", "Kritik, keine Antwort nötig")
assert C("Ich werde in der Schule gemobbt")[0] == "todo"
assert C("x" * 300)[0] == "todo"
assert C("This is so scary, is it real?")[0] == "todo"
assert C("This is amazing, love this channel") == ("reply", "praise_en")

for kind, options in comments.REPLIES.items():
    for o in options:
        assert "http" not in o and "–" not in o and "—" not in o and len(o) < 140, o
        assert kind in comments.KIND_LABEL
assert comments.pick("praise", comments.REPLIES["praise"][:-1]) == comments.REPLIES["praise"][-1]

now = dt.datetime(2026, 11, 18, 12, 0, tzinfo=store.TZ)
fresh = "2026-11-18T09:00:00Z"
threads = [
    {"id": "a", "video_id": "v1", "author": "A", "author_channel": "ca", "text": "Mega gut", "at": fresh, "own_reply": False},
    {"id": "b", "video_id": "v1", "author": "B", "author_channel": "cb", "text": "Quelle?", "at": fresh, "own_reply": False},
    {"id": "c", "video_id": "v1", "author": "C", "author_channel": "cc", "text": "idiot", "at": fresh, "own_reply": False},
    {"id": "d", "video_id": "v1", "author": "Ich", "author_channel": "own", "text": "Danke", "at": fresh, "own_reply": False},
    {"id": "e", "video_id": "v1", "author": "E", "author_channel": "ce", "text": "cool", "at": fresh, "own_reply": True},
    {"id": "f", "video_id": "v1", "author": "F", "author_channel": "cf", "text": "cool", "at": "2026-11-01T09:00:00Z",
     "own_reply": False},
    {"id": "g", "video_id": "v2", "author": "A", "author_channel": "ca", "text": "Auch cool", "at": fresh, "own_reply": False},
    {"id": "h", "video_id": "v2", "author": "H", "author_channel": "ch", "text": "Mach mal was über Haie", "at": fresh,
     "own_reply": False},
]
vids = {"v1": {"title": "Horror", "type": "Horror"}, "v2": {"title": "Erklär", "type": "Erklärvideo: Warum/Rätsel"}}
d = comments.load()
d["settings"]["on"] = True
send = comments.process(threads, d, "own", vids, now=now)
assert [e["id"] for e, _ in send] == ["a", "h"], send   # g: gleiche Person schon dran
assert [t["id"] for t in d["todo"]] == ["b"]
assert d["log"][0]["id"] == "c" and not d["log"][0]["sent"]
assert "d" not in d["seen"] and "e" not in d["seen"] and "f" in d["seen"] and "g" not in d["seen"]
assert d["wishes"][0]["text"].startswith("Mach mal")
for entry, text in send:
    comments.record_sent(d, entry, text)
comments.save(d)
assert comments.replied_today(comments.load()) >= 0

# Tageslimit: bei 1 pro Tag und schon 1 gesendet kommt nichts mehr
d2 = comments.load()
d2["settings"].update(per_day=1)
d2["seen"] = {}
d2["log"] = [{"sent": True, "at": now.isoformat()}]
assert comments.process(threads, d2, "own", vids, now=now) == []

# Freigabe-Modus: Antworten werden Entwürfe statt gesendet
d3 = comments.load()
d3["seen"], d3["todo"], d3["log"] = {}, [], []
d3["settings"].update(mode="freigabe")
assert comments.process(threads, d3, "own", vids, now=now) == []
assert any(t.get("draft") for t in d3["todo"]) and any(t["id"] == "b" and not t.get("draft") for t in d3["todo"])

# Zugang: ohne force-ssl kein Antworten
assert comments.access({"refresh_token": "x", "analytics_token": "y", "analytics_scopes": "yt-analytics.readonly"}) == "zugang"
assert comments.access({"refresh_token": "x", "analytics_token": "y",
                        "analytics_scopes": "https://www.googleapis.com/auth/youtube.force-ssl"}) == "ok"
assert comments.error_text(Exception("insufficientPermissions"))[0] == "zugang"

# Zeitfenster
d4 = comments.load()
d4["settings"]["on"] = True
d4["status"] = {}
assert comments.due(d4, now) and not comments.due(d4, now.replace(hour=23))
print("comments ok")
