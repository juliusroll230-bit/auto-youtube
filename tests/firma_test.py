"""Firmen-Spiel: Skript aus echter Abozahl, Namen und Wunschjobs, Spielstand, Einbau in den Sendeplan."""
import datetime as dt
import glob
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import cartoon  # noqa: E402
import firma  # noqa: E402
import numerals  # noqa: E402

assert firma.words(41) == "einundvierzig" and firma.words(4100) == "viertausendeinhundert"
for n in (1, 7, 19, 41, 100, 999, 1001, 12345, 250000):
    assert numerals.parse(firma.words(n)) == n, n
assert firma.stufe(41)[0][1] == "fabrik" and firma.stufe(3)[0][1] == "garage" and firma.stufe(1500)[0][1] == "konzern"
assert firma.clean_name("@Max_Gamer2011") == "Max" and firma.clean_name("@xx") == "" and firma.clean_name("Nazi99") == ""

comments = [{"id": "c1", "name": "@LenaFaehrt", "text": "Ich will Testfahrerin sein!", "at": "1", "channel": "a"},
            {"id": "c2", "name": "Troll", "text": "ich will arsch sein", "at": "2", "channel": "b"},
            {"id": "c3", "name": "Kai", "text": "cooles Video", "at": "3", "channel": "c"},
            {"id": "c4", "name": "Boss", "text": "Ich will Mechaniker sein", "at": "4", "channel": "own"}]
w = firma.wishes(comments)
assert [x["job"] for x in w] == ["Testfahrer", "Mechaniker"], w

subs = [{"name": "Tobi", "channel": "t"}, {"name": "@Mia_2010", "channel": "m"}]
spec, st = firma.episode(41, None, comments, subs, today=dt.date(2026, 11, 11), own_channel="own")
assert not cartoon.validate(spec), cartoon.validate(spec)
assert st["tag"] == 1 and st["mitarbeiter"] == 41 and st["geld"] > 0
assert {t["name"] for t in st["team"]} == {"Tobi", "Mia", "LenaFaehrt"}, st["team"]
assert any("LenaFaehrt" in s["text"] for s in spec["segments"])
assert not any("Mechaniker" in s["text"] for s in spec["segments"]), "eigener Kanal stellt sich nicht selbst ein"
hud = [s["szene"] for s in spec["segments"] if s["szene"]["typ"] == "firma"]
assert hud and hud[0]["namen"][0] == "LenaFaehrt" and hud[0]["stufe"] == "fabrik"

# nächster Tag: gleiche Kommentare zählen nicht doppelt, Abos sinken -> Kündigung, Ausgaben nie unter null
spec2, st2 = firma.episode(38, st, comments, subs, today=dt.date(2026, 11, 12), own_channel="own")
assert st2["tag"] == 2 and not any("LenaFaehrt wollte" in s["text"] for s in spec2["segments"])
assert any("gekündigt" in s["text"] for s in spec2["segments"]) and st2["geld"] >= 0
assert not cartoon.validate(spec2), cartoon.validate(spec2)
for tag in range(len(firma.EVENTS)):  # jedes Ereignis einmal
    sp, _ = firma.episode(41, {"tag": tag, "mitarbeiter": 40, "geld": 500})
    assert not cartoon.validate(sp), (tag, cartoon.validate(sp))
for n in (0, 5, 12, 199, 5000):
    sp, _ = firma.episode(n, {"tag": 6, "mitarbeiter": 3, "geld": 0}, comments, subs)
    assert not cartoon.validate(sp), (n, cartoon.validate(sp))

# Einbau: zur Firmen-Sendezeit kommt die Folge vor die Warteschlange, sonst nicht
import server  # noqa: E402
import store  # noqa: E402
store.write("channel.json", {"id": "own", "subscribers": 41})
server.yt.recent_comments = lambda cfg, cid: comments
server.yt.public_subscribers = lambda cfg: subs
day = store.now().strftime("%Y-%m-%d")
assert server.firma_episode(day + "-09") is None
file, sp = server.firma_episode(day + "-17")
assert os.path.basename(file).startswith("0000-firma-tag-1") and sp["firma_state"]["mitarbeiter"] == 41
server.firma_episode(day + "-17")
assert len(glob.glob(store.path("queue", "0000-firma-*.json"))) == 1, "alte Folge wird ersetzt"
store.write("firma.json", sp["firma_state"])
assert server.firma_episode(day + "-17") is None, "nur eine Folge pro Tag"
print("ok")
