"""Prüft, ob die Zentrale eine Whop-Kampagnen-Seite (Content Rewards) richtig liest. Läuft ohne Netz."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import whop  # noqa: E402

page = open(os.path.join(HERE, "fixtures", "whop_campaign.html"), encoding="utf-8").read()
info = whop.parse(page)
assert info["title"] == "$1,000 Stanley Meng Streamer Clipping Campaign", info["title"]
assert info["brand"] == "ClippedIn", info["brand"]
assert info["rates"] == [{"platform": "TikTok", "rate": 1.0, "currency": "$"},
                         {"platform": "Instagram", "rate": 0.8, "currency": "$"}], info["rates"]
assert (info["min_payout"], info["max_payout"]) == (2.0, 100.0), info
assert (info["budget_used"], info["budget_total"]) == (679.0, 1000.0), info
assert info["status"] == "pausiert", info["status"]
assert "Stanley Meng's" in info["about"]

pid, url = whop.normalize("Schau mal: https://contentrewards.com/c/campaigns/8A91BC4A-feb8-455d-87de-95d82f69e5eb?ref=x")
assert pid == "8a91bc4a-feb8-455d-87de-95d82f69e5eb" and url.endswith(pid)
assert whop.normalize("https://contentrewards.com/discover/d61a073d-6a6a-48eb-a66f-5533f9213849")[0].startswith("d61a")
for bad in ("https://whop.com/contentrewards/", "https://youtube.com/watch?v=1", ""):
    try:
        whop.normalize(bad)
    except ValueError:
        continue
    raise AssertionError("hätte abgelehnt werden müssen: " + bad)
try:
    whop.parse("<html><head><title>Content Rewards</title></head></html>")
except ValueError:
    pass
else:
    raise AssertionError("leere Seite hätte abgelehnt werden müssen")

assert whop._num("1,000") == 1000 and whop._num("1.000,50") == 1000.5 and whop._num("0.80") == 0.8

os.makedirs(os.environ["DATA_DIR"], exist_ok=True)
item = whop.add(url, page=page)
assert whop.find(pid)["title"] == item["title"]
items = whop.refresh(get=lambda u: (_ for _ in ()).throw(OSError("offline")))
assert items[0]["error"] and items[0]["budget_total"] == 1000.0  # alte Werte bleiben
items = whop.refresh(get=lambda u: page.replace("Paused", "Active"))
assert items[0]["status"] == "läuft" and items[0]["error"] is None
s = whop.summary()
assert s[0]["budget_left"] == 321.0 and s[0]["videos"] == 0
whop.remove(pid)
assert whop.load() == []
print("whop ok")
