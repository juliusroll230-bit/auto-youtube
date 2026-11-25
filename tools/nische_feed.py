"""Sammelt die öffentlichen Aufrufe der Shorts (aus docs/videos.json) und schreibt docs/nische.json.

Läuft in GitHub Actions nach tools/channel_feed.py. Der RSS-Feed zeigt nur die neuesten 15 Videos, darum
merkt sich docs/statistik.json jedes Video mit seinen zuletzt gesehenen Aufrufen (Shorts sammeln die meisten
am ersten Tag). docs/nische.json sagt der täglichen Skript-Aufgabe, welche Titel-Muster und Themenfelder
gerade vorn liegen (grob, Median je Gruppe; die faire Rechnung macht die Zentrale im Nischen-Kompass).
"""
import glob
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import nische  # noqa: E402

DOCS = os.path.join(ROOT, "docs")
MIN_AGE_H = 20   # jüngere Videos haben ihre Aufrufe noch nicht gesammelt


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def specs_by_title():
    out = {}
    for path in glob.glob(os.path.join(ROOT, "seed", "*.json")):
        spec = load(path, None)
        if isinstance(spec, dict) and spec.get("title") and spec.get("laenge") != "lang":
            out[nische.plain_title(spec["title"]).lower()] = spec
    return out


def main(now=None):
    import datetime as dt
    now = now or dt.datetime.now(dt.timezone.utc)
    feed = load(os.path.join(DOCS, "videos.json"), {}).get("videos", [])
    stats = load(os.path.join(DOCS, "statistik.json"), {"videos": {}})
    for v in feed:
        if not v.get("id") or v["title"].startswith("Jeder Abonnent"):
            continue
        old = stats["videos"].get(v["id"], {})
        stats["videos"][v["id"]] = {"title": v["title"], "published": v.get("published"),
                                    "views": max(int(v.get("views") or 0), int(old.get("views") or 0)),
                                    "seen": now.isoformat(timespec="seconds")}
    rated = []
    for vid, v in stats["videos"].items():
        try:
            age = (dt.datetime.fromisoformat(v["seen"]) - dt.datetime.fromisoformat(v["published"])).total_seconds() / 3600
        except (KeyError, TypeError, ValueError):
            continue
        if age >= MIN_AGE_H:
            rated.append(v)
    out = nische.public_stats(rated, specs_by_title())
    out["updated_at"] = now.isoformat(timespec="seconds")
    out["hinweis"] = ("Grob: öffentliche Aufrufe nach ca. 1 Tag, Median je Gruppe. Faktor 1,3 = 30 % mehr als der Kanal-Median. "
                      "Erst ab 3 Videos je Gruppe gelistet. Genauer: Zentrale > Nischen-Kompass.")
    with open(os.path.join(DOCS, "statistik.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=0)
    with open(os.path.join(DOCS, "nische.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(out["videos"], "bewertete Videos in nische.json")


if __name__ == "__main__":
    main()
