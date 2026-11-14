"""Hook-Prüfliste und Humanizer für die Skripte.

Ideen aus dem Skill-Paket "claude-content-skills" (MIT): virality (Checkliste für die ersten
3 Sekunden) und humanizer (typische KI-Floskeln entfernen), umgebaut für deutsche
Strichmännchen-Shorts.

    python3 hookcheck.py seed/0193-*.json          # Note und was fehlt
    python3 hookcheck.py --fix seed/0193-*.json    # zusätzlich Floskeln/Gedankenstriche entfernen

Die App nutzt dasselbe: neue Skripte werden beim Einlesen bereinigt (clean), die Zentrale
zeigt die Note (check) und der Lernmodus vergleicht starke und schwache Hooks.
"""
import json
import re
import sys

# --- Humanizer ---------------------------------------------------------------------

# Begrüßungen und Ankündigungen am Anfang des ersten Satzes (werden entfernt)
INTRO = re.compile(
    r"^\s*(?:(?:hallo|hey|hi|servus|moin)(?:\s+(?:leute|zusammen|ihr))?|willkommen(?:\s+zurück)?(?:\s+bei[^,.!?]*)?"
    r"|heute\s+(?:geht\s+es\s+um|schauen\s+wir\s+uns|zeige\s+ich\s+dir|erkläre\s+ich\s+dir)[^,.!?]*"
    r"|in\s+diesem\s+(?:video|short)[^,.!?]*)\s*[,.!:]+\s*",
    re.I)

# Ganze Sätze, die nur ankündigen und nichts sagen (werden entfernt)
EMPTY_SENTENCES = [
    r"lass(?:t)?\s+uns\s+(?:gemeinsam\s+)?(?:eintauchen|loslegen|anfangen|einen\s+blick\s+(?:darauf\s+)?werfen)",
    r"tauchen\s+wir\s+(?:gemeinsam\s+)?ein",
    r"schnall\s+dich\s+an",
    r"los\s+geht'?s",
    r"bleib\s+dran,?\s+(?:es\s+)?(?:wird|lohnt\s+sich)[^.!?]*",
]
EMPTY = re.compile(r"(?:^|(?<=[.!?]))\s*(?:" + "|".join(EMPTY_SENTENCES) + r")\s*[.!]+", re.I)

DASH = re.compile(r"\s*(?:—|–|\s--\s)\s*")

# Was oft nach KI klingt (wird nur gemeldet, nicht automatisch umgeschrieben)
TELLS = [
    (r"\bnicht\s+nur\b[^.!?]*\bsondern\b", "„nicht nur … sondern“"),
    (r"\bfaszinierend\w*", "„faszinierend“"),
    (r"\bspannend\w*", "„spannend“"),
    (r"\bunglaublich\w*", "„unglaublich“"),
    (r"\batemberaubend\w*", "„atemberaubend“"),
    (r"\bbemerkenswert\w*", "„bemerkenswert“"),
    (r"\beintauchen\b", "„eintauchen“"),
    (r"\breise\s+(?:durch|in)\b", "„Reise durch …“"),
    (r"\bin\s+der\s+welt\s+de[rs]\b", "„in der Welt der …“"),
    (r"\bes\s+ist\s+wichtig\s+zu\b", "„es ist wichtig zu …“"),
    (r"\b(?:zusammenfassend|letztendlich|im\s+grunde\s+genommen)\b", "Füllwort"),
    (r"\bhier\s+ist\s+der\s+(?:clou|haken)\b", "„hier ist der Clou“"),
    (r"\bund\s+das\s+(?:beste|verrückteste)\s*[?:]", "„und das Beste?“"),
    (r"\blass(?:t)?\s+das\s+(?:mal\s+)?sacken\b", "„lass das sacken“"),
]
TELLS = [(re.compile(p, re.I), name) for p, name in TELLS]


def humanize(text, first=False):
    """Entfernt Gedankenstriche, Begrüßungen und leere Ankündigungen. Der Inhalt bleibt gleich."""
    out = DASH.sub(", ", text)
    out = re.sub(r",\s*([.!?])", r"\1", out)  # "Satz, ." nach einem Strich am Ende
    if first:
        out = INTRO.sub("", out)
    out = EMPTY.sub("", out)
    out = re.sub(r"([!?])\1+", r"\1", out)  # "!!!" -> "!"
    out = re.sub(r"\s{2,}", " ", out).strip()
    if out and out[0].islower() and out != text.strip():
        out = out[0].upper() + out[1:]
    return out or text


def clean(spec):
    """Bereinigt Titel und Sätze eines Skripts. Gibt (skript, geändert?) zurück."""
    changed = False
    title = spec.get("title")
    if isinstance(title, str):
        new = DASH.sub(", ", title).strip(" ,")
        changed |= new != title
        spec["title"] = new
    for i, seg in enumerate(spec.get("segments", [])):
        if not isinstance(seg.get("text"), str):
            continue
        new = humanize(seg["text"], first=i == 0)
        changed |= new != seg["text"]
        seg["text"] = new
    return spec, changed


def tells(spec):
    """Gefundene KI-Floskeln im ganzen Skript (Liste von Namen, doppelte nur einmal)."""
    text = " ".join(str(s.get("text", "")) for s in spec.get("segments", []))
    found = [name for rx, name in TELLS if rx.search(text)]
    if DASH.search(text):
        found.append("Gedankenstrich")
    return found


# --- Hook-Prüfliste ------------------------------------------------------------------

YOU = re.compile(r"\b(?:du|dich|dir|dein\w*|ihr|euch|euer\w*)\b", re.I)
WE_I = re.compile(r"^\s*(?:ich|wir|heute|in\s+diesem)\b", re.I)
TENSION = re.compile(
    r"\?|!|\b(?:plötzlich|niemand\w*|nie|nichts|kein\w*|weg|verschw\w+|spurlos|allein\w*|tot\w*|tödlich\w*|stirbt|sterben"
    r"|verboten\w*|geheim\w*|rätsel\w*|seltsam\w*|unmöglich\w*|leer\w*|starr\w*|schreit|brennt|explod\w+|reißt|stürzt"
    r"|fällt|fällst|knapp|riesig\w*|ohne|nicht\s+mehr|warum|wieso|was\s+passiert|niemals|zurück|doch|aber|still|bewegt|öffnet|klopft|kichert"
    r"|flüstert|läutet|brummt|schwebt)\b", re.I)
STILL = {"", "steht", "sitzt", "liegt", "schlaeft", "schläft"}
NUMBER_WORDS = re.compile(r"\d|\b(?:hundert|tausend|million\w*|milliard\w*)\b", re.I)

SHORT_WORDS = (40, 85)  # ca. 16 bis 34 Sekunden gesprochen
HOOK_MAX = 12
HOOK_MAX_LONG = 25


def _is_long(spec):
    return str(spec.get("laenge", "")).lower() == "lang" or len(spec.get("segments", [])) > 20


def _scene(seg):
    return seg.get("szene") or seg.get("visual") or {}


def check(spec):
    """Prüft die ersten Sekunden nach acht Punkten. Gibt Note, Punkte und Tipps zurück."""
    segs = spec.get("segments") or [{}]
    first = str(segs[0].get("text", "")).replace("*", "").strip()
    words = len(first.split())
    long = _is_long(spec)
    niche = str(spec.get("niche", "")).lower()
    scene = _scene(segs[0])
    typ = str(scene.get("typ") or scene.get("type") or "").lower()
    total = sum(len(str(s.get("text", "")).split()) for s in segs)
    found = tells(spec)

    if niche.startswith("erkl"):
        about_you = bool(YOU.search(first)) or first.endswith("?")
        you_tip = "Erklärvideo: im ersten Satz „du“ sagen oder die Frage stellen."
    else:
        about_you = not WE_I.search(first)
        you_tip = "Nicht mit „Ich“, „Wir“ oder „Heute“ anfangen, sondern mit der Szene."

    if spec.get("stil") == "cartoon" or "szene" in segs[0]:
        moving = typ in ("horror", "zahl", "jahr", "vergleich", "liste", "akte") or (
            typ in ("figur", "gruppe") and str(scene.get("aktion", "")).lower() not in STILL)
        visible = bool(scene.get("objekt") or scene.get("text") or scene.get("augen") or scene.get("wetter")
                       or scene.get("zahl") or scene.get("jahr"))
    else:  # normale Shorts haben immer einen bewegten Hintergrund; Bild = Grafik, Emoji, Auto oder Zahl
        moving = True
        visible = bool(scene or segs[0].get("emoji") or spec.get("style") == "car" or NUMBER_WORDS.search(first))

    lo, hi = SHORT_WORDS
    points = [
        ("start", "Startet sofort", not INTRO.match(first) and not re.match(r"^\s*(?:wusstest\s+du|kennst\s+du\s+das)", first, re.I),
         "Begrüßung oder „Wusstest du“ weglassen, direkt mit der Situation anfangen."),
        ("kurz", "Erster Satz kurz", words <= (HOOK_MAX_LONG if long else HOOK_MAX),
         f"Erster Satz hat {words} Wörter, besser höchstens {HOOK_MAX_LONG if long else HOOK_MAX}."),
        ("du", "Dreht sich um den Zuschauer", about_you, you_tip),
        ("spannung", "Spannung im ersten Satz", bool(TENSION.search(first)),
         "Etwas Krasses passieren lassen: plötzlich, niemand, verschwunden, eine Frage …"),
        ("bewegung", "Bild bewegt sich ab Sekunde 0", moving,
         "Erste Szene mit Bewegung (rennt, zittert, zeigt, schockiert) statt „steht“."),
        ("bild", "Erkennbares Bild", visible, "Erste Szene braucht ein Objekt, Emoji oder Wort zum Thema."),
        ("floskeln", "Klingt nicht nach KI", len(found) <= (2 if long else 0),
         ("KI-Floskeln: " + ", ".join(found)) if found else ""),
        ("laenge", "Passende Länge", long or lo <= total <= hi,
         f"{total} Wörter, für ca. 22 Sekunden {lo} bis {hi} Wörter."),
    ]
    score = sum(1 for p in points if p[2])
    return {
        "score": score, "max": len(points),
        "points": [{"key": k, "label": label, "ok": bool(ok)} for k, label, ok, _ in points],
        "tips": [tip for _, _, ok, tip in points if not ok and tip],
    }


def bucket(score):
    """Gruppe für den Lernmodus."""
    return "stark (8 von 8)" if score >= 8 else "gut (6-7 von 8)" if score >= 6 else "schwach (bis 5 von 8)"


def main(args):
    fix = "--fix" in args
    files = [a for a in args if a != "--fix"]
    if not files:
        print(__doc__)
        return 1
    worst = 8
    for name in files:
        with open(name, encoding="utf-8") as f:
            spec = json.load(f)
        if fix:
            spec, changed = clean(spec)
            if changed:
                with open(name, "w", encoding="utf-8") as f:
                    json.dump(spec, f, ensure_ascii=False, indent=2)
                    f.write("\n")
        r = check(spec)
        worst = min(worst, r["score"])
        print(f"{r['score']}/{r['max']}  {name}")
        for tip in r["tips"]:
            print("      - " + tip)
    return 0 if worst >= 6 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
