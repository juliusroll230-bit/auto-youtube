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
spec, st = firma.episode(41, None, comments, subs, today=dt.date(2026, 11, 11), own_channel="own", thema="autos")
assert not cartoon.validate(spec), cartoon.validate(spec)
a = st["themen"]["autos"]
assert a["tag"] == 1 and a["mitarbeiter"] == 41 and a["geld"] > 0
assert {t["name"] for t in st["team"]} == {"Tobi", "Mia", "LenaFaehrt"}, st["team"]
assert any("LenaFaehrt" in s["text"] for s in spec["segments"])
assert not any("Mechaniker" in s["text"] for s in spec["segments"]), "eigener Kanal stellt sich nicht selbst ein"
hud = [s["szene"] for s in spec["segments"] if s["szene"]["typ"] == "firma"]
assert hud and hud[0]["namen"][0] == "LenaFaehrt" and hud[0]["stufe"] == "fabrik"

# nächster Tag: gleiche Kommentare zählen nicht doppelt, Abos sinken -> Kündigung, Ausgaben nie unter null
spec2, st2 = firma.episode(38, st, comments, subs, today=dt.date(2026, 11, 12), own_channel="own", thema="autos")
assert st2["themen"]["autos"]["tag"] == 2 and not any("LenaFaehrt wollte" in s["text"] for s in spec2["segments"])
assert any("gekündigt" in s["text"] for s in spec2["segments"]) and st2["themen"]["autos"]["geld"] >= 0
assert not cartoon.validate(spec2), cartoon.validate(spec2)
# vier Firmen: jedes Ereignis, jede Größe, eigene Jobs, eigener Spielstand
for th in firma.THEME_ORDER:
    T = firma.THEMES[th]
    assert len(T["stufen"]) == len(firma.STUFEN) and T["events"] and T["jobs"]
    for tag in range(len(T["events"])):
        sp, _ = firma.episode(41, {"themen": {th: {"tag": tag, "mitarbeiter": 40, "geld": 500}}}, thema=th)
        assert not cartoon.validate(sp), (th, tag, cartoon.validate(sp))
    for n in (0, 5, 12, 199, 5000):
        sp, _ = firma.episode(n, {"themen": {th: {"tag": 6, "mitarbeiter": 3, "geld": 0}}}, comments, subs, thema=th)
        assert not cartoon.validate(sp), (th, n, cartoon.validate(sp))
        hud = [s["szene"] for s in sp["segments"] if s["szene"]["typ"] == "firma"]
        assert all(h["thema"] == th and 0 <= h["level"] <= 4 and h["stufe_label"] for h in hud)
    assert sp["slug"].startswith(f"firma-{th}-tag-7") and th in sp["firma_thema"]
astro = [{"id": "x1", "name": "Nora", "text": "Ich will Astronautin werden", "at": "1", "channel": "n"}]
assert firma.wishes(astro, jobs=firma.THEMES["rakete"]["jobs"])[0]["job"] == "Astronaut"
assert not firma.wishes(astro), "Autofirma hat keine Astronauten, der Wunsch wartet auf die Raketenfirma"
# alter Spielstand (nur Abo Motors) wird zur Autofirma, danach reihum Burger, Rakete, Games, Autos
old = {"tag": 1, "mitarbeiter": 41, "geld": 5600, "team": [], "used": []}
order, s0 = [], old
for k in range(5):
    sp, s0 = firma.episode(41, s0, today=dt.date(2026, 11, 12 + k))
    order.append(sp["firma_thema"])
assert order == ["burger", "rakete", "games", "autos", "burger"], order
assert s0["themen"]["autos"]["tag"] == 2 and s0["themen"]["autos"]["geld"] > 5600 and s0["themen"]["burger"]["tag"] == 2

# Einbau: zur Firmen-Sendezeit kommt die Folge vor die Warteschlange, sonst nicht
import server  # noqa: E402
import store  # noqa: E402
store.write("channel.json", {"id": "own", "subscribers": 41})
server.yt.recent_comments = lambda cfg, cid: comments
server.yt.public_subscribers = lambda cfg: subs
assert store.due_firma(None) is None and store.due_firma(20, store.now().replace(hour=19)) is None
key = store.due_firma(20, store.now().replace(hour=21))
assert key
file, sp = server.firma_episode()
assert os.path.basename(file).startswith("0000-firma-autos-tag-1") and sp["firma_state"]["themen"]["autos"]["mitarbeiter"] == 41
assert not store.queue_files(), "Firmen-Folge liegt nicht in der normalen Warteschlange"
server.firma_episode()
assert len(glob.glob(store.path("firma", "*.json"))) == 1, "alte Folge wird ersetzt"
store.write("firma.json", sp["firma_state"])
assert server.firma_episode() is None, "nur eine Folge pro Tag"
store.mark_slot(key, "firma_slots")
assert store.due_firma(20, store.now().replace(hour=21)) is None
print("ok")
