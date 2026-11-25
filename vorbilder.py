"""Vorbilder: erfolgreiche Kanäle in unseren Nischen, von denen wir Stil und Methoden lernen.

Nur lernen, nie kopieren: Die App liest von jedem Vorbild nur Titel und Aufrufe der neuesten
Videos aus dem öffentlichen RSS-Feed von YouTube (kein API-Schlüssel, keine Quote, nichts wird
heruntergeladen). Daraus baut sie
- „Läuft gerade“: die Vorbild-Videos der letzten Tage, die am schnellsten Aufrufe sammeln,
- „Muster“: wie die Titel gebaut sind (Wörter, Frage, Du-Ansprache, Emoji) im Vergleich zu unseren,
- Tipps, wo wir klar anders sind.

Läuft an zwei Stellen mit demselben Code:
- in der Zentrale (server.py, alle 12 Stunden, Karte „Vorbilder“ im Reiter Zuschauer),
- in GitHub Actions (tools/vorbilder_feed.py → docs/vorbilder.json), damit die tägliche
  Skript-Aufgabe die Muster und Trends lesen kann (Regel in CLAUDE.md).
"""
import datetime as dt
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

FILE = "vorbilder.json"
REFRESH_HOURS = 12
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "m": "http://search.yahoo.com/mrss/"}
TREND_DAYS = 14   # nur Videos der letzten 2 Wochen zählen für „Läuft gerade“
TREND_N = 12

# Recherche 20.11.2026 (Abos und Top-Shorts von YouTube, öffentlich). Die Abozahl ist ein Stand,
# die neuesten Videos holt die App selbst.
CHANNELS = [
    {"id": "UCvz84_Q0BbvZThy75mbd-Dg", "name": "Zack D. Films", "handle": "@zackdfilms", "lang": "en",
     "nische": "3D-Erklärvideo", "abos": "29,8 Mio.",
     "top": "How Stitches Work 😯 (255 Mio.)",
     "anders": "Eine Alltags- oder Körperfrage, Antwort in 30 s, Titel 3 bis 5 Wörter plus ein Emoji, über 4.000 Shorts.",
     "lernen": "Blockwelt-Erklärvideos: Körper und Alltagsdinge (Pflaster, Splitter, Adern), ganz kurze Titel."},
    {"id": "UCPRmoN_Oq-20XBTQfagEOJA", "name": "Zeck Felms", "handle": "@ZeckFelms", "lang": "en",
     "nische": "3D-Erklärvideo", "abos": "1,3 Mio.",
     "top": "How to Win Tic Tac Toe Everytime 😱 (97 Mio.)",
     "anders": "Gleicher 3D-Stil wie Zack D. Films, aber lockerer Ton und „So gewinnst du immer“-Tricks.",
     "lernen": "Neuer Erklär-Typ „So gewinnst du immer bei …“ (echte Strategie, z. B. Spiele)."},
    {"id": "UCBNqzxdXbV3Oki_aKtiS5UA", "name": "NYKentertain", "handle": "@nykentertain", "lang": "en",
     "nische": "3D-Erklärvideo", "abos": "878 Tsd.",
     "top": "Which Treadmill Should You Choose? 🏃 (53 Mio.)",
     "anders": "Fast jeder Titel verspricht einen Vorteil oder eine Wahl („Welches würdest du nehmen?“).",
     "lernen": "Ab und zu eine Wahl-Frage im Titel, die Leute in die Kommentare holt."},
    {"id": "UCphTF9wHwhCt-BzIq-s4V-g", "name": "What If", "handle": "@whatifscienceshow", "lang": "en",
     "nische": "Was passiert, wenn …", "abos": "9 Mio.",
     "top": "What If Earth Was Shaped Like a Donut? (51 Mio.)",
     "anders": "Absurde, aber wissenschaftliche Gedankenspiele, Titel beginnt immer mit „What If“.",
     "lernen": "Ab und zu ein großes Gedankenspiel statt nur Körper („Was wäre, wenn die Erde ein Donut wäre?“)."},
    {"id": "UCnwUjPK7dXety-AJ4fNw_RQ", "name": "The Paint Explainer", "handle": "@ThePaintExplainer", "lang": "en",
     "nische": "Strichmännchen", "abos": "2 Mio.",
     "top": "Lange Erklärvideos im Paint-Stil",
     "anders": "Einfachste Zeichnungen, die Frage im Titel trägt alles. Wenige, lange Videos.",
     "lernen": "Unser Strichmännchen-Look reicht. Die Frage muss stark sein, nicht die Grafik."},
    {"id": "UCUAL--p3qAa27luR0IYbjZA", "name": "Pencilmation", "handle": "@pencilmation", "lang": "en",
     "nische": "Strichmännchen", "abos": "20,6 Mio.",
     "top": "Krill🦐 (46 Mio.)",
     "anders": "Ein-Wort-Titel, Gag ohne Sprache, endet so, dass man es nochmal schaut.",
     "lernen": "Loop-Ende weiter testen, Bild-Gags in der ersten Sekunde."},
    {"id": "UCB4H9VsgYNwHuXrcL6F_v5g", "name": "Unlucky Guy", "handle": "@UnluckyGuyStories", "lang": "en",
     "nische": "Blockwelt-Horror", "abos": "568 Tsd.",
     "top": "Never Run To The Ice Cream Truck At Night 😱 (5,7 Mio.)",
     "anders": "Spielwelt-Horror mit Regeln („Niemals …“, „Du hast 60 Sekunden …“), vertraute Orte wie Schule.",
     "lernen": "Blockwelt-Horror-Titel als Regel oder Countdown: „Geh nachts nie zum Eiswagen“."},
    {"id": "UCsCAWoG-SagS7aFuWT1IZPw", "name": "Horror Shorts Party", "handle": "@HorrorShortsParty", "lang": "en",
     "nische": "Horror", "abos": "1,7 Mio.",
     "top": "Animierte Grusel-Shorts an bekannten Orten",
     "anders": "Der Ort macht den Klick: Orte, die jeder kennt. Nutzt fremde Marken und Figuren (machen wir nicht).",
     "lernen": "Horror an Alltagsorten (Supermarkt, Bus, Schulklo), aber ohne Marken."},
    {"id": "UCpFFItkfZz1qz5PpHpqzYBw", "name": "Nexpo", "handle": "@Nexpo", "lang": "en",
     "nische": "Mystery", "abos": "4 Mio.",
     "top": "Lange Internet-Rätsel",
     "anders": "Eine Nische, die sonst keiner bedient: unheimliche Internet-Rätsel, ruhig erzählt.",
     "lernen": "Mystery-Themen aus dem Internet und der Technik (seltsame Funksignale, verschwundene Webseiten)."},
    {"id": "UCDq8FAH3ewRf_nXKdmY36DQ", "name": "SONNENSEITE", "handle": "@SONNENSEITEBrightSideGerman", "lang": "de",
     "nische": "Alltags-Erklärvideo (DE)", "abos": "1,5 Mio.",
     "top": "Es hieß, dass die blaue Seite Kugelschreiber wegradiert (2,4 Mio.)",
     "anders": "Deutsche Alltags-Rätsel zu Dingen, die jeder zu Hause hat. Über 11.000 Videos.",
     "lernen": "Deutsche Titel über Alltagsdinge: „Wozu ist dieser Knopf am Gurt?“, „Warum 1 % Akku so lange hält“."},
    {"id": "UCKGMHVipEvuZudhHD05FOYA", "name": "Simplicissimus", "handle": "@Simplicissimus", "lang": "de",
     "nische": "Erklärvideo (DE)", "abos": "2,6 Mio.",
     "top": "Russland ist gar nicht so groß! (2,2 Mio.)",
     "anders": "Kurze Shorts aus langen Videos, Titel als Behauptung, die man prüfen will.",
     "lernen": "Ab und zu Titel als Behauptung statt Frage („Japan ist riesig!“)."},
    {"id": "UCwRH985XgMYXQ6NxXDo8npw", "name": "Dinge Erklärt – Kurzgesagt", "handle": "@KurzgesagtDE", "lang": "de",
     "nische": "Erklärvideo (DE)", "abos": "2,7 Mio.",
     "top": "Lange Wissenschaftsvideos",
     "anders": "Sehr starke Animation, wenige Videos, alles mit Quellen.",
     "lernen": "Fakten sauber halten, lieber ein Thema weglassen als etwas erfinden."},
    {"id": "UCesjlAoEgN_Sz_cKTvKEmmw", "name": "Doktor Whatson", "handle": "@DoktorWhatson", "lang": "de",
     "nische": "Erklärvideo (DE)", "abos": "429 Tsd.",
     "top": "Ist Neuralink wirklich so langlebig? (373 Tsd.)",
     "anders": "Aktuelle Technik- und Wissenschaftsthemen, Frage im Titel.",
     "lernen": "Ab und zu ein aktuelles Thema als „Warum …?“."},
    {"id": "UCYFqha8pa6s5OvMGVGXyyEg", "name": "Schliingeel Facts", "handle": "@SchliingeelFacts", "lang": "de",
     "nische": "Fakten-Shorts (DE)", "abos": "156 Tsd.",
     "top": "Ich lese deine Gedanken! (2 Mio.)",
     "anders": "Mitmach-Shorts: der Zuschauer testet sich selbst (Farben sehen, Gedanken lesen).",
     "lernen": "Mitmach-Hook: „Teste dich: …“ oder „Schau genau hin“ bei Erklärvideos."},
]

QUESTION = re.compile(r"\?")
YOU = re.compile(r"\b(du|dich|dir|dein\w*|you|your)\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
START_Q = re.compile(r"^(was|warum|wie|wieso|weshalb|wer|wo|welche\w*|kann|können|ist|what|why|how|can|could|which|who)\b", re.I)
TAGS = re.compile(r"#\w+")


# Taktiken, die bei mehreren Vorbildern gleich sind (Recherche 25.11.2026: Zack D. Films, Zeck Felms, What If,
# The Paint Explainer, SONNENSEITE, Schliingeel Facts u. a.; Analysen ihres Schnitts und Tons). Wir übernehmen nur die
# Methode, als Test: Der Lernmodus vergleicht jede mit unserer bisherigen Art und nimmt nur, was bei UNS besser läuft.
# "merkmal" ist der Schlüssel unter „Was am besten funktioniert“ (learn.FEATURE_NAMES).
TAKTIKEN = [
    {"name": "Spannungsmusik statt Party-Beat", "merkmal": "musik",
     "gesehen": "3D-Erklärkanäle legen leise, pulsierende Spannungsmusik mit Ticken unter die Stimme.",
     "wir": "Musik-Stile „spannung“, „leicht“ (verspielt), „drop“ (Beat erst auf dem Aha-Moment) gegen „beat“."},
    {"name": "Beat-Drop auf der Auflösung", "merkmal": "musik",
     "gesehen": "Bis zur Antwort bleibt der Ton zurückhaltend, auf der Antwort kommt der Knall.",
     "wir": "Musik-Stil „drop“, dazu die Soundeffekte „stark“/„voll“ (Riser, Schlag, Pause)."},
    {"name": "Schnitt alle 1 bis 2 Sekunden", "merkmal": "tempo",
     "gesehen": "Fast nie bleibt ein Bild länger als 2 Sekunden stehen, jeder Schnitt mit Geräusch.",
     "wir": "Tempo „schnell“ (Schnitt alle ca. 1,3 s mit Snap) gegen normal."},
    {"name": "Auffällige Übergänge", "merkmal": "uebergang",
     "gesehen": "Zoom durchs Bild, Wischer und Blitze verdecken den Schnitt, das Auge bleibt dran.",
     "wir": "Übergänge „zoom“, „wisch“ (flüssiger Farb-Wisch), „kreis“, „blitz“ gegen den alten Wisch „whip“."},
    {"name": "Frage bleibt im Bild", "merkmal": "halten",
     "gesehen": "Die Frage aus dem Titel steht oben, bis sie beantwortet ist. Wer geht, verpasst die Antwort.",
     "wir": "„frage“ (Frage oben, Haken bei der Auflösung), „balken“ (Fortschrittsbalken), „beides“, „ohne“."},
    {"name": "Antwort im vorletzten Satz, Ende führt in den Anfang", "merkmal": "ende",
     "gesehen": "Kein Abschied, das Video endet so, dass es nahtlos von vorn läuft.",
     "wir": "Loop-Ende in 5 von 15 Skripten."},
    {"name": "Kurze Frage im Titel plus 1 Emoji", "merkmal": "typ",
     "gesehen": "3 bis 6 Wörter, eine Frage zu etwas, das jeder kennt (Körper, Zuhause).",
     "wir": "Regel für die täglichen Skripte, Titel-Vergleich oben."},
    {"name": "Klare, ruhige Erzählstimme", "merkmal": "stimme",
     "gesehen": "Eine gleichbleibende, gut verständliche Stimme, eher trocken als aufgeregt.",
     "wir": "Stimmen „aufgeregt“, „klar“, „freundlich“ im Vergleich (Lernmodus)."},
]


def clean_title(t):
    return re.sub(r"\s+", " ", TAGS.sub("", t or "")).strip()


def words(t):
    return len([w for w in re.split(r"\s+", EMOJI.sub("", clean_title(t))) if re.search(r"\w", w)])


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 shorts-zentrale"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for e in root.findall("a:entry", NS):
        stats = e.find("m:group/m:community/m:statistics", NS)
        link = e.find("a:link", NS)
        href = link.get("href", "") if link is not None else ""
        out.append({"id": e.findtext("yt:videoId", namespaces=NS),
                    "title": clean_title(e.findtext("a:title", namespaces=NS)),
                    "views": int(stats.get("views", 0)) if stats is not None else 0,
                    "published": e.findtext("a:published", namespaces=NS),
                    "short": "/shorts/" in href})
    return out


def _age_days(published, now):
    try:
        t = dt.datetime.fromisoformat(published.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return max((now - t).total_seconds() / 86400, 0.25)


def pattern(titles):
    """Wie die Titel gebaut sind: Ø Wörter und Anteile (0 bis 100) für Frage, Du, Emoji, Fragewort vorn."""
    ts = [clean_title(t) for t in titles if clean_title(t)]
    if not ts:
        return None
    pct = lambda rx: round(100 * sum(1 for t in ts if rx.search(t)) / len(ts))
    return {"n": len(ts), "words": round(sum(words(t) for t in ts) / len(ts), 1),
            "question": pct(QUESTION), "you": pct(YOU), "emoji": pct(EMOJI), "starts_q": pct(START_Q)}


def tips(theirs, ours):
    """Höchstens 3 kurze Tipps, wo unsere Titel klar anders sind als die der Vorbilder."""
    if not theirs or not ours or ours["n"] < 5:
        return []
    out = []
    if ours["words"] - theirs["words"] >= 2:
        out.append(f"Kürzere Titel: Vorbilder im Schnitt {theirs['words']:.0f} Wörter, wir {ours['words']:.0f}.")
    if theirs["question"] - ours["question"] >= 25:
        out.append(f"Mehr Fragen im Titel: Vorbilder {theirs['question']} %, wir {ours['question']} %.")
    if theirs["emoji"] - ours["emoji"] >= 30:
        out.append(f"Ein Emoji am Titelende: Vorbilder {theirs['emoji']} %, wir {ours['emoji']} %.")
    if ours["emoji"] - theirs["emoji"] >= 40:
        out.append(f"Weniger Emojis: Vorbilder {theirs['emoji']} %, wir {ours['emoji']} %.")
    return out[:3]


def build(feeds, our_titles=(), now=None):
    """feeds: {channel_id: [videos] oder None (Fehler)}. Gibt das gespeicherte Ergebnis zurück."""
    now = now or dt.datetime.now(dt.timezone.utc)
    chans, recent = [], []
    for c in CHANNELS:
        vids = feeds.get(c["id"])
        row = {k: c[k] for k in ("id", "name", "handle", "lang", "nische", "abos", "top", "anders", "lernen")}
        row["url"] = "https://www.youtube.com/" + c["handle"]
        row["ok"] = vids is not None
        if vids:
            for v in vids:
                age = _age_days(v.get("published"), now)
                v["per_day"] = round(v["views"] / age) if age else 0
                if age is not None and age <= TREND_DAYS:
                    recent.append(dict(v, channel=c["name"], handle=c["handle"], lang=c["lang"], nische=c["nische"]))
            best = max(vids, key=lambda v: v["per_day"])
            row["best_new"] = {"id": best["id"], "title": best["title"], "views": best["views"], "per_day": best["per_day"]}
            row["new_per_week"] = sum(1 for v in vids if (_age_days(v.get("published"), now) or 99) <= 7)
        chans.append(row)
    recent.sort(key=lambda v: v["per_day"], reverse=True)
    trend = [{k: v[k] for k in ("id", "title", "views", "per_day", "channel", "handle", "lang", "nische", "short")}
             for v in recent[:TREND_N]]
    theirs = pattern([v["title"] for v in recent[:40]])
    ours = pattern(list(our_titles)[:40])
    return {"updated": now.isoformat(timespec="minutes"), "channels": chans, "trend": trend,
            "muster": theirs, "unsere": ours, "tips": tips(theirs, ours), "taktiken": TAKTIKEN,
            "regel": "Nur Stil und Methoden lernen: Art der Frage, Titelbau, Länge, Rhythmus. "
                     "Keine Themen, Texte, Bilder oder Videos 1:1 übernehmen, keine fremden Videos clippen."}


def fetch_all(fetch=None):
    fetch = fetch or (lambda cid: parse(get(FEED.format(cid))))
    feeds = {}
    for c in CHANNELS:
        try:
            feeds[c["id"]] = fetch(c["id"])
        except Exception as e:  # ein kaputter Feed soll die anderen nicht stoppen
            print("Vorbild", c["name"], "nicht erreichbar:", e)
            feeds[c["id"]] = None
    return feeds


# --- Zentrale --------------------------------------------------------------------

def load():
    import store
    return store.read(FILE, {})


def due(d=None):
    d = load() if d is None else d
    try:
        t = dt.datetime.fromisoformat(d["updated"])
    except (KeyError, ValueError):
        return True
    return (dt.datetime.now(dt.timezone.utc) - t).total_seconds() > REFRESH_HOURS * 3600


def refresh(our_titles=()):
    import store
    feeds = fetch_all()
    if not any(v for v in feeds.values()):
        return load()  # kein Netz: alte Daten behalten
    d = build(feeds, our_titles)
    store.write(FILE, d)
    return d


def summary():
    d = load()
    if not d:
        return {"channels": [dict({k: c[k] for k in ("name", "handle", "lang", "nische", "abos", "top", "anders", "lernen")},
                                  url="https://www.youtube.com/" + c["handle"]) for c in CHANNELS],
                "trend": [], "tips": [], "updated": None, "taktiken": TAKTIKEN}
    return {**d, "taktiken": TAKTIKEN}


if __name__ == "__main__":
    print(json.dumps(build(fetch_all()), ensure_ascii=False, indent=1)[:3000])
