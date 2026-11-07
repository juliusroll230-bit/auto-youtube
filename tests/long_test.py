"""Prüft die langen Videos: Skript-Regeln, eigene Warteschlange, Wochentage. Ohne Chromium/ffmpeg:
    python tests/long_test.py
"""
import datetime as dt
import json
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="long-test-")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cartoon  # noqa: E402
import store  # noqa: E402

spec = json.load(open(os.path.join(ROOT, "seed", "0112-erklaert-kuehlschrank-lang.json"), encoding="utf-8"))
assert cartoon.is_long(spec) and cartoon.validate(spec) == [], cartoon.validate(spec)
short = dict(spec, segments=spec["segments"][:8])
assert any("1200" in e for e in cartoon.validate(short)), "zu kurz für ein langes Video"
assert any("höchstens 95" in e for e in cartoon.validate({k: v for k, v in spec.items() if k != "laenge"}))

assert store.long_days(4) == [0, 2, 4, 5] and store.long_days(0) == [] and len(store.long_days(7)) == 7
store.init()
mon = store.TZ.localize(dt.datetime(2026, 11, 9, 17, 0)) if hasattr(store.TZ, "localize") else dt.datetime(2026, 11, 9, 17, 0, tzinfo=store.TZ)
assert store.due_long(4, at=mon) is None, "vor 19 Uhr noch nicht"
assert store.due_long(4, at=mon.replace(hour=19)) == "2026-11-09"
assert store.due_long(4, at=mon.replace(hour=19, day=10)) is None, "Dienstag ist kein Tag für lange Videos"
store.mark_slot("2026-11-09", "long_slots")
assert store.due_long(4, at=mon.replace(hour=19)) is None, "heute schon gepostet"

short_spec = {"slug": "kurz-test", "title": "t", "niche": "Geld", "segments": [{"text": "Hallo."}]}
open(store.path("queue", "0001-kurz.json"), "w").write(json.dumps(short_spec))
open(store.path("queue", "0002-lang.json"), "w").write(json.dumps(spec))
shorts = [s["slug"] for _, s in store.planned_queue()]
assert "kurz-test" in shorts and spec["slug"] not in shorts, "Shorts bekommen kein langes Video"
longs = [s["slug"] for _, s in store.planned_queue(long=True)]
assert spec["slug"] in longs and "kurz-test" not in longs
print("ok: lange Videos")
