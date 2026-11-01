"""Holt die neuesten Shorts des Kanals für die Homepage (docs/videos.json + docs/thumbs/).

Läuft in GitHub Actions (.github/workflows/kanal.yml). Nutzt nur den öffentlichen
RSS-Feed von YouTube, keinen API-Schlüssel. Vorschaubilder werden lokal abgelegt,
damit die Homepage beim Öffnen nichts von YouTube nachlädt.
"""
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

CHANNEL_ID = "UCElma5bjX-4XZGpKo9dheag"
FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "m": "http://search.yahoo.com/mrss/"}
NICHES = {"business": "Autos", "psychologie": "Psychologie", "geschichte": "Geschichte",
          "geld": "Geld", "geografie": "Geografie"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 shorts-homepage"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", namespaces=NS)
        title = (e.findtext("a:title", namespaces=NS) or "").replace("#shorts", "").strip()
        desc = e.findtext("m:group/m:description", namespaces=NS) or ""
        stats = e.find("m:group/m:community/m:statistics", NS)
        tags = [w[1:].lower() for w in desc.split() if w.startswith("#")]
        niche = next((NICHES[t] for t in tags if t in NICHES), "Wissen")
        out.append({
            "id": vid,
            "title": title,
            "text": desc.split("\n")[0].strip(),
            "niche": niche,
            "views": int(stats.get("views", 0)) if stats is not None else 0,
            "published": e.findtext("a:published", namespaces=NS),
        })
    return out


def main():
    videos = parse(get(FEED))
    if not videos:
        sys.exit("Feed ist leer, alte Liste bleibt.")
    thumbs = os.path.join(ROOT, "thumbs")
    os.makedirs(thumbs, exist_ok=True)
    keep = set()
    for v in videos:
        path = os.path.join(thumbs, v["id"] + ".jpg")
        keep.add(v["id"] + ".jpg")
        if not os.path.exists(path):
            try:
                data = get(f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg")
                with open(path, "wb") as f:
                    f.write(data)
            except OSError as err:
                print("Kein Vorschaubild für", v["id"], err)
        v["thumb"] = "thumbs/" + v["id"] + ".jpg" if os.path.exists(path) else None
    for name in os.listdir(thumbs):
        if name.endswith(".jpg") and name not in keep:
            os.remove(os.path.join(thumbs, name))
    data = {"channel": {"id": CHANNEL_ID, "handle": "@60SekundenWissen-s4i",
                        "url": "https://www.youtube.com/@60SekundenWissen-s4i"},
            "videos": videos}
    with open(os.path.join(ROOT, "videos.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(len(videos), "Videos gespeichert")


if __name__ == "__main__":
    main()
