"""Schutz: höchstens max_shorts_day Shorts am Tag (23.11.2026, der 11. Upload am Tag bekam 0 Aufrufe)."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="cap-test-")
import store  # noqa: E402

store.DATA = os.environ["DATA_DIR"]
store.init()
cfg = store.config()
assert len(cfg["post_hours"]) == 7 and cfg["max_shorts_day"] == 7 and cfg["block_per_day"] == 2
today = store.now().strftime("%Y-%m-%dT10:00:00")
st = store.state()
st["firma_slots"] = ["F"]
st["uploads"] = [{"slot": "a", "posted_at": today}, {"slot": "b", "posted_at": today},
                 {"slot": "F", "posted_at": today},                       # Firmen-Folge zählt nicht
                 {"slot": "L", "posted_at": today, "lang": True},        # langes Video auch nicht
                 {"slot": "c", "posted_at": today, "kind": "clip"},      # Clip nicht
                 {"slot": "d", "posted_at": "2020-01-01T10:00:00"}]      # anderer Tag nicht
store.write("state.json", st)
assert store.shorts_today() == 2
print("cap ok")
import learn
_s = {"stil": "cartoon", "niche": "Erklären", "title": "X", "segments": [{"text": "a"}], "aktuell": True}
assert learn.features(_s, {})["aktuell"] == "aktuell" and learn.features({**_s, "aktuell": False}, {})["aktuell"] == "zeitlos"
assert learn.features({**_s, "laenge": "lang"}, {})["aktuell"] is None and "aktuell" in learn.FEATURE_NAMES
