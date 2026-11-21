"""Reiter „Insta & TikTok“: Zahlen von Buffer, Zuordnung zu eigenen Shorts, nächster Post, Profil-Checkliste (ohne Netz)."""
import datetime as dt
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import social  # noqa: E402
import store  # noqa: E402

now = dt.datetime(2026, 11, 21, 13, 0, tzinfo=store.TZ)
store.write("social.json", {"instagram": {"on": True, "last": {"at": (now - dt.timedelta(hours=1)).isoformat(), "title": "A"}},
                            "tiktok": {"on": True}})
social.buffer_save({"key": "k" * 40, "org": "o1", "channels": {"instagram": "c-ig", "tiktok": "c-tt"},
                    "names": {"instagram": "60sek", "tiktok": "60sek_tt"}})


def gql(key, q, v=None):
    if "posts(" in q:
        assert v["i"]["filter"]["channelIds"] == ["c-ig", "c-tt"]
        return {"posts": {"edges": [
            {"node": {"id": "p1", "channelService": "instagram", "status": "sent", "text": "Warum gähnen wir?\n#wissen",
                      "sentAt": "2026-11-20T15:00:00Z", "externalLink": "https://instagram.com/reel/x",
                      "metrics": [{"type": "views", "value": 1200}, {"type": "likes", "value": 80}, {"type": "comments", "value": 3}]}},
            {"node": {"id": "p2", "channelService": "tiktok", "status": "error", "text": "Kaputt", "createdAt": "2026-11-20T18:00:00Z",
                      "error": {"message": "Video zu kurz"}, "metrics": None}},
            {"node": {"id": "p3", "channelService": "tiktok", "status": "sent", "text": "TT", "sentAt": "2026-11-21T10:00:00Z",
                      "metrics": [{"type": "views", "value": 5000}, {"type": "favorites", "value": 300}]}},
        ]}}
    if "channels(" in q:
        return {"channels": [{"id": "c-ig", "service": "instagram", "avatar": "https://x/a.png", "isDisconnected": False},
                             {"id": "c-tt", "service": "tiktok", "avatar": "", "isDisconnected": True}]}
    raise AssertionError(q)


social._gql = gql
st = social.refresh_stats(force=True)
assert len(st["posts"]) == 3 and not st["errors"], st
posted = [{"video_id": "v1", "slug": "gaehnen", "title": "Warum gähnen wir?", "views": 900,
           "posted_at": (now - dt.timedelta(hours=20)).isoformat(),
           "auto": {"instagram": "p1", "instagram_at": "2026-11-20T16:00:00+01:00"}},
          {"video_id": "v2", "slug": "neu", "title": "Neu", "views": 100, "posted_at": (now - dt.timedelta(hours=5)).isoformat()}]
for vid in ("v1", "v2"):
    os.makedirs(os.path.dirname(store.share_path(vid)), exist_ok=True)
    open(store.share_path(vid), "wb").close()
o = social.overview(posted, now)
ig, tt = o["instagram"], o["tiktok"]
assert ig["connected"] and ig["buffer"] and ig["avatar"] == "https://x/a.png"
assert ig["posts"][0]["slug"] == "gaehnen" and ig["totals"] == {"views": 1200, "likes": 80, "comments": 3}
assert len(ig["posts"]) == 1  # nicht doppelt (Buffer-Post und eigener Upload sind derselbe)
assert tt["totals"] == {"views": 5000, "likes": 300} and tt["failed"][0]["error"] == "Video zu kurz" and tt["disconnected"]
assert ig["next"]["at"].startswith("2026-11-21T15:00")  # 3 h nach dem letzten Post
assert tt["next"]["title"] == "Warum gähnen wir?"  # v1 fehlt auf TikTok noch und ist der beste
assert ig["followers"] is None and ig["has_numbers"]
# Abends nichts mehr: nächster Post morgen 12 Uhr
late = now.replace(hour=22, minute=30)
assert social._next_time("tiktok", social.load(), posted, late).isoformat().startswith("2026-11-22T12:00")
# Checkliste bleibt erhalten, auch wenn andere Teile social.json speichern
assert social.set_done("bio", True) == ["bio"]
social.set_settings("instagram", per_day=3)
assert social.load()["profil_done"] == ["bio"]
assert social.set_done("bio", False) == []
try:
    social.set_done("quatsch", True)
    raise AssertionError("unbekannter Punkt")
except ValueError:
    pass
# Buffer kaputt: Fehler steht drin, kein Absturz
def boom(*a, **k):
    raise social.ApiError("Buffer kennt diesen Schlüssel nicht.")
social._gql = boom
st = social.refresh_stats(force=True)
assert "Buffer" in st["errors"]["buffer"]
assert social.overview(posted, now)["errors"]["buffer"]
# Ohne alles: nicht verbunden, keine Zahlen
social.buffer_disconnect()
o = social.overview([], now)
assert not o["tiktok"]["connected"] and not o["tiktok"]["has_numbers"] and o["tiktok"]["next"] is None
print("social_view ok")
