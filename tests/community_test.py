"""Community-Posts: Vorschläge aus echten Daten, Umfrage-Grenzen, Bilder, Abhaken, Wasserzeichen."""
import datetime as dt
import os
import sys
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import community  # noqa: E402
import store  # noqa: E402

store.init()
now = dt.datetime(2026, 11, 14, 10, 0)
posted = [{"video_id": "v1", "title": "Was passiert, wenn du tagelang nicht schläfst? 😵", "views": 1500,
           "posted_at": "2026-11-12T08:00:00"},
          {"video_id": "v2", "title": "Das Schiff, das niemand fand 🚢", "views": 200, "posted_at": "2026-11-13T08:00:00"},
          {"video_id": "c1", "kind": "clip", "title": "Clip", "views": 9999, "posted_at": "2026-11-13T08:00:00"}]
planned = [{"slug": "a", "title": "Warum gähnen wir, wenn andere gähnen? 🥱"},
           {"slug": "b", "title": "Was passiert, wenn " + "sehr " * 20 + "lange Titel kommen? 🤯"},
           {"slug": "c", "title": "Die Puppe im Keller (Teil 2) 👻"}]
P = community.suggestions(posted, planned, {"title": "60 Sekunden Wissen", "subscribers": 57}, [8, 11, 13, 16, 18], now, firma=True)
kinds = [p["id"].split("-")[0] for p in P]
assert kinds[:7] == ["frage", "heute", "wahl", "frag", "top", "meinung", "danke"], kinds
assert "kulisse" in kinds and "Um 11, 13, 16 Uhr" in P[1]["text"], P[1]["text"]
assert "firma" in kinds
for p in P:
    assert p["type"] in ("umfrage", "bild", "text") and p["text"] and p["why"]
    for o in p.get("options") or []:
        assert len(o) <= community.OPTION_MAX, o
    assert 2 <= len(p.get("options") or [1, 2]) <= 5
top = next(p for p in P if p["id"].startswith("top"))
assert "v1" in top["text"] and "1.500" in top["text"], top["text"]  # Clips zählen nicht
assert "(Teil" not in " ".join(next(p for p in P if p["id"].startswith("wahl"))["options"])
assert "heute" in P[0]["text"], P[0]["text"]  # Erstes geplantes Video kommt heute um 11 Uhr
assert next(p for p in P if p["id"].startswith("danke"))["img"]["big"] == "50"
# gleicher Tag = gleiche Vorschläge, anderer Mischwert = andere Meinungsfrage
assert [p["id"] for p in P] == [p["id"] for p in community.suggestions(posted, planned, {"subscribers": 57}, [8, 11, 13, 16, 18], now, firma=True)]
assert community.suggestions([], [], {}, [], now, shuffle=1)[0]["text"] != community.suggestions([], [], {}, [], now)[0]["text"]
# ohne Daten: wenigstens eine Meinungsfrage
assert sorted(p["type"] for p in community.suggestions([], [], {}, [], now)) == ["text", "text", "umfrage"]
posted[0]["sentences"] = ["Du bleibst wach.", "Nach einem Tag wirst du langsam.", "Dann wird es schlimm."]
W = community.suggestions(posted, [], {}, [], now)
assert any(p["id"].startswith("wusst") and "Nach einem Tag" in p["text"] and "v1" in p["text"] for p in W)

for p in P:
    if p["type"] == "bild":
        img = community.render(p)
        assert img.size == (1080, 1080)
wm = community.watermark()
assert wm.size == (300, 300) and wm.mode == "RGBA" and wm.getpixel((0, 0))[3] == 0

pid = community.overview(store, posted, planned, {}, [8, 11], firma=False)["posts"][0]["id"]
community.mark(store, pid)
assert community.overview(store, posted, planned[2:], {}, [8, 11], firma=False)["posts"][0]["done"], "Haken geht verloren"
o = community.overview(store, posted, planned, {}, [8, 11], firma=False)
assert o["week"] == 1 and "posts" in o and o["per_day"] == 3
plan = [p for p in o["posts"] if p.get("hour")]
assert [p["id"] for p in community.overview(store, posted, planned[1:], {}, [8, 11], firma=False)["posts"]] == [p["id"] for p in o["posts"]], "Tagesplan muss fest bleiben"
assert [p["hour"] for p in plan] == [10, 14, 19] and len({p["type"] for p in plan}) == 3, plan
community.set_per_day(store, 5)
o = community.overview(store, posted, planned, {}, [8, 11, 13, 16, 18], firma=True)
assert [p["hour"] for p in o["posts"] if p.get("hour")] == [9, 12, 15, 19, 21]
assert community.post_times(3, [10, 14]) == [11, 15, 19]  # nie zur gleichen Stunde wie ein Short
for bad in (0, 6, "x"):
    try:
        community.set_per_day(store, bad)
    except ValueError:
        pass
    else:
        raise AssertionError("ungültige Anzahl angenommen")
try:
    community.mark(store, "../x")
except ValueError:
    pass
else:
    raise AssertionError("ungültige ID angenommen")
community.reshuffle(store)
assert community.load(store)["shuffle"] == 1
d = store.dashboard()
assert "posts" in d["community"], d["community"]
print("Community-Posts ok:", ", ".join(kinds))
