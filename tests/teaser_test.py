import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_DIR"] = tempfile.mkdtemp()
import store, server, yt
store.init() if hasattr(store, "init") else None
os.makedirs(store.path("relax-teasers"), exist_ok=True)
open(os.path.join(store.path("relax-teasers"), "vid1.mp4"), "wb").write(b"x")
store.write("relax.json", {"uploads": [{"video_id": "vid1", "title": "T", "idea": None, "minutes": 60, "at": "2026-11-25", "teaser_pending": True}]})
calls = []
yt.upload = lambda cfg, path, spec: calls.append(path) or "tz1"
server.relax_retry_teasers({"relax_token": "x"})
u = store.read("relax.json", {})["uploads"][0]
assert u["teaser_id"] == "tz1" and not u["teaser_pending"] and len(calls) == 1, u
assert not os.path.exists(os.path.join(store.path("relax-teasers"), "vid1.mp4"))
print("teaser_test ok")
