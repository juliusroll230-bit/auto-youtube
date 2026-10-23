"""Fasst Warteschlange, Uploads, Statistiken und Kanal in content/dashboard.json zusammen.

Die Website liest nur diese eine Datei. Braucht nur die Python-Standardbibliothek.
"""
import datetime as dt
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "content")


def load(name, default):
    path = os.path.join(CONTENT, name)
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def card(spec):
    """Die Angaben, die die Website für eine Video-Karte braucht."""
    words = sum(len(s["text"].split()) for s in spec["segments"])
    return {
        "slug": spec["slug"],
        "title": spec["title"],
        "niche": spec["niche"],
        "style": spec.get("style", "gradient"),
        "colors": spec.get("colors", []),
        "car_color": spec.get("car_color", ""),
        "accent": spec.get("accent", ""),
        "emoji": spec["segments"][0].get("emoji", ""),
        "hook": spec["segments"][0]["text"],
        "seconds": round(words / 2.5 + 0.3 * len(spec["segments"])),
    }


def build():
    queue = [card(json.load(open(f, encoding="utf-8"))) for f in sorted(glob.glob(os.path.join(CONTENT, "queue", "*.json")))]
    state = load("state.json", {"uploads": []})
    stats = load("stats.json", {"videos": {}, "updated_at": None})
    posted = []
    for u in state["uploads"]:
        spec_path = os.path.join(CONTENT, "posted", "*" + u["slug"] + ".json")
        match = glob.glob(spec_path)
        base = card(json.load(open(match[0], encoding="utf-8"))) if match else {"slug": u["slug"], "title": u["title"]}
        posted.append({**base, "slot": u["slot"], "video_id": u["video_id"], **stats["videos"].get(u["video_id"], {})})
    return {
        "updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "stats_updated_at": stats.get("updated_at"),
        "slots": [int(h) for h in os.environ.get("POST_HOURS", "12,17,20").split(",")],
        "channel": load("channel.json", None),
        "connect": load("connect.json", {"status": "offen"}),
        "queue": queue,
        "posted": posted,
    }


def main():
    data = build()
    with open(os.path.join(CONTENT, "dashboard.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"dashboard.json: {len(data['queue'])} geplant, {len(data['posted'])} gepostet")


if __name__ == "__main__":
    main()
