"""Hook-Prüfliste und Humanizer für die Skripte.

Ideen aus dem Skill-Paket "claude-content-skills" (MIT): virality (Checkliste für die ersten
3 Sekunden) und humanizer (typische KI-Floskeln entfernen), umgebaut für deutsche
Strichmännchen-Shorts.

Seit 15.11.2026 dazu die Text-Regeln aus „unslop“ von Damir Sokolovsky (@heydamir, CC BY 4.0,
https://github.com/heydamir/unslop), auf Deutsch umgebaut: keine Hype-Wörter, keine Begrüßung,
keine gehäuften Ausrufezeichen, keine unbelegten Zahlen, kurze Zeilen ohne Schlusspunkt,
Emojis nur als Bild und nicht als Deko. Das gilt auch für Titel, Beschreibung und Thumbnail-Text.

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

# Gedankenstriche, aber nicht zwischen Zahlen („1959–1960“ bleibt)
DASH = re.compile(r"(?<!\d)\s*(?:—|–|\s--\s)\s*|\s*(?:—|–|\s--\s)\s*(?!\d)")

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
    # typisch deutsches KI-Deutsch (unslop + Humanizer)
    (r"\b(?:heutzutage|in\s+der\s+heutigen\s+(?:zeit|welt))\b", "„heutzutage“"),
    (r"\beine?\s+(?:wichtige|entscheidende|zentrale|große)\s+rolle\b", "„spielt eine wichtige Rolle“"),
    (r"\bvon\s+(?:entscheidender|großer|zentraler)\s+bedeutung\b", "„von entscheidender Bedeutung“"),
    (r"\b(?:darüber\s+hinaus|nicht\s+zuletzt|zweifellos|ohne\s+zweifel|im\s+endeffekt|sozusagen)\b", "Füllwort"),
    (r"(?:^|[.!?]\s+)tatsächlich\b", "„Tatsächlich …“ am Satzanfang"),
    (r"\bmehr\s+als\s+nur\b", "„mehr als nur“"),
    (r"\b(?:fakt\s+ist|spoiler)\s*:", "„Fakt ist:“"),
    (r"\bdie\s+antwort\s+wird\s+dich\s+überraschen\b", "„die Antwort wird dich überraschen“"),
]
TELLS = [(re.compile(p, re.I), name) for p, name in TELLS]

# Hype-Wörter (unslop: „supercharge, seamless, unlock, magic, revolutionize“ auf Deutsch)
HYPE = [
    (r"\brevolution(?:är\w*|ier\w*)", "„revolutionär“"),
    (r"\bbahnbrechend\w*", "„bahnbrechend“"),
    (r"\bultimativ\w*", "„ultimativ“"),
    (r"\bnahtlos\w*", "„nahtlos“"),
    (r"\bgame[\s-]?changer\b|\bdas\s+ändert\s+alles\b", "„Game-Changer“"),
    (r"\bdu\s+wirst\s+(?:es\s+)?nicht\s+glauben\b", "„du wirst nicht glauben“"),
    (r"\bunfassbar\w*", "„unfassbar“"),
    (r"\b(?:der|die|das)\s+absolute\s+wahnsinn\b|\babsolut\s+krass\b", "„absoluter Wahnsinn“"),
    (r"\bgänsehaut\s+garantiert\b", "„Gänsehaut garantiert“"),
    (r"\bmuss\s+man\s+gesehen\s+haben\b|\bmust[\s-]see\b", "„muss man gesehen haben“"),
]
HYPE = [(re.compile(p, re.I), name) for p, name in HYPE]

# Behauptungen, die niemand prüfen kann (unslop: „Loved by 10,000+ teams“)
CLAIMS = [
    (r"\b(?:9\d|100)\s*(?:%|prozent)\s+(?:aller|der)\s+\w+", "„99 % der Menschen …“"),
    (r"\b(?:die\s+meisten|fast\s+alle|kaum\s+jemand)\s+(?:menschen|leute|deutschen)?\s*(?:wissen|kennen)\s+(?:das\s+)?nicht\b",
     "„die meisten wissen das nicht“"),
    (r"\bwissenschaftlich\s+(?:bewiesen|belegt)\b", "„wissenschaftlich bewiesen“ ohne Quelle"),
]
CLAIMS = [(re.compile(p, re.I), name) for p, name in CLAIMS]

_E1 = "[\U0001F000-\U0001F1E5\U0001F200-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF][\uFE0F\U0001F3FB-\U0001F3FF]*"
EMOJI = re.compile("[\U0001F1E6-\U0001F1FF]{2}|" + _E1 + "(?:\u200D" + _E1 + ")*")
GREETING = re.compile(r"^\s*(?:(?:hallo|hey|hi|servus|moin)(?:\s+(?:leute|zusammen|ihr))?|willkommen(?:\s+zurück)?)\s*[,.!:]+\s*", re.I)


def _found(text, rules):
    return [name for rx, name in rules if rx.search(text)]


def polish(text, kind="line"):
    """Bereinigt einen kurzen Text (unslop): kind = title, line (Thumbnail), description oder post.

    Entfernt Gedankenstriche, Begrüßung, gehäufte !!/??, leere Ankündigungen; Titel und Zeilen
    enden ohne Punkt, ein Titel behält höchstens ein Emoji. Hashtags und Zeilenumbrüche bleiben.
    """
    if not isinstance(text, str) or not text.strip():
        return text
    if kind in ("description", "post"):
        lines = []
        for i, line in enumerate(text.split("\n")):
            if line.lstrip().startswith("#") or not line.strip():
                lines.append(line.rstrip())
                continue
            new = humanize(line, first=i == 0)
            new = GREETING.sub("", new) if i == 0 else new
            lines.append(new)
        out = "\n".join(lines).strip("\n")
        return out or text
    out = DASH.sub(" " if kind == "line" else ", ", text)
    out = GREETING.sub("", out)
    out = re.sub(r"([!?])[!?1]+", r"\1", out)
    out = re.sub(r",\s*([.!?])", r"\1", out)
    out = re.sub(r"\s*,\s*$", "", out)
    out = re.sub(r"(?<![.])\.\s*$", "", out.strip())  # kein Schlusspunkt, „…“ bleibt
    if kind == "title":
        seen = []
        def keep_first(m):
            seen.append(m.group(0))
            return m.group(0) if len(seen) == 1 else ""
        out = EMOJI.sub(keep_first, out)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,")
    if out and out[0].islower() and out != text.strip():
        out = out[0].upper() + out[1:]
    return out or text


def text_tips(spec):
    """Tipps für Titel, Beschreibung und Thumbnail-Text (zählen nicht zur Hook-Note)."""
    tips = []
    title = str(spec.get("title") or "")
    desc = str(spec.get("description") or "")
    thumbs = spec.get("thumb_text") or []
    thumbs = [thumbs] if isinstance(thumbs, str) else [str(t) for t in thumbs]
    plain = EMOJI.sub("", title).strip()
    if len(plain) > 70:
        tips.append(f"Titel hat {len(plain)} Zeichen, besser unter 60 (sonst abgeschnitten).")
    if len(EMOJI.findall(title)) > 1:
        tips.append("Titel: höchstens ein Emoji.")
    if title.count("!") > 1 or re.search(r"[!?]{2,}", title):
        tips.append("Titel: keine gehäuften Ausrufezeichen.")
    caps = [w for w in re.findall(r"\b[A-ZÄÖÜ]{4,}\b", title)]
    if len(caps) > 1:
        tips.append("Titel: nicht mehrere Wörter in GROSSBUCHSTABEN.")
    found = _found(title + " " + desc + " " + " ".join(thumbs), HYPE)
    if found:
        tips.append("Hype-Wörter: " + ", ".join(found) + ". Lieber sagen, was passiert.")
    text = " ".join([title, desc] + [str(s.get("text", "")) for s in spec.get("segments", [])])
    found = _found(text, CLAIMS)
    if found:
        tips.append("Unbelegte Behauptung: " + ", ".join(found) + ". Nur mit echter Quelle, sonst weg.")
    if GREETING.match(desc):
        tips.append("Beschreibung beginnt mit einer Begrüßung, lieber direkt mit dem Inhalt.")
    tw = set(re.findall(r"\w{4,}", title.lower()))
    for t in thumbs:
        words = re.findall(r"\w{4,}", t.replace("|", " ").lower())
        if len(words) >= 3 and sum(w in tw for w in words) >= len(words) - 1:
            tips.append("Thumbnail-Text wiederholt den Titel, lieber eine neue Neugier-Zeile.")
            break
    segs = spec.get("segments") or []
    if str(spec.get("ende", "")).lower() == "loop" and segs:
        last = str(segs[-1].get("text", "")).strip()
        if last.endswith((".", "!")):
            tips.append("Loop-Ende: der letzte Satz soll offen enden und in den ersten Satz übergehen (ohne Schlusspunkt).")
    return tips


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
    for key, kind in (("title", "title"), ("description", "description")):
        if isinstance(spec.get(key), str):
            new = polish(spec[key], kind)
            changed |= new != spec[key]
            spec[key] = new
    thumbs = spec.get("thumb_text")
    if isinstance(thumbs, list):
        new = [polish(t, "line") if isinstance(t, str) else t for t in thumbs]
        changed |= new != thumbs
        spec["thumb_text"] = new
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
    found = [name for rx, name in TELLS + HYPE if rx.search(text)]
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
    elif niche == "erzählung":  # Ich-Geschichte: „Ich“ ist erlaubt, nur kein „Heute“ oder „In diesem Video“
        about_you = not re.match(r"^\s*(?:heute|in\s+diesem)\b", first, re.I)
        you_tip = "Geschichte: direkt mit der Situation anfangen, nicht mit „Heute“."
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
        "text_tips": text_tips(spec),
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
        for tip in r["text_tips"]:
            print("      · " + tip)
    return 0 if worst >= 6 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
