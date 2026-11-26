"""Kampagnen-Vorschläge (vorschlaege.py) mit nachgebauten Seiten: robots.txt, Übersicht (JSON-LD + Karten),
Kampagnenseiten, Filter (Shorts, Rate, Budget, Material, US-Pflicht), Reihenfolge (Deutsch, Nische), Push nur
einmal ab 2 $, Verknüpfen und Ausblenden. Läuft ohne Netz."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import store  # noqa: E402
import vorschlaege as vs  # noqa: E402
import whop  # noqa: E402

store.init()


def pid(n):
    return f"{n:02d}aaaaaa-0000-0000-0000-000000000000"


# id: (Titel, Übersicht-Budget, Übersicht-Rate, Detail-Angaben)
CAMPS = {
    1: ("[GERMANY] Blizzard WoW Forever", "$1.2K / $10K", "$2.50 /1K",
        dict(yt="2.50", budget="$1,200 / $10,000", status="Accepting clips", mat=4, extra="Clips for German players")),
    2: ("Energy Drink Clips", "$500 / $20K", "$1 – $3 /1K",
        dict(yt="3.00", budget="$500 / $20,000", status="Accepting clips", mat=2, extra="Lifestyle")),
    3: ("Minecraft Server Highlights", "$100 / $5K", "$1.20 /1K",
        dict(yt="1.20", budget="$100 / $5,000", status="Accepting clips", mat=1, extra="gaming clips")),
    4: ("US Podcast Clips", "$100 / $8K", "$4 /1K",
        dict(yt="4.00", budget="$100 / $8,000", status="Accepting clips", mat=3, extra="60%+ US audience required")),
    5: ("TikTok Only Dance", "$100 / $8K", "$2 /1K",
        dict(yt=None, budget="$100 / $8,000", status="Accepting clips", mat=3, extra="")),
    6: ("Almost Empty Budget", "$9K / $10K", "$3 /1K",
        dict(yt="3.00", budget="$9,000 / $10,000", status="Accepting clips", mat=3, extra="")),
    7: ("Cheap Rate Campaign", "$100 / $10K", "$0.50 /1K",
        dict(yt="0.50", budget="$100 / $10,000", status="Accepting clips", mat=3, extra="")),
    8: ("No Material Story Clips", "$100 / $10K", "$2 /1K",
        dict(yt="2.00", budget="$100 / $10,000", status="Accepting clips", mat=0, extra="")),
    9: ("Paused Space Facts", "$100 / $10K", "$2 /1K",
        dict(yt="2.00", budget="$100 / $10,000", status="Not accepting clips", mat=3, extra="")),
}


def overview_page(ids):
    items = [{"@type": "ListItem", "position": i + 1, "name": CAMPS[n][0],
              "url": f"https://contentrewards.com/c/campaigns/{pid(n)}"} for i, n in enumerate(ids)]
    ld = {"@context": "https://schema.org", "@graph": [{"@type": "ItemList", "itemListElement": items}]}
    cards = "".join(f"<div class='card'><h3>{CAMPS[n][0]}</h3><span>{CAMPS[n][1]}</span><span>{CAMPS[n][2]}</span></div>"
                    for n in ids)
    return (f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head>'
            f"<body><h1>Clipping campaigns</h1>{cards}<a href='?page=2'>Load more campaigns</a></body></html>")


def detail_page(n):
    title, _, _, d = CAMPS[n]
    rates = "<div>TikTok</div><div>Per 1K views</div><div>$1.00</div>"
    if d["yt"]:
        rates += f"<div>YouTube</div><div>Per 1K views</div><div>${d['yt']}</div>"
    mat = f"<div>Reference materials</div><div>{d['mat']} files</div>" if d["mat"] else ""
    return (f'<html><head><meta property="og:title" content="{title} by Brand {n}">'
            f'<meta property="og:description" content="About campaign {n}. {d["extra"]}"></head>'
            f"<body><div>{d['status']}</div>{rates}<div>Budget</div><div>{d['budget']}</div>{mat}"
            f"<p>{d['extra']}</p></body></html>")


ALL = list(CAMPS)
fetched = []


def fake_get(url):
    fetched.append(url)
    if url == vs.OVERVIEW:
        return overview_page(ALL)
    for n in CAMPS:
        if pid(n) in url:
            return detail_page(n)
    raise OSError("nicht da")


ROBOTS_OK = "User-agent: *\nDisallow: /api/\nDisallow: /home\n"
ROBOTS_NO = "User-agent: *\nDisallow: /c/\n"
pushed, slept = [], []

# 1. Hilfsfunktionen
assert vs._money("$1.6K") == 1600 and vs._money("$12.4K") == 12400 and vs._money("$2.50") == 2.5
over = vs.parse_overview(overview_page(ALL))
assert len(over) == 9 and over[0]["used"] == 1200 and over[0]["total"] == 10000 and over[0]["rate_max"] == 2.5, over[0]
assert over[1]["rate_min"] == 1 and over[1]["rate_max"] == 3, over[1]
try:
    vs.parse_overview("<html><body>Seite umgebaut</body></html>")
    raise AssertionError("ohne Kampagnenliste muss ein Fehler kommen")
except ValueError:
    pass
info = vs.parse_detail(detail_page(1))
assert info["materials"] == 4 and info["german"] and not info["us_only"] and info["status"] == "läuft", info
assert vs.parse_detail(detail_page(4))["us_only"]
assert vs.parse_detail(detail_page(9))["status"] == "pausiert"

# 2. robots.txt verbietet: nichts lesen, keine Vorschläge
d = vs.refresh(get=fake_get, get_robots=lambda: ROBOTS_NO, sleep=slept.append, alert=pushed.append)
assert not fetched and d["items"] == [] and "robots.txt" in d["error"], d

# 3. Normaler Lauf: Filter und Reihenfolge
d = vs.refresh(get=fake_get, get_robots=lambda: ROBOTS_OK, sleep=slept.append, alert=pushed.append)
assert d["error"] is None, d
ids = [x["id"] for x in d["items"]]
assert ids == [pid(1), pid(3), pid(2)], [x["title"] for x in d["items"]]   # Deutsch, dann Nische, dann Rate
# 6 (Budget) und 7 (Rate) fliegen schon in der Übersicht raus, ohne Seitenabruf
assert not any(pid(6) in u or pid(7) in u for u in fetched), fetched
assert len(fetched) <= 1 + vs.MAX_DETAILS and len(slept) == len(fetched) - 2, (fetched, slept)
first = d["items"][0]
assert first["rate"] == 2.5 and first["left"] == 8800 and first["materials"] == 4 and first["german"], first

# 4. Push nur ab 2 $ und nur einmal je Kampagne
assert sorted(x["id"] for x in pushed) == sorted([pid(1), pid(2)]), pushed
fetched.clear()
vs.refresh(get=fake_get, get_robots=lambda: ROBOTS_OK, sleep=slept.append, alert=pushed.append)
assert len(pushed) == 2, "jede Kampagne nur einmal melden"

# 5. Seite nicht erreichbar: alte Vorschläge bleiben, Fehler wird gezeigt
def broken(url):
    raise OSError("weg")


d = vs.refresh(get=broken, get_robots=lambda: ROBOTS_OK, sleep=slept.append, alert=pushed.append)
assert len(d["items"]) == 3 and "nicht erreichbar" in d["error"], d

# 6. Ausblenden: verschwindet und kommt nicht wieder
vs.hide(pid(2))
assert pid(2) not in [x["id"] for x in vs.overview()["items"]]
d = vs.refresh(get=fake_get, get_robots=lambda: ROBOTS_OK, sleep=slept.append, alert=pushed.append)
assert pid(2) not in [x["id"] for x in d["items"]]

# 7. Verknüpfen: legt die Kampagne an, tritt nicht bei, Vorschlag verschwindet
whop.fetch = fake_get
item = vs.link(pid(1))
assert item["id"] == pid(1) and whop.find(pid(1)) and item["status"] == "läuft", item
ov = vs.overview()
assert pid(1) not in [x["id"] for x in ov["items"]] and ov["every_hours"] == 6, ov
d = vs.refresh(get=fake_get, get_robots=lambda: ROBOTS_OK, sleep=slept.append, alert=pushed.append)
assert pid(1) not in [x["id"] for x in d["items"]], "verknüpfte Kampagnen nicht nochmal vorschlagen"
try:
    vs.link(pid(9))
    raise AssertionError("nur vorhandene Vorschläge verknüpfen")
except ValueError:
    pass

# 8. Nie automatisch beitreten oder einreichen: kein POST, keine anderen Seiten als Übersicht und Kampagnen
assert all(u == vs.OVERVIEW or "/c/campaigns/" in u for u in fetched), fetched
src = open(os.path.join(os.path.dirname(HERE), "vorschlaege.py"), encoding="utf-8").read()
assert "urlopen" not in src and "submit" not in src.lower(), "vorschlaege.py darf nur über whop.fetch lesen"

print("vorschlaege ok")
