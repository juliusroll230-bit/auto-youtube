"""Schreibt docs/vorbilder.json: Muster und Trends der Vorbild-Kanäle (siehe vorbilder.py).

Läuft in GitHub Actions (.github/workflows/kanal.yml), höchstens alle 12 Stunden neu.
Die tägliche Skript-Aufgabe liest die Datei (Regel in CLAUDE.md).
"""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import vorbilder  # noqa: E402

DOCS = os.path.join(HERE, "..", "docs")
OUT = os.path.join(DOCS, "vorbilder.json")


def main():
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
        if not vorbilder.due(old) and "--force" not in sys.argv:
            print("Vorbilder sind noch frisch, nichts zu tun.")
            return
    except (OSError, ValueError):
        pass
    try:
        with open(os.path.join(DOCS, "videos.json"), encoding="utf-8") as f:
            ours = [v["title"] for v in json.load(f).get("videos", [])]
    except (OSError, ValueError, KeyError):
        ours = []
    feeds = vorbilder.fetch_all()
    if not any(v for v in feeds.values()):
        sys.exit("Kein Vorbild-Feed erreichbar, alte Datei bleibt.")
    data = vorbilder.build(feeds, ours, dt.datetime.now(dt.timezone.utc))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(sum(1 for c in data["channels"] if c["ok"]), "Vorbilder gelesen,", len(data["trend"]), "Trend-Videos")


if __name__ == "__main__":
    main()
