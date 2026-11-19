"""Skripte mit "vorrang": true kommen in der Warteschlange vor allen anderen dran."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="vorrang-test-")

import store  # noqa: E402

store.DATA = os.environ["DATA_DIR"]
os.makedirs(store.path("queue"), exist_ok=True)
for name, extra in (("0001-a.json", {}), ("0002-b.json", {"vorrang": True}), ("0003-c.json", {})):
    spec = {"slug": name[5:-5], "niche": "Erklären", "title": name, "segments": [{"text": "a"}], **extra}
    with open(store.path("queue", name), "w", encoding="utf-8") as f:
        json.dump(spec, f)
order = [os.path.basename(f) for f, _ in store.planned_queue(posted=[])]
assert order[0] == "0002-b.json", order
assert sorted(order) == ["0001-a.json", "0002-b.json", "0003-c.json"]
print("vorrang ok")
