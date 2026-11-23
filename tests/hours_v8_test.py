"""Gespeicherte 10 Sendezeiten werden einmalig auf 15 (8 bis 22 Uhr) umgestellt."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="hours-test-")

import store  # noqa: E402

store.DATA = os.environ["DATA_DIR"]
old = [8, 10, 12, 13, 15, 16, 17, 18, 20, 21]
json.dump({"post_hours": old, "post_hours_weekend": old, "hours_v7": True}, open(store.path("config.json"), "w"))
store.init()
cfg = store.config()
assert cfg["post_hours"] == store.DEFAULT_CONFIG["post_hours"], cfg["post_hours"]   # seit 23.11. (hours_v9): 7 Shorts am Tag
assert cfg["post_hours_weekend"] == store.DEFAULT_CONFIG["post_hours_weekend"]
assert len(cfg["post_hours"]) == 7 and cfg["block_per_day"] == 2
# Danach bleiben eigene Zeiten wieder stehen
store.save_config(post_hours=[9, 12])
store.init()
assert store.config()["post_hours"] == [9, 12]
print("hours v8 ok")
