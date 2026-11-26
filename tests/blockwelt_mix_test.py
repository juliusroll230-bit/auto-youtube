"""Täglicher Mix: von 15 Shorts sind 5 Blockwelt (1 von 3), egal wie viele alte Strichmännchen warten.
Dazu der Vorrat: fertig gerenderte Shorts stehen vorne und werden nicht doppelt gerendert."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="mix-test-")

import learn  # noqa: E402
import store  # noqa: E402

store.DATA = os.environ["DATA_DIR"]
for d in ("queue", "ready", "out", "posted"):
    os.makedirs(store.path(d), exist_ok=True)
store.save_config(post_hours=list(range(8, 23)), post_hours_weekend=list(range(8, 23)), block_per_day=5)   # 15 Plätze, 5 Blockwelt

# 30 alte Strichmännchen-Erklärvideos (die beste Nische) vor 10 Blockwelt-Skripten in der Dateireihenfolge
n = 0
for i in range(30):
    n += 1
    spec = {"slug": f"s{i}", "niche": "Erklären" if i % 3 else "Mystery", "title": f"S{i}", "stil": "cartoon",
            "segments": [{"text": "a"}]}
    json.dump(spec, open(store.path("queue", f"{n:04d}-s{i}.json"), "w"))
for i in range(10):
    n += 1
    spec = {"slug": f"b{i}", "niche": "Horror" if i % 2 else "Erklären", "title": f"B{i}", "stil": "cartoon",
            "welt": "block", "segments": [{"text": "a"}]}
    json.dump(spec, open(store.path("queue", f"{n:04d}-b{i}.json"), "w"))

order = store.planned_queue(posted=[])
day = [learn.is_block(s) for _, s in order[:15]]
assert sum(day) == 5, day
assert not any(day[i] and day[i + 1] for i in range(14)), day  # nie zwei Blockwelt direkt hintereinander

# Gestern lief nur Strichmännchen: der Anteil gleicht sich über das Fenster aus, ohne alles auf einmal
posted = [{"features": {"welt": "Strichmännchen 2D"}, "niche": "Erklären", "slot": "x"} for _ in range(14)]
order = store.planned_queue(posted=posted)
assert learn.is_block(order[0][1]), "nach 14 Strichmännchen kommt zuerst ein Blockwelt-Video"

# Ohne Blockwelt-Anteil (block_per_day 0): alte Reihenfolge des Lernmodus
store.save_config(block_per_day=0)
assert store.block_share(store.config()) is None
store.save_config(block_per_day=5)

# Vorrat: ein fertiges Video steht vorne, beim nächsten Rendern wird es übersprungen
first_file, first_spec = store.planned_queue(posted=[], with_ready=False)[0]
video = store.path("out", "fertig.mp4")
open(video, "wb").write(b"x")
store.add_ready(os.path.basename(first_file), {"video": video, "total": 20.0, "timings": [[0, 1]], "look": {},
                                               "spec": first_spec})
assert len(store.ready_items()) == 1
assert store.planned_queue(posted=[])[0][0] == first_file
assert first_file not in [f for f, _ in store.planned_queue(posted=[], with_ready=False)]
# Skript weg (z. B. abgelehnt): Vorrats-Video wird weggeräumt
os.remove(first_file)
assert store.ready_items() == [] and not os.path.exists(video)
print("blockwelt mix ok")
