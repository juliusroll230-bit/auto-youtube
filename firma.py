"""Firmen-Spiel: "Für jeden Abonnenten stelle ich einen Mitarbeiter in meiner Firma ein".

Vier ganz verschiedene Firmen wechseln sich ab (Autofirma, Burgerladen, Raketenfirma, Spielestudio, siehe THEMES),
damit man sieht, welche am besten ankommt.

Einmal am Tag zusätzlich zu den normalen Shorts (ab firma_hour, Standard 20 Uhr) baut die Zentrale einen Cartoon-Short:
- Mitarbeiter = echte Abozahl des Kanals (aus channel.json, alle 20 Minuten aktualisiert)
- jeder Mitarbeiter bringt 100 € am Tag, das Spielgeld landet auf dem Firmenkonto (firma.json)
- Zuschauer schreiben ihren Wunschjob in die Kommentare ("Ich will Zeichner sein"), die Firma stellt
  sie mit Namen ein (nur Jobs aus der Liste unten, damit nichts Unpassendes ins Bild kommt)
- ab 10, 40, 200 und 1000 Abos zieht die Firma um (bei der Autofirma: Garage, Werkstatt, Fabrik, Großfabrik, Konzern)

Spielgeld ist erfunden, das Video sagt das nicht anders. Test: python firma.py 41 ausgabe/ '{}' burger
"""
import datetime as dt
import json
import re
import sys

PER_HEAD = 100  # Spielgeld pro Mitarbeiter und Tag
FIRMA = "Autofirma"
FIRMENNAME = "Abo Motors"

STUFEN = [  # (ab Mitarbeitern, Schlüssel für die Szene, wie man es spricht)
    (0, "garage", "eine Hinterhof-Garage"),
    (10, "werkstatt", "eine richtige Werkstatt"),
    (40, "fabrik", "eine Autofabrik mit Fließband"),
    (200, "grossfabrik", "eine Großfabrik mit zwei Fließbändern"),
    (1000, "konzern", "einen Weltkonzern mit eigener Teststrecke"),
]

# Wunschjobs: Stichwort im Kommentar -> (Jobname, Emoji). Nur diese Jobs werden vergeben.
JOBS = [
    (r"mechanik|schrauber|werkstatt", "Mechaniker", "🔧"),
    (r"lackier|maler|farbe", "Lackierer", "🎨"),
    (r"schwei(ß|ss)", "Schweißer", "🔥"),
    (r"testfahrer|fahrer|rennfahrer|pilot|drift", "Testfahrer", "🏎️"),
    (r"designer|zeichner|künstler|kuenstler|grafik", "Designer", "✏️"),
    (r"ingenieur|erfinder|techniker|entwickler|tüftler", "Ingenieur", "⚙️"),
    (r"programmier|coder|informatik|roboter|hacker", "Roboter-Programmierer", "🤖"),
    (r"verkäufer|verkaeufer|verkauf|händler|haendler|autohaus", "Verkäufer", "💼"),
    (r"manager|chef|boss|leiter|ceo", "Manager", "📊"),
    (r"hausmeister|putz", "Hausmeister", "🧹"),
    (r"koch|köchin|koechin|kantine|bäcker|baecker", "Kantinen-Koch", "🍕"),
    (r"security|wachmann|sicherheit|bodyguard|türsteher", "Security", "🛡️"),
    (r"praktikant|azubi|lehrling", "Praktikant", "☕"),
    (r"youtuber|streamer|influencer|marketing|werbung", "Werbe-Star", "🎥"),
]
WISH = re.compile(r"\b(will|möchte|moechte|wäre|waere|werde|werden|bin|als|job|arbeite|einstellen|nimm|sein)\b", re.I)
BAD = re.compile(r"https?://|www\.|\.com|\.de\b|fick|fuck|scheiß|scheiss|hure|nazi|hitler|nigg|schwuchtel|arsch|"
                 r"wichs|porn|sex|kill|tot\b|bitch|spast|behindert|opfer", re.I)

ONES = ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf", "zwölf",
        "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn"]
TENS = ["", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig", "achtzig", "neunzig"]

# Was in der Firma passiert, je Tag ein anderes Ereignis: (Satz, Emoji, Geld, Gefühl, Aktion, Schild)
EVENTS = [
    ("Unser erstes Auto ist verkauft, das bringt {b} Euro extra!", "🚗", 1500, "freude", "jubelt", "Verkauft!"),
    ("Ein Roboterarm dreht durch und lackiert die Wand, Reparatur: {b} Euro.", "🤖", -600, "staunen", "schockiert", "Roboter-Chaos"),
    ("Ein Rennteam bestellt drei Sportwagen und zahlt {b} Euro!", "🏁", 2500, "staunen", "jubelt", "Großauftrag"),
    ("Ein Reifen platzt beim Test, neue Reifen kosten {b} Euro.", "🛞", -400, "angst", "zittert", "Peng!"),
    ("Ich kaufe eine neue Lackieranlage für {b} Euro.", "🎨", -800, "cool", "zeigt", "Neue Anlage"),
    ("Ein Influencer fährt unser Auto im Video, wir verdienen {b} Euro!", "🎥", 2000, "freude", "jubelt", "Viral!"),
    ("Der Strom fällt aus, das Fließband steht still, Verlust: {b} Euro.", "⚡", -700, "wut", "zittert", "Stromausfall"),
    ("Unser Auto gewinnt den Preis für das schönste Design: {b} Euro!", "🏆", 3000, "staunen", "jubelt", "Preis!"),
    ("Pizza für die ganze Fabrik, das kostet {b} Euro.", "🍕", -300, "freude", "winkt", "Pizza-Party"),
    ("Ein Testfahrer landet im See, das Abschleppen kostet {b} Euro.", "🌊", -900, "angst", "faellt", "Oh nein!"),
]


COMMON_JOBS = [  # gibt es in jeder Firma
    (r"manager|chef|boss|leiter|ceo", "Manager", "📊"),
    (r"hausmeister|putz", "Hausmeister", "🧹"),
    (r"security|wachmann|sicherheit|bodyguard|türsteher", "Security", "🛡️"),
    (r"praktikant|azubi|lehrling", "Praktikant", "☕"),
]

# Vier ganz verschiedene Firmen. Jeden Abend kommt die nächste dran (THEME_ORDER), jede hat ihren eigenen Spielstand,
# damit man nach ein paar Tagen sieht, welche Firma die meisten Aufrufe holt (Slug: firma-<thema>-tag-N).
THEMES = {
    "autos": {
        "firma": FIRMA, "name": FIRMENNAME, "in": "in meiner Autofirma", "icon": "🚗", "ziel": "🏭",
        "arbeit": "Jeder baut Autos für hundert Euro am Tag", "beispiel": "Ich will Testfahrer sein",
        "stufen": [(s[2], lab) for s, lab in zip(STUFEN, ["HINTERHOF-GARAGE", "WERKSTATT", "AUTOFABRIK", "GROSSFABRIK", "WELTKONZERN"])],
        "jobs": JOBS, "events": EVENTS, "tags": ["autos", "autofirma"], "colors": ["#1f2440", "#3f8cff"],
    },
    "burger": {
        "firma": "Burgerladen", "name": "Abo Burger", "in": "in meinem Burgerladen", "icon": "🍔", "ziel": "🍔",
        "arbeit": "Jeder brät Burger für hundert Euro am Tag", "beispiel": "Ich will Grillmeister sein",
        "stufen": [("eine kleine Imbissbude", "IMBISSBUDE"), ("ein richtiger Burgerladen", "BURGERLADEN"),
                   ("ein großes Burger-Restaurant", "BURGER-RESTAURANT"), ("ein Burger-Palast mit Riesen-Burger auf dem Dach", "BURGER-PALAST"),
                   ("ein Burger-Imperium", "BURGER-IMPERIUM")],
        "jobs": [(r"grill|burger|brat|brät", "Grillmeister", "🍔"), (r"pommes|fritt", "Pommes-Profi", "🍟"),
                 (r"koch|köchin|koechin|küche|kueche", "Koch", "🍳"), (r"kellner|bedienung|service", "Kellner", "🍽️"),
                 (r"kasse|kassier", "Kassierer", "💶"), (r"liefer|fahrer|kurier", "Lieferfahrer", "🛵"),
                 (r"bäcker|baecker|brötchen|broetchen", "Bäcker", "🥯"), (r"shake|eis|barkeeper|getränk|getraenk", "Shake-Mixer", "🥤"),
                 (r"tester|probier|vorkoster", "Burger-Tester", "😋")] + COMMON_JOBS,
        "events": [
            ("Ein Food-Blogger lobt unseren Burger, das bringt {b} Euro extra!", "🍔", 2000, "freude", "jubelt", "Viral!"),
            ("Die Fritteuse qualmt, die Reparatur kostet {b} Euro.", "🔥", -700, "angst", "zittert", "Qualm!"),
            ("Eine Schulklasse bestellt hundert Burger und zahlt {b} Euro!", "🎒", 2500, "staunen", "jubelt", "Großauftrag"),
            ("Der Kühlschrank geht kaputt, neues Fleisch kostet {b} Euro.", "🧊", -500, "wut", "zittert", "Kühlschrank kaputt"),
            ("Wir erfinden den Dreifach-Käse-Burger, alle wollen ihn: {b} Euro!", "🧀", 1800, "freude", "jubelt", "Neuer Burger"),
            ("Ein Lieferroller hat einen Platten, das kostet {b} Euro.", "🛵", -300, "traurig", "steht", "Platten!"),
            ("Wir gewinnen den Preis für die besten Pommes: {b} Euro!", "🍟", 3000, "staunen", "jubelt", "Preis!"),
            ("Ich kaufe einen riesigen neuen Grill für {b} Euro.", "♨️", -800, "cool", "zeigt", "Neuer Grill"),
            ("Eine Möwe klaut einen Burger, der Ersatz kostet {b} Euro.", "🐦", -200, "wut", "zittert", "Möwen-Alarm"),
            ("Ein Promi feiert bei uns Geburtstag und zahlt {b} Euro!", "🎉", 2200, "freude", "jubelt", "Party!"),
        ],
        "tags": ["burger", "restaurant"], "colors": ["#d8312b", "#ffcf3f"],
    },
    "rakete": {
        "firma": "Raketenfirma", "name": "Abo Space", "in": "in meiner Raketenfirma", "icon": "🚀", "ziel": "🪐",
        "arbeit": "Jeder baut Raketen für hundert Euro am Tag", "beispiel": "Ich will Astronaut sein",
        "stufen": [("eine Raketen-Garage", "RAKETEN-GARAGE"), ("ein echtes Testgelände", "TESTGELÄNDE"),
                   ("eine Raketenbasis mit Startrampe", "RAKETENBASIS"), ("ein Weltraumbahnhof mit zwei Raketen", "WELTRAUMBAHNHOF"),
                   ("ein Konzern, der zum Mars fliegt", "MARS-KONZERN")],
        "jobs": [(r"astronaut|raumfahrer|kosmonaut|weltall|weltraum", "Astronaut", "🪐"),
                 (r"ingenieur|techniker|tüftler|tueftler|erfinder|konstrukteur", "Raketen-Ingenieur", "🛠️"),
                 (r"pilot|flieger|fliegen", "Pilot", "✈️"), (r"countdown|leitstand|mission|kontrolle", "Missionsleiter", "🎧"),
                 (r"forscher|wissenschaft|physik|chemie|astronom", "Forscher", "🔭"),
                 (r"programmier|coder|informatik|hacker|computer", "Programmierer", "💻"),
                 (r"mechanik|schrauber", "Mechaniker", "🔧"), (r"koch|köchin|essen", "Weltraum-Koch", "🍝")] + COMMON_JOBS,
        "events": [
            ("Unsere Testrakete fliegt bis in die Wolken, ein Sender zahlt {b} Euro für das Video!", "🚀", 2000, "freude", "jubelt", "Abheben!"),
            ("Die Testrakete landet im Ententeich, das Bergen kostet {b} Euro.", "🦆", -600, "staunen", "zittert", "Platsch!"),
            ("Eine Firma bestellt einen Wettersatelliten für {b} Euro!", "🛰️", 3000, "staunen", "jubelt", "Großauftrag"),
            ("Ein Gewitter stoppt den Countdown, Verlust: {b} Euro.", "⛈️", -500, "wut", "zittert", "Abbruch!"),
            ("Ich kaufe einen neuen Treibstofftank für {b} Euro.", "⛽", -800, "cool", "zeigt", "Neuer Tank"),
            ("Wir finden einen Mini-Meteoriten und verkaufen ihn für {b} Euro!", "☄️", 1500, "staunen", "jubelt", "Meteorit!"),
            ("Ein Bolzen fehlt, die ganze Rakete muss zerlegt werden: {b} Euro.", "🔩", -700, "angst", "zittert", "Wo ist er?"),
            ("Wir gewinnen den Preis für die schnellste Rakete: {b} Euro!", "🏆", 2500, "staunen", "jubelt", "Preis!"),
            ("Astronauten-Eis für alle, das kostet {b} Euro.", "🍦", -300, "freude", "winkt", "Eis-Party"),
            ("Ein Museum kauft unsere alte Rakete für {b} Euro!", "🏛️", 1800, "freude", "jubelt", "Verkauft!"),
        ],
        "tags": ["rakete", "weltraum"], "colors": ["#14183d", "#7fe3ff"],
    },
    "games": {
        "firma": "Spielestudio", "name": "Abo Games", "in": "in meinem Spielestudio", "icon": "🎮", "ziel": "🕹️",
        "arbeit": "Jeder entwickelt Spiele für hundert Euro am Tag", "beispiel": "Ich will Spieletester sein",
        "stufen": [("ein Studio im Kinderzimmer", "KINDERZIMMER"), ("ein kleines Indie-Studio", "INDIE-STUDIO"),
                   ("ein großes Game-Studio", "GAME-STUDIO"), ("ein Game-Gigant mit Pokal-Regal", "GAME-GIGANT"),
                   ("ein Gaming-Imperium", "GAMING-IMPERIUM")],
        "jobs": [(r"tester|zocker|gamer|zock|spielen", "Spieletester", "🎮"),
                 (r"programmier|coder|informatik|hacker|entwickler", "Programmierer", "💻"),
                 (r"zeichner|designer|künstler|kuenstler|grafik|animat", "Grafiker", "🎨"),
                 (r"level|map|welten|baumeister", "Level-Designer", "🧱"), (r"musik|sound|komponist|dj", "Sound-Designer", "🎵"),
                 (r"streamer|youtuber|influencer|marketing|werbung", "Streamer", "📹"), (r"e-?sport|profi|pro gamer", "E-Sportler", "🏆"),
                 (r"sprecher|stimme|synchron", "Sprecher", "🎙️"), (r"bug|fehler|qualität", "Bug-Jäger", "🐛")] + COMMON_JOBS,
        "events": [
            ("Unser erstes Spiel geht viral, das bringt {b} Euro!", "🎮", 2000, "freude", "jubelt", "Viral!"),
            ("Ein Bug lässt alle Figuren fliegen, das Reparieren kostet {b} Euro.", "🐛", -600, "staunen", "zittert", "Bug!"),
            ("Ein großer Verlag will unser Spiel und zahlt {b} Euro!", "🤝", 3000, "staunen", "jubelt", "Großauftrag"),
            ("Der Server stürzt ab, Verlust: {b} Euro.", "💥", -700, "wut", "zittert", "Server down"),
            ("Ich kaufe Gaming-Stühle für alle, das kostet {b} Euro.", "💺", -800, "cool", "zeigt", "Neue Stühle"),
            ("Ein Streamer spielt unser Spiel live, wir verdienen {b} Euro!", "📹", 1800, "freude", "jubelt", "Live!"),
            ("Die Kaffeemaschine explodiert, eine neue kostet {b} Euro.", "☕", -300, "angst", "zittert", "Kaffee-Notstand"),
            ("Unser Spiel gewinnt den Preis für das beste Indie-Spiel: {b} Euro!", "🏆", 2500, "staunen", "jubelt", "Preis!"),
            ("Pizza-Nacht vor dem Release, das kostet {b} Euro.", "🍕", -300, "freude", "winkt", "Pizza-Nacht"),
            ("Ein Turnier mit unserem Spiel bringt {b} Euro Eintritt!", "🏟️", 1500, "freude", "jubelt", "Turnier!"),
        ],
        "tags": ["gaming", "spiele"], "colors": ["#1b1036", "#ff6fd0"],
    },
}
THEME_ORDER = ["autos", "burger", "rakete", "games"]


def words(n):
    """Ganze Zahl als deutsches Zahlwort (für die Stimme), z. B. 4100 -> viertausendeinhundert."""
    n = int(round(n))
    if n < 0:
        return "minus " + words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return (("ein" if o == 1 else ONES[o]) + "und" if o else "") + TENS[t]
    if n < 1000:
        h, r = divmod(n, 100)
        return ("ein" if h == 1 else ONES[h]) + "hundert" + (words(r) if r else "")
    if n < 1_000_000:
        th, r = divmod(n, 1000)
        return ("ein" if th == 1 else words(th)) + "tausend" + (words(r) if r else "")
    m, r = divmod(n, 1_000_000)
    head = "eine Million" if m == 1 else words(m) + " Millionen"
    return head + (" " + words(r) if r else "")


def stufe(n):
    cur = [s for s in STUFEN if n >= s[0]][-1]
    nxt = next((s for s in STUFEN if s[0] > n), None)
    return cur, nxt


def clean_name(name):
    """Kurzer, sprechbarer Name aus dem YouTube-Namen (ohne @, Zahlen und Sonderzeichen), sonst ''."""
    s = re.sub(r"^@", "", name or "")
    s = re.sub(r"[-_.]+", " ", s)
    s = re.sub(r"[^A-Za-zÄÖÜäöüß ]", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) < 3 or BAD.search(s):
        return ""
    first = s.split(" ")[0]
    return (first if len(first) >= 3 else s)[:14]


def wishes(comments, taken=(), jobs=None):
    """Wunschjobs aus Kommentaren: [{name, job, emoji, id}] (älteste zuerst, jede Person nur einmal)."""
    seen, out = set(taken), []
    for c in sorted(comments, key=lambda c: c.get("at", "")):
        text = c.get("text", "")
        who = c.get("channel") or c.get("name")
        if not text or who in seen or c.get("id") in seen or BAD.search(text) or not WISH.search(text):
            continue
        job = next(((label, emo) for pat, label, emo in (jobs or JOBS) if re.search(pat, text, re.I)), None)
        name = clean_name(c.get("name", ""))
        if not job or not name:
            continue
        seen.add(who)
        out.append({"name": name, "job": job[0], "emoji": job[1], "id": c.get("id", ""), "who": who})
    return out


def _hud(n, neu, geld, geld_neu, cur, names, extra=None, th=None, lv=None):
    th = th or THEMES["autos"]
    lv = STUFEN.index(cur) if lv is None else lv
    sc = {"typ": "firma", "mitarbeiter": n, "neu": max(0, neu), "geld": geld, "geld_neu": geld_neu,
          "pro_tag": n * PER_HEAD, "stufe": cur[1], "name": th["name"], "namen": names[:26],
          "thema": next(k for k, v in THEMES.items() if v is th), "level": lv, "stufe_label": th["stufen"][lv][1], "icon": th["icon"]}
    sc.update(extra or {})
    return sc


def theme_states(state):
    """Spielstand je Firma. Alter Spielstand (nur Autofirma, vor den vier Firmen) zählt als Autofirma."""
    state = state or {}
    themen = {k: dict(v) for k, v in (state.get("themen") or {}).items()}
    if "tag" in state and "autos" not in themen:
        themen["autos"] = {k: state[k] for k in ("tag", "mitarbeiter", "geld") if k in state}
    return themen


def next_theme(state):
    """Welche Firma heute dran ist: reihum, angefangen mit der, die am wenigsten Folgen hat."""
    themen = theme_states(state)
    folgen = sum(int(v.get("tag", 0)) for v in themen.values())
    return THEME_ORDER[folgen % len(THEME_ORDER)]


def episode(subs, state=None, comments=(), subscribers=(), today=None, own_channel="", thema=None):
    """Baut das Skript der nächsten Folge. Gibt (skript, neuer_zustand) zurück; den Zustand erst nach dem Upload speichern.

    subs: echte Abozahl. comments: yt.recent_comments (Wunschjobs). subscribers: yt.public_subscribers (Namen).
    thema: autos, burger, rakete oder games (ohne Angabe: die nächste Firma reihum).
    Das Team (Namen der Abonnenten) gilt für alle Firmen, Tag, Mitarbeiter und Konto zählt jede Firma für sich.
    """
    state = dict(state or {})
    thema = thema if thema in THEMES else next_theme(state)
    th = THEMES[thema]
    themen = theme_states(state)
    own = themen.get(thema, {})
    today = today or dt.date.today()
    tag = int(own.get("tag", 0)) + 1
    alt = int(own.get("mitarbeiter", 0))
    geld = int(own.get("geld", 0))
    n = max(0, int(subs))
    diff = n - alt
    first = tag == 1
    cur, nxt = stufe(n)
    old_cur, _ = stufe(alt)
    lv = STUFEN.index(cur)
    umsatz = n * PER_HEAD
    ev = th["events"][(tag - 1) % len(th["events"])]
    bonus = abs(ev[2]) if ev[2] > 0 else min(abs(ev[2]), geld + umsatz)  # Ausgaben nie größer als das Konto
    geld_neu = max(0, geld + umsatz + (bonus if ev[2] > 0 else -bonus))
    # Team: Namen der Abonnenten (öffentliche Abos) und Wunschjobs aus Kommentaren, älteste zuerst
    team = [dict(t) for t in state.get("team", [])]
    known = {t.get("who") for t in team}
    folge = sum(int(v.get("tag", 0)) for v in themen.values()) + 1  # laufende Nummer über alle Firmen
    for sub in reversed(list(subscribers)):  # YouTube liefert die neuesten zuerst
        who, nm = sub.get("channel") or sub.get("name"), clean_name(sub.get("name", ""))
        if nm and who not in known and who != own_channel:
            team.append({"name": nm, "who": who, "seit": folge})
            known.add(who)
    used = set(state.get("used", [])) | {own_channel}
    new_people = wishes([c for c in comments if c.get("channel") != own_channel], used, th["jobs"])[:2]
    for p in new_people:
        hit = next((t for t in team if t.get("who") == p["who"]), None)
        if hit:
            hit["job"] = p["job"]
        else:
            team.append({"name": p["name"], "who": p["who"], "seit": folge, "job": p["job"]})
    names = [t["name"] for t in reversed(team)]  # neueste zuerst, die sitzen bei den Neuen
    fresh = [t["name"] for t in team if t.get("seit") == folge]

    def hud(neu, g0, g1, extra=None):
        return _hud(n, neu, g0, g1, cur, names, extra, th, lv)

    segs = []
    if first:
        segs.append({"text": f"Für jeden Abonnenten stelle ich einen Mitarbeiter {th['in']} ein.",
                     "szene": hud(n, 0, 0, {"text": "Tag 1"})})
        segs.append({"text": f"Ich habe {words(n)} Abonnenten, also starte ich mit {words(n)} Leuten.",
                     "szene": {"typ": "zahl", "zahl": n, "einheit": "Mitarbeiter", "objekt": th["icon"], "farbcode": "#3f8cff"}})
    else:
        segs.append({"text": f"Tag {words(tag)}: Für jeden Abonnenten stelle ich einen Mitarbeiter {th['in']} ein.",
                     "szene": hud(max(0, diff), geld, geld, {"text": f"Tag {tag}"})})
        if diff > 0:
            segs.append({"text": f"Seit der letzten Folge kamen {words(diff)} Neue dazu, jetzt sind wir {words(n)}!",
                         "szene": {"typ": "zahl", "zahl": n, "einheit": "Mitarbeiter", "objekt": th["icon"], "farbcode": "#3f8cff"}})
        elif diff == 0:
            segs.append({"text": f"Leider kam niemand dazu, wir sind immer noch {words(n)}.",
                         "szene": {"typ": "figur", "ort": "stadt", "gefuehl": "traurig", "aktion": "steht", "objekt": "😢"}})
        else:
            segs.append({"text": f"{words(-diff).capitalize()} Leute haben gekündigt, wir sind nur noch {words(n)}.",
                         "szene": {"typ": "figur", "ort": "stadt", "gefuehl": "wut", "aktion": "zittert", "objekt": "📦"}})
    if fresh and not new_people:
        shout = ", ".join(fresh[:3])
        segs.append({"text": f"Willkommen im Team, {shout}!",
                     "szene": hud(min(n, len(fresh)), geld, geld, {"text": "Willkommen!"})})
    for p in new_people:
        segs.append({"text": f"{p['name']} wollte {p['job']} werden, und ab heute ist {p['name']} unser {p['job']}!",
                     "szene": hud(0, geld, geld, {"objekt": p["emoji"], "text": f"{p['name']}: {p['job']}"[:22], "neuling": p["name"]})})
    if not first and cur != old_cur:
        segs.append({"text": f"Und wir ziehen um: Ab heute sind wir {th['stufen'][lv][0]}!",
                     "szene": hud(0, geld, geld, {"text": "Umzug!"})})
    segs.append({"text": f"{th['arbeit']}, das sind {words(umsatz)} Euro.",
                 "szene": {"typ": "zahl", "zahl": umsatz, "einheit": "Euro am Tag", "objekt": "💶", "farbcode": "#2fbf6a"}})
    segs.append({"text": ev[0].format(b=words(bonus)),
                 "szene": hud(0, geld, geld, {"objekt": ev[1], "text": ev[5]})})
    segs.append({"text": f"Auf dem Firmenkonto sind jetzt {words(geld_neu)} Euro.",
                 "szene": hud(0, geld, geld_neu, {"text": "Kontostand"})})
    if nxt:
        segs.append({"text": f"Bei {words(nxt[0])} Abonnenten wird daraus {th['stufen'][STUFEN.index(nxt)][0]}.",
                     "szene": {"typ": "objekt", "objekt": th["ziel"], "text": f"Ziel: {nxt[0]} Abos", "ort": "stadt"}})
    segs.append({"text": "Abonniere und schreib deinen Traumjob in die Kommentare, dann stelle ich dich ein!",
                 "szene": hud(0, geld_neu, geld_neu, {"chef": True, "gefuehl": "freude", "aktion": "zeigt", "text": "Dein Job?"})})
    # kurz halten: höchstens 95 Wörter
    def count():
        return sum(len(x["text"].split()) for x in segs)
    for drop in ("Ziel:", "Willkommen!"):
        if count() > 95:
            segs = [x for x in segs if not str(x["szene"].get("text", "")).startswith(drop)]
    while count() > 95 and any(x["szene"].get("neuling") for x in segs):
        i = max(i for i, x in enumerate(segs) if x["szene"].get("neuling"))
        segs.pop(i)

    spec = {
        "slug": f"firma-{thema}-tag-{tag}-{today.isoformat()}", "stil": "cartoon", "format": "firma", "niche": "Firma",
        "firma_thema": thema,
        "stimmung": "neugierig", "stimme": "klar", "colors": th["colors"], "accent": "#ffe14d",
        "title": f"Jeder Abonnent = 1 Mitarbeiter {th['in']} (Tag {tag}) {th['icon']}",
        "description": (f"Für jeden Abonnenten stelle ich einen Mitarbeiter {th['in']} „{th['name']}“ ein. "
                        f"Heute: {n} Mitarbeiter und {geld_neu:,} € Spielgeld auf dem Konto (alles nur im Spiel).".replace(",", ".") +
                        f"\n\nSchreib deinen Traumjob in die Kommentare (z. B. „{th['beispiel']}“), dann stelle ich dich ein!"
                        f"\n\n#{th['tags'][0]} #firma #abonnenten #shorts"),
        "tags": th["tags"] + ["firma", "abonnenten", "mitarbeiter", "spiel", "shorts"],
        "figur": {"farbe": "navy", "hut": "zylinder", "name": "Chef"},
        "segments": segs,
    }
    themen[thema] = {"tag": tag, "mitarbeiter": n, "geld": geld_neu, "last_day": today.isoformat()}
    new_state = {"themen": themen, "last_day": today.isoformat(), "last_thema": thema, "team": team[-2000:],
                 "used": (list(state.get("used", [])) + [p["who"] for p in new_people] + [p["id"] for p in new_people])[-2000:]}
    return spec, new_state


if __name__ == "__main__":
    import cartoon
    import make_short
    subs = int(sys.argv[1]) if len(sys.argv) > 1 else 41
    st = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    demo_c = [{"id": "c1", "name": "@LenaFaehrt", "text": "Ich will Testfahrerin sein!", "at": "1", "channel": "a"}]
    demo_s = [{"name": n, "channel": n} for n in ["Tobi", "Mia_2010", "@JonasXD", "Emma", "Paul", "Ben"]]
    spec, new = episode(subs, st, demo_c, demo_s, thema=sys.argv[4] if len(sys.argv) > 4 else None)
    print(json.dumps(spec, ensure_ascii=False, indent=1))
    print(cartoon.validate(spec) or "ok", sum(len(s["text"].split()) for s in spec["segments"]), "Wörter")
    if len(sys.argv) > 2:
        path, dur, _ = cartoon.build_video(spec, sys.argv[2], make_short.load_tts())
        print(path, f"{dur:.1f}s")
