"""Einreich-Station: geposteter Content-Rewards-Clip ist offen, wird eingereicht, Rückgängig macht ihn wieder offen.
Läuft ohne Netz und ohne YouTube."""
import datetime as dt
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import clips  # noqa: E402
import einreichen  # noqa: E402
import store  # noqa: E402
import whop  # noqa: E402

store.init()
PID = "8a91bc4a-feb8-455d-87de-95d82f69e5eb"
camp = {"id": PID, "url": "https://contentrewards.com/c/campaigns/" + PID, "title": "Test-Kampagne", "brand": "Marke",
        "rates": [{"platform": "YouTube", "rate": 2.0, "currency": "$"}], "currency": "$",
        "min_payout": 1.0, "max_payout": 50.0}
store.write(whop.FILE, [camp])

# Kampagne mit zwei Clips: einer schon gepostet, einer noch nicht
c = clips.create("WoW Test", "whop", rights=True)
now = store.now()
posted_at = (now - dt.timedelta(minutes=30)).isoformat(timespec="seconds")


def setup(x):
    x["program"] = PID
    x["clips"] = [{"n": 1, "title": "Clip eins", "status": "freigegeben"},
                  {"n": 2, "title": "Clip zwei", "status": "freigegeben"}]


clips.update(c["id"], setup)
store.write("stats.json", {"videos": {"vid1": {"views": 1500}, "vid2": {"views": 900}}})

# 1. Vor dem Posten: nichts offen, Einreichen nicht erlaubt
assert einreichen.overview()["open"] == 0
try:
    einreichen.submit(c["id"], 1)
except ValueError:
    pass
else:
    raise AssertionError("ungepostete Clips dürfen nicht eingereicht werden")

# 2. Publisher postet Clip 1 -> offen, Live-Feed meldet es
clips.mark_posted(c["id"], 1, "vid1")
camp_now = clips.load(c["id"])
assert einreichen.ready(camp_now, camp_now["clips"][0])
assert any("Clip bereit zum Einreichen" in e["text"] and e.get("agent") == "publisher" for e in store.state()["events"])
ov = einreichen.overview()
assert ov["open"] == 1 and ov["items"][0]["state"] == "offen", ov
it = ov["items"][0]
assert it["link"] == "https://youtube.com/shorts/vid1" and it["url"] == camp["url"] and it["views"] == 1500
assert it["campaign"] == "Test-Kampagne" and it["minutes"] is not None and not it["late"]
assert ov["campaigns"][0]["open"] == 1 and ov["campaigns"][0]["submitted"] == 0 and ov["campaigns"][0]["earned"] == 0

# 3. Älter als 2 Stunden -> orange (late)
later = now + dt.timedelta(hours=3)
assert einreichen.overview(now=later)["items"][0]["late"] is True

# 4. Einreichen -> eingereicht_at gesetzt, Geld nur für eingereichte Clips (1500/1000*2 = 3,00)
entry = einreichen.submit(c["id"], 1)
assert entry["eingereicht_at"], entry
ov = einreichen.overview()
assert ov["open"] == 0 and ov["items"][0]["state"] == "eingereicht" and ov["items"][0]["eingereicht_at"]
assert ov["campaigns"][0]["submitted"] == 1 and ov["campaigns"][0]["earned"] == 3.0, ov["campaigns"]
assert store.read(einreichen.FILE, {})["clips"][einreichen.key(c["id"], 1)]["eingereicht_at"]

# 5. Rückgängig -> wieder offen, eingereicht_at = null
einreichen.undo(c["id"], 1)
assert store.read(einreichen.FILE, {})["clips"][einreichen.key(c["id"], 1)]["eingereicht_at"] is None
ov = einreichen.overview()
assert ov["open"] == 1 and ov["campaigns"][0]["earned"] == 0

# 6. Nicht einreichen -> nicht mehr offen, zählt nicht als eingereicht; Rückgängig holt ihn zurück
einreichen.skip(c["id"], 1)
ov = einreichen.overview()
assert ov["open"] == 0 and ov["items"][0]["state"] == "nicht" and ov["campaigns"][0]["skipped"] == 1
einreichen.undo(c["id"], 1)
assert einreichen.overview()["open"] == 1

# 7. Clips ohne Whop-Kampagne erscheinen nicht; unbekannte Clips geben einen Fehler
c2 = clips.create("Eigenes Video", "upload", rights=True)
clips.update(c2["id"], lambda x: x.update(clips=[{"n": 1, "title": "Ohne Kampagne", "status": "freigegeben"}]))
clips.mark_posted(c2["id"], 1, "vid9")
assert not einreichen.ready(clips.load(c2["id"]), clips.load(c2["id"])["clips"][0])
assert all(x["id"] != c2["id"] for x in einreichen.overview()["items"])
for bad in ((c2["id"], 1), (c["id"], 99), ("gibt-es-nicht-0000", 1), (c["id"], "x")):
    try:
        einreichen.submit(*bad)
    except ValueError:
        continue
    raise AssertionError("hätte abgelehnt werden müssen: %r" % (bad,))

# 8. Server-Endpunkte (wie /api/whop/*): offen -> eingereicht -> Rückgängig
import json  # noqa: E402
import threading  # noqa: E402
import urllib.request  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

import server  # noqa: E402

server.PASSWORD = ""
srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = "http://127.0.0.1:%d/" % srv.server_address[1]


def post(path, body):
    req = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


code, j = post("api/einreichen/submit", {"id": c["id"], "n": 1})
assert code == 200 and j["entry"]["eingereicht_at"], (code, j)
ov = einreichen.overview()
assert ov["items"][0]["state"] == "eingereicht" and ov["open"] == 0
code, j = post("api/einreichen/undo", {"id": c["id"], "n": 1})
assert code == 200 and j["entry"]["eingereicht_at"] is None
code, j = post("api/einreichen/skip", {"id": c["id"], "n": 99})
assert code == 400 and j["error"]
srv.shutdown()
print("Einreich-Station ok")
