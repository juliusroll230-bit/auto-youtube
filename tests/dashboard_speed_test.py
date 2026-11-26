"""Zentrale lädt schnell, auch mit vielen Uploads (26.11.2026: Seite blieb leer, weil jeder Aufruf alle Skripte
für jeden Upload neu las). Prüft Skript-Suche, Zwischenspeicher und den schnelleren Vergleich mit Nachbartagen."""
import datetime as dt
import glob
import json
import math
import os
import random
import shutil
import sys
import tempfile
import time

os.environ["DATA_DIR"] = tempfile.mkdtemp()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import learn  # noqa: E402
import store  # noqa: E402

store.init()
for f in store.queue_files():   # init legt die Skripte aus seed/ in die Warteschlange: hier nur posted/ testen
    os.remove(f)
TZ = dt.timezone(dt.timedelta(hours=1))
now = dt.datetime(2026, 11, 26, 14, 0, tzinfo=TZ)
seeds = sorted(glob.glob(os.path.join(HERE, "..", "seed", "*.json")))[:300]
ups, stats = [], {}
for i, f in enumerate(seeds):
    shutil.copy(f, store.path("posted", os.path.basename(f)))
    spec = store.load_spec(f)
    at = (now - dt.timedelta(hours=(len(seeds) - i) * 1.5)).isoformat(timespec="seconds")
    ups.append({"slot": at, "slug": spec["slug"], "video_id": f"v{i:06d}", "title": spec["title"], "posted_at": at})
    stats[f"v{i:06d}"] = {"views": random.Random(i).randint(50, 3000)}
for i in range(300):   # Clipi-Clips: haben kein Skript in posted/ (vorher wurden dafür jedes Mal alle Dateien gelesen)
    at = (now - dt.timedelta(minutes=30 * i)).isoformat(timespec="seconds")
    ups.append({"slug": f"clip-{i}", "video_id": f"c{i:06d}", "title": "Clip", "posted_at": at, "kind": "clip", "channel": "clips"})
store.write("state.json", {"uploads": ups})
store.write("stats.json", {"videos": stats})

# 1. find_spec findet über Dateiname und Feld slug, queue/ geht vor posted/
first = store.load_spec(seeds[0])
assert store.find_spec(first["slug"])["title"] == first["title"]
assert store.find_spec("gibt-es-nicht") is None
q = dict(first, title="Neue Fassung in der Warteschlange")
with open(store.path("queue", "9999-" + first["slug"] + ".json"), "w", encoding="utf-8") as fh:
    json.dump(q, fh, ensure_ascii=False)
assert store.find_spec(first["slug"])["title"] == "Neue Fassung in der Warteschlange"
os.remove(store.path("queue", "9999-" + first["slug"] + ".json"))
assert store.find_spec(first["slug"])["title"] == first["title"]

# 2. Kopie: wer das Skript ändert, verändert nicht den Zwischenspeicher
s = store.find_spec(first["slug"])
s["title"] = "kaputt"
s["segments"].clear()
assert store.find_spec(first["slug"])["title"] == first["title"] and store.find_spec(first["slug"])["segments"]

# 3. geänderte Datei wird neu gelesen
p = store.path("posted", os.path.basename(seeds[0]))
d = store.load_spec(p)
d["title"] = "Geänderter Titel"
time.sleep(0.01)
with open(p, "w", encoding="utf-8") as fh:
    json.dump(d, fh, ensure_ascii=False)
os.utime(p, None)
assert store.find_spec(first["slug"])["title"] == "Geänderter Titel"

# 4. relative() liefert dasselbe wie der alte Vergleich mit allen Videos
posted = store.posted_items()
for v in posted:
    v.update(stats.get(v["video_id"], {}))
new = learn.relative(posted, now)
items = learn._rated(posted, now)
every = [sc for _, sc, _, _ in items]
for k, (v, sc, age_d, at) in enumerate(items):
    near = [s2 for j, (_, s2, _, at2) in enumerate(items)
            if j != k and abs((at2 - at).total_seconds()) <= learn.BASE_DAYS * 86400]
    if len(near) < learn.BASE_MIN:
        near = every[:k] + every[k + 1:]
    base = learn._median(near)
    lr = math.log(max(sc, 1.0) / max(base, 1.0)) if base else 0.0
    assert new[k][0] is v and abs(new[k][2] - lr) < 1e-9, k

# 5. die ganze Zentrale lädt schnell (vorher mehrere Sekunden schon hier, auf dem Server Minuten)
store.dashboard()
t = time.time()
dash = store.dashboard()
took = time.time() - t
assert len(dash["posted"]) == len(ups), len(dash["posted"])
assert took < 3, f"Zentrale braucht {took:.1f} s"
print(f"ok dashboard_speed ({took:.2f} s für {len(ups)} Uploads)")
