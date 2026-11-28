import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_DIR"] = tempfile.mkdtemp()
import store, server, yt
cfg = {"relax_token": "x"}
store.write("relax.json", {"uploads": [
    {"video_id": "old", "title": "A", "minutes": 180, "at": "2026-11-20", "teaser_id": "oldT"},
    {"video_id": "fine", "title": "B", "minutes": 60, "at": "2026-11-20"}]})
# 1) Kanal nicht bestätigt: 15 Minuten + Hinweis
yt.long_uploads_status = lambda c: "eligible"
assert server.relax_long_cap(cfg) == 15
info = store.read("relax.json", {})
assert info["verify"] and "youtube.com/verify" in info["notice"]
# 2) alte abgelehnte Videos werden gelöscht und aus der Liste genommen
deleted = []
yt.upload_states = lambda c, ids: {"old": {"upload": "rejected", "reason": "length"}, "fine": {"upload": "processed", "reason": ""}}
yt.delete_video = lambda c, v: deleted.append(v)
server.relax_check_uploads(cfg)
info = store.read("relax.json", {})
assert sorted(deleted) == ["old", "oldT"], deleted
assert [u["video_id"] for u in info["uploads"]] == ["fine"]
assert info["verify"]   # Hinweis bleibt
# 3) bestätigt: Begrenzung weg
st = store.state(); st["relax_cap"] = 15; store.write("state.json", st)
yt.long_uploads_status = lambda c: "allowed"
assert server.relax_long_cap(cfg) is None
assert not store.read("relax.json", {})["verify"] and store.state().get("relax_cap") is None
print("verify_test ok")
