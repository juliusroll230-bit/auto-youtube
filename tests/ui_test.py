"""Oberfläche „wenige Knöpfe“: Tageszähler der Agenten, jede Ansicht hat ihren Satz, alte Links bleiben.
Läuft ohne Netz und ohne Browser."""
import datetime as dt
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import agents  # noqa: E402
import store  # noqa: E402

store.init()

# 1. „Was hat er heute geschafft?“: Zähler zählt nur erfolgreiche Läufe von heute
store.agent_done("analyst")
store.agent_done("analyst")
store.agent_done("analyst", error="kaputt")
run = store.state()["agent_runs"]["analyst"]
assert run["today"] == 2 and run["day"] == store.now().date().isoformat(), run

# Ein neuer Tag setzt den Zähler zurück
with store.LOCK:
    st = store.state()
    st["agent_runs"]["analyst"]["day"] = "2000-01-01"
    store.write("state.json", st)
store.agent_done("analyst")
assert store.state()["agent_runs"]["analyst"]["today"] == 1

# 2. overview liefert „today“, beim Publisher die heute hochgeladenen Videos
cfg = store.config()
now = store.now()
ctx = {"connected": True, "analytics": False, "working": set(), "queue": 0, "posted": 0, "favorite": None,
       "next_slot": now + dt.timedelta(hours=1), "now": now, "repo": False, "branding_at": None,
       "tasks": {}, "clips": {}, "posted_today": 7}
runs = {"analyst": {"at": now.isoformat(), "count": 9, "day": now.date().isoformat(), "today": 3},
        "designer": {"at": now.isoformat(), "count": 9, "day": "2000-01-01", "today": 5}}
try:
    ov = {a["id"]: a for a in agents.overview(cfg, runs, ctx)}
except KeyError as e:  # falls overview weitere Felder braucht: mit dem echten Dashboard prüfen
    raise SystemExit("overview braucht ctx-Feld " + str(e))
assert ov["analyst"]["today"] == 3, ov["analyst"]
assert ov["designer"]["today"] == 0, "gestern zählt nicht"
assert ov["publisher"]["today"] == 7, ov["publisher"]

# 3. Website: jede Ansicht hat ihren Satz „Hier siehst du …“, Erweitert existiert, alte Links bleiben
html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
intro = html[html.index("var INTRO = {"):]
intro = intro[:intro.index("};")]
keys = set(re.findall(r'"([a-z]+(?:/[a-z]+)?)"\s*:', intro))
pages = html[html.index("var PAGES = {"):html.index("var ALIAS")]
for page, body in re.findall(r'\n\s+(\w+): \{ name: "[^"]+", subs: \[(.*?)\] \}', pages):
    for sub in re.findall(r'\["(\w+)", "', body):
        assert page + "/" + sub in keys or page in keys, "Kein Satz für " + page + "/" + sub
assert '["erweitert", "Erweitert", ["#advBox"]]' in pages, "Kanäle > Erweitert fehlt"
for old in ["plan", "videos", "einreichen", "community"]:
    assert re.search(r"\b" + old + r': "', html[html.index("var ALIAS"):html.index("var ALIAS") + 600]), old
for fn in ["function uiBuild", "function uiRender", "function uiDots", "function uiFold", "function uiTerms", "function agentToday"]:
    assert fn in html, fn
# Nichts gelöscht: die alten Bedienelemente gibt es weiter (nur woanders)
for el in ['id="planForm"', 'id="postNow"', 'class="more-set', 'id="cqPer"', 'id="erList"']:
    assert el in html, el

print("ui_test ok")
