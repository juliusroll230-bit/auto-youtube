"""Nischen-Kompass: Welche Titel-Muster und Themenfelder bei uns wirklich laufen.

Ideen aus Julius' Paket „claude-content-skills“ (MIT), auf Deutsch und auf unseren Kanal umgebaut:
- hook-mining: Titel nach ihrem psychologischen Muster sortieren und nach echten Aufrufen ranken.
  Nie einen Titel kopieren, nur das Muster nehmen, das bei UNS funktioniert.
- going-viral: nach ca. einem Drittel einen Zwischen-Haken („Aber dann …“), damit die Leute nicht wegwischen,
  und jeden Tag den Einstieg wechseln (immer „Plötzlich …“ ermüdet und wirkt nach Massenware).
- content-audit / content-pillar-builder: das stärkste Themenfeld finden, um die Nische zu schärfen.

Alles wird aus dem Skript berechnet, gilt also sofort auch für alle alten Videos.
Ohne Abhängigkeiten, damit es auch in GitHub Actions läuft (tools/channel_feed.py).
"""
import re

# --- Titel-Muster (hook-mining, deutsch) ---------------------------------------------------
# Reihenfolge zählt: das erste passende Muster gewinnt.
PATTERNS = [
    ("Was passiert, wenn …?", r"^was passiert\b"),
    ("Warum …?", r"^(warum|wieso|weshalb)\b"),
    ("Regel/Countdown", r"^(geh|schwimm|steig|öffne|schau|dreh|antworte|bleib|lauf|fahr|nimm|iss|trink|sag)\w*\b.*\bnie(mals)?\b"
                        r"|\b\d+\s*sekunden\b|\bdu hast\b.*\bum\b|^\w+:\s*\d+\s*sekunden"),
    ("Mitmachen/Wahl", r"^teste dich|\bwelche[rsn]?\b.*\?$|\bwürdest du\b"),
    ("Zahl/Liste", r"^\d+\s+\w+"),
    ("Das X, das niemand …", r"^(der|die|das)\s+[\wäöüß-]+(\s+[\wäöüß-]+){0,3},\s*(der|die|das|den|dem|wo)\b"),
    ("Mythos/Irrtum", r"\b(mythos|irrtum|glauben fast alle|stimmt nicht|wirklich bedeutet|nicht gegründet)\b"),
    ("Frage", r"\?$"),
]
PATTERNS = [(name, re.compile(rx, re.I)) for name, rx in PATTERNS]
EMOJI_TAIL = re.compile(r"[\s\W_]+$")


def plain_title(title):
    """Titel ohne Emoji, #shorts und Leerzeichen am Ende."""
    t = re.sub(r"#\w+", "", str(title or ""))
    t = re.sub(r"[^\w\s?!.,:;'\"„“()/&%€$-]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def title_pattern(title, niche=""):
    """Psychologisches Muster eines Titels, z. B. „Was passiert, wenn …?“ oder „Das X, das niemand …“."""
    t = plain_title(title)
    if str(niche).lower() == "erzählung" and not t.lower().startswith(("was passiert", "warum")):
        return "Ich-Geschichte"
    if re.search(r"^jeder abonnent\b", t, re.I):
        return "Firmen-Spiel"
    for name, rx in PATTERNS:
        if rx.search(t):
            return name
    return "Aussage/Fakt"


# --- Themenfeld (Nische schärfen) ------------------------------------------------------------
FIELDS = [
    ("Körper & Sinne", r"schlaf|schläf|träum|müde|gähn|blinzel|auge|ohr|nase|zunge|zahn|zähn|haut|haar|herz|blut|gehirn|hirn"
                       r"|muskel|knochen|bauch|magen|hunger|durst|trink|schwitz|friert|kälte|hitze|heiß wird|fieber|husten|niese"
                       r"|schluckauf|gänsehaut|schwindel|tränen|wunde|finger|hand|händ|fuß|füß|atme|luft an|stimme|verschluck"
                       r"|sonnenbrand|koffein|salz isst|zucker|essen müde|sitzt|riech|schmeck|knackt|zitter|körper|stille|dunkel"
                       r"|déjà|weinen|gedächtnis|vergess"),
    ("Weltall", r"weltall|planet|mond|sonne\b|mars|merkur|venus|jupiter|saturn|stern|galax|quasar|urknall|rakete|astronaut"
                r"|schwarzes loch|komet|asteroid|iss\b"),
    ("Natur & Erde", r"meer|ozean|see\b|fluss|vulkan|erdbeben|blitz|gewitter|regen|schnee|eis\b|wüste|wald|berg|wetter"
                     r"|wolke|strömung|tote meer|insel|küste|land\b|kontinent|australien|himmel|treibsand|sand"),
    ("Tiere", r"katze|hund|wal\b|hai\b|vogel|vögel|insekt|ameise|spinne|tier|fisch|pferd|elefant|krake|skorpion|biene|flamingo|frosch|schlange"),
    ("Technik & Alltag", r"handy|akku|ladegerät|aufzug|wlan|internet|computer|auto\b|kühlschrank|mikrowelle|flugzeug|zug\b"
                         r"|strom|batterie|lampe|maschine|roboter|wolkenkratzer|cent|friseur|cola|mentos|zwiebel"),
    ("Autos, Firmen & Geld", r"ferrari|porsche|audi|bmw|mercedes|tesla|vw\b|volkswagen|skoda|lamborghini|toyota|opel|rolls|marke|firma"),
    ("Echte Rätsel & Geschichte", r"\b1\d{3}\b|jahrhundert|antik|römer|pyramide|pharao|ritter|krieg|schlacht|kaiser|könig"
                                  r"|tempel|grab|schrift|verschwund|expedition|ötzi|mauer"),
]
FIELDS = [(name, re.compile(rx, re.I)) for name, rx in FIELDS]


def topic_field(spec):
    """Themenfeld eines Shorts. Ausgedachte Grusel- und Alltagsgeschichten bekommen ihr eigenes Feld."""
    niche = str(spec.get("niche", "")).lower()
    if niche == "horror":
        return "Grusel (ausgedacht)"
    if niche == "erzählung":
        return "Alltagsgeschichte (ausgedacht)"
    if niche in ("mystery", "geschichte"):
        return "Echte Rätsel & Geschichte"
    if niche == "psychologie":
        return "Psychologie & Gehirn"
    if niche in ("business", "geld", "geld & finanzen"):
        return "Autos, Firmen & Geld"
    segs = spec.get("segments") or []
    text = " ".join([plain_title(spec.get("title"))] + [str(s.get("text", "")) for s in segs[:2]]).replace("*", "")
    for name, rx in FIELDS:
        if rx.search(text):
            return name
    return "Sonstiges"


# --- Zwischen-Haken (going-viral: „re-hook at the dips“) ----------------------------------
REHOOK = re.compile(
    r"^(aber|doch|dann|und dann|jetzt|plötzlich|erst|warte|bis|nur|das seltsamste|das verrückte|der haken|der trick"
    r"|das eigentliche|noch seltsamer|und es wird|es wird|hier wird|genau da|ab da|ab hier)\b|\baber\s+(dann|erst|jetzt)\b",
    re.I)


def rehook(spec):
    """„mit“, wenn zwischen ca. 25 % und 70 % des Textes ein Satz die Spannung neu anzieht, sonst „ohne“.

    Nur für Shorts (lange Videos haben ihre eigene Dramaturgie)."""
    if str(spec.get("laenge", "")).lower() == "lang":
        return None
    segs = [str(s.get("text", "")).replace("*", "").strip() for s in spec.get("segments") or []]
    if len(segs) < 4:
        return None
    total = sum(len(s.split()) for s in segs) or 1
    seen = 0
    for i, s in enumerate(segs):
        if i and 0.2 <= seen / total <= 0.7 and REHOOK.search(s):
            return "mit"
        seen += len(s.split())
    return "ohne"


# --- Vielfalt beim Einstieg (going-viral: „rotate the angle every post“) -------------------
def opener(spec):
    """Die ersten zwei Wörter des ersten Satzes, klein geschrieben (z. B. „plötzlich liegt“ -> „plötzlich“)."""
    segs = spec.get("segments") or [{}]
    words = re.findall(r"[\wäöüß]+", str(segs[0].get("text", "")).lower())
    return words[0] if words else ""


QUESTION_OPENERS = {"was", "warum", "wieso", "weshalb", "wie", "wer", "wo"}


def sameness(spec, recent):
    """Tipps, wenn ein neues Skript genauso anfängt oder heißt wie viele der letzten (recent: Liste von Skripten)."""
    tips = []
    if not recent:
        return tips
    first = opener(spec)
    if first in QUESTION_OPENERS:   # „Was passiert, wenn du …?“ ist bei Erklärvideos das Format, kein Massenware-Zeichen
        first = ""
    n = sum(1 for r in recent if opener(r) == first)
    if first and n >= max(4, len(recent) // 5):
        tips.append(f"Einstieg „{first.capitalize()} …“ hatten {n} der letzten {len(recent)} Skripte. "
                    "Lieber anders anfangen (Frage, Zahl, Regel, mitten in der Handlung), sonst wirkt es wie Massenware.")
    pat = title_pattern(spec.get("title"), spec.get("niche"))
    if pat in ("Das X, das niemand …", "Aussage/Fakt"):
        m = sum(1 for r in recent if title_pattern(r.get("title"), r.get("niche")) == pat)
        if m >= max(5, len(recent) * 2 // 5):
            tips.append(f"Titel nach dem Muster „{pat}“ hatten {m} der letzten {len(recent)}. "
                        "Ein anderes Muster wählen (Frage, Regel, Wahl-Frage).")
    if re.search(r"\bniemand\w*\b", plain_title(spec.get("title")), re.I):
        m = sum(1 for r in recent if re.search(r"\bniemand\w*\b", plain_title(r.get("title")), re.I))
        if m >= max(4, len(recent) // 5):
            tips.append(f"„niemand“ stand in {m} der letzten {len(recent)} Titel. Ein anderes Spannungswort nehmen.")
    return tips


# --- Kompass für die Zentrale und die tägliche Skript-Aufgabe --------------------------------
COMPASS_KEYS = (("themenfeld", "Themenfeld"), ("titel_muster", "Titel-Muster"), ("typ", "Video-Typ"),
                ("welt_typ", "Look je Video-Typ"), ("zwischenhaken", "Zwischen-Haken"), ("platz", "Upload des Tages"))
MIN_N = 4          # so viele bewertete Videos braucht ein Wert, bevor der Kompass ihn nennt
CLEAR = 1.25       # ab diesem Faktor zum Schnitt gilt ein Wert als „klar vorn“


def compass(rows):
    """Aus den Zeilen von learn.feature_summary: je Merkmal Bester und Schwächster plus ehrliche Empfehlungen."""
    by = {r["key"]: r for r in rows}
    out, advice = [], []
    for key, label in COMPASS_KEYS:
        vals = [v for v in (by.get(key) or {}).get("values", []) if v.get("videos", 0) >= MIN_N and v.get("rel")]
        if len(vals) < 2:
            continue
        vals.sort(key=lambda v: v["rel"], reverse=True)
        best, worst = vals[0], vals[-1]
        out.append({"key": key, "label": label, "best": best, "worst": worst, "values": vals})
        if key == "themenfeld" and best["rel"] >= CLEAR:
            advice.append(f"Schärfere Nische: „{best['value']}“ läuft {best['rel']:.1f}× so gut wie üblich. "
                          f"Mehr Skripte aus diesem Feld, „{worst['value']}“ ({worst['rel']:.1f}×) seltener.")
        if key == "titel_muster" and best["rel"] >= CLEAR:
            advice.append(f"Titel: Muster „{best['value']}“ ({best['rel']:.1f}×) öfter nehmen, "
                          f"„{worst['value']}“ ({worst['rel']:.1f}×) seltener.")
        if key == "zwischenhaken":
            mit = next((v for v in vals if v["value"] == "mit"), None)
            ohne = next((v for v in vals if v["value"] == "ohne"), None)
            if mit and ohne and mit["rel"] >= ohne["rel"] * 1.15:
                advice.append("Zwischen-Haken wirkt: Shorts mit einem „Aber dann …“-Satz in der Mitte laufen besser.")
        if key == "platz":
            first = next((v for v in vals if v["value"].startswith("1.")), None)
            late = next((v for v in vals if v["value"].startswith("11.")), None)
            if first and late and late["rel"] < first["rel"] * 0.5:
                advice.append(f"Ehrlich: Uploads 11 bis 15 am Tag laufen nur {late['rel']:.1f}× (1 bis 5: {first['rel']:.1f}×). "
                              "Weniger, dafür stärkere Shorts am Tag würden wohl mehr bringen.")
    return {"rows": out, "advice": advice}


def public_stats(videos, specs=None):
    """Für docs/nische.json (GitHub Actions): Muster und Felder aus öffentlichen Aufrufen, als Median je Gruppe.

    videos: [{title, views}], specs: {Titel ohne Emoji (klein): Skript} aus seed/. Grob, aber ohne Server lesbar
    für die tägliche Skript-Aufgabe (die genaue, faire Rechnung macht die Zentrale)."""
    specs = specs or {}

    def med(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if xs else 0
    rated = [v for v in videos if v.get("views")]
    base = med([v["views"] for v in rated]) or 1
    groups = {"titel_muster": {}, "themenfeld": {}, "zwischenhaken": {}}
    for v in rated:
        spec = specs.get(plain_title(v.get("title")).lower()) or {"title": v.get("title"), "segments": []}
        groups["titel_muster"].setdefault(title_pattern(spec.get("title"), spec.get("niche", "")), []).append(v["views"])
        groups["themenfeld"].setdefault(topic_field(spec), []).append(v["views"])
        hook = rehook(spec)
        if hook:
            groups["zwischenhaken"].setdefault(hook, []).append(v["views"])
    out = {"videos": len(rated), "median": base}
    for key, g in groups.items():
        out[key] = sorted(({"value": k, "videos": len(xs), "median": med(xs), "faktor": round(med(xs) / base, 2)}
                           for k, xs in g.items() if len(xs) >= 3), key=lambda r: -r["faktor"])
    return out
