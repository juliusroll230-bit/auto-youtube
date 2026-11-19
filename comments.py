"""Antworten auf YouTube-Kommentare: kurz, freundlich, ehrlich und ohne Spam.

Die App liest alle 30 Minuten die neuesten Kommentare unter den Videos des Hauptkanals und
antwortet selbst auf einfache Fälle (Lob, Grusel-Reaktionen, „Ist das echt?“ bei ausgedachten
Geschichten, Themenwünsche, „Ist das KI?“). Alles, was echtes Wissen oder Fingerspitzengefühl
braucht (Fragen zu Fakten und Quellen, Korrekturen, ernste Themen, lange Texte), landet unter
„Für dich“ in der Zentrale. Beleidigungen, Links und Werbung bekommen keine Antwort.

Antworten schreiben braucht bei Google die Berechtigung youtube.force-ssl. Die Anmeldung per
Geräte-Code (Upload-Zugang) darf die nicht haben, darum läuft es über den zweiten Zugang
(Webanwendung, siehe yt.py → Zuschauer-Daten), der sie seit 18.11.2026 mit anfragt.

Die Daten liegen in comments.json.
"""
import datetime as dt
import glob
import os
import random
import re

import store

FILE = "comments.json"
DEFAULTS = {"on": False, "mode": "auto", "per_day": 20}
PER_DAY = (1, 50)
MODES = ("auto", "freigabe")
CHECK_MIN = 30        # so oft wird nachgeschaut
MAX_PER_RUN = 5       # höchstens so viele Antworten pro Durchgang (nicht alles auf einmal)
MAX_AGE_DAYS = 3      # ältere Kommentare bleiben unbeantwortet
HOURS = (8, 22)       # nur tagsüber antworten
KEEP_LOG, KEEP_TODO, KEEP_WISHES = 120, 60, 40

# --- Erkennen ------------------------------------------------------------------

LINK = re.compile(r"https?://|www\.|\b[\w-]+\.(com|de|net|org|ly|io|gg|tv|me|link)\b|t\.me/|discord\.gg", re.I)
SPAM = re.compile(r"sub ?4 ?sub|abo gegen abo|abonnier\w* (mich|meinen)|schau\w* (mal )?(auf |bei )?mein\w* kanal|"
                  r"mein(en)? kanal|check (out )?my|my channel|telegram|whats ?app|krypto|crypto|bitcoin|forex|"
                  r"gewinnspiel|investier|onlyfans|promo|\+\d{6,}", re.I)
INSULT = re.compile(r"hurensohn|\bhure\b|wichser|fotze|missgeburt|\bspast|behindert|schwuchtel|\bnazi|hitler|"
                    r"arschloch|\bfick|fresse|bastard|\bidiot|\bopfer\b|nigg|neger|\bkys\b|verreck|\bstirb\b", re.I)
SENSITIVE = re.compile(r"selbstmord|suizid|umbringen|\britz|sterben will|nicht mehr leben|depress|missbrauch|"
                       r"gemobbt|mobbing|\bhilfe\b|polizei|notfall|geschlagen|ich hab angst vor (meinem|meiner)", re.I)
NEGATIVE = re.compile(r"müll|scheiß|scheiss|schlecht|langweilig|cringe|\bslop\b|schrott|\bdumm|peinlich|nervig|"
                      r"unnötig|clickbait|dislike", re.I)
CORRECTION = re.compile(r"stimmt nicht|stimmt doch nicht|\bfalsch|\bfake\b|gelogen|\blüge|\bquelle|beweis|fehler|"
                        r"nicht wahr|stimmt das|unsinn|quatsch", re.I)
REAL_Q = re.compile(r"(ist|war) (das|die geschichte|es|der fall|das alles) (wirklich |echt )?(echt|wahr|real|passiert)|"
                    r"echt passiert|wirklich passiert|wahre geschichte|true story|is (this|it) real", re.I)
PART2 = re.compile(r"teil ?(2|zwei)|part ?2|fortsetzung|wie geht.{0,12}weiter", re.I)
WISH = re.compile(r"mach\w* (mal |doch |bitte |auch |ein |einen |n |noch )*(video|eins|teil|was|folge|short)|"
                  r"kannst du (mal |bitte |auch |noch )*.{0,50}(machen|erklären)|video (über|zu|von)\b|"
                  r"^idee\b|vorschlag|mach\w* (mal |doch |bitte )*(was|eins) (über|zu)", re.I)
AI = re.compile(r"\bki\b|\bai\b|künstliche intelligenz|ki-?stimme|roboter-? ?stimme|chat ?gpt|computerstimme", re.I)
FIRST = re.compile(r"^\W*(erster|erste|first|1\.?)\W*!*\W*$", re.I)
SCARED = re.compile(r"grusel|gänsehaut|angst|creepy|horror|unheimlich|nicht (mehr )?schlafen|schauder|"
                    r"😱|👻|💀|😨|😰|😳", re.I)
LEARNED = re.compile(r"wusste ich nicht|wieder was gelernt|was gelernt|nie gewusst|interessant|lehrreich|"
                     r"jetzt weiß ich", re.I)
PRAISE = re.compile(r"cool|krass|nice|geil|stark|super|toll|mega|\bwow|gut gemacht|gutes video|\btop\b|lustig|"
                    r"haha|\blol\b|schön|süß|liebe (den|deine|eure|das)|bester|weiter so|gefällt|richtig gut|"
                    r"love|amazing|great|awesome|😂|🔥|❤|♥|👍|💯|🙌|😍|🥰", re.I)
GERMAN = re.compile(r"\b(der|die|das|und|ist|ich|nicht|ein|eine|du|wie|was|mit|auch|aber|so|mal|echt|schon)\b", re.I)
ENGLISH = re.compile(r"\b(the|this|is|what|and|you|it|was|so|that|of|my|i|why|how|video)\b", re.I)

# Antworten: kurz, ohne Links, ohne Werbung, ohne Versprechen. Mehrere Varianten, damit nichts doppelt klingt.
REPLIES = {
    "praise": ["Danke dir! 🙌", "Freut mich, dass es dir gefällt 😊", "Danke fürs Zuschauen! 🙂",
               "Danke, das freut uns echt 🙌", "Schön, dass du dabei bist 😊", "Danke für den netten Kommentar! 🙂",
               "Danke! Morgen kommt schon das nächste Video 🙂"],
    "praise_en": ["Thank you! 🙌", "Thanks for watching! 🙂", "Glad you liked it 😊"],
    "learned": ["Freut mich, dass du was Neues mitnimmst! 🙂", "Genau dafür machen wir die Videos 😊",
                "Ging uns beim Recherchieren genauso 😄", "Danke! Schön, wenn man etwas Neues lernt 🙂"],
    "scared": ["Dann hat die Geschichte ja funktioniert 👻", "Licht anlassen hilft 😄", "Sorry für die Gänsehaut 😅👻",
               "Freut mich, dass es dich gegruselt hat 👻", "Gut, dass es nur eine Geschichte ist 😄"],
    "real_fiction": ["Nein, die Geschichte ist ausgedacht 🙂 Gruselig sollte sie trotzdem sein.",
                     "Keine Sorge, das ist eine ausgedachte Geschichte 😄",
                     "Ausgedacht! Aber schön, dass sie echt gewirkt hat 🙂"],
    "real_story": ["Nein, die Geschichte ist ausgedacht 🙂 Schön, dass sie dich erreicht hat.",
                   "Ausgedacht, aber mit Liebe erzählt 😊"],
    "real_mystery": ["Ja, den Fall gibt es wirklich. Viele Fragen dazu sind bis heute offen.",
                     "Ja, das ist wirklich passiert. Eine ganz sichere Erklärung gibt es bis heute nicht."],
    "part2": ["Eine Fortsetzung gibt es nicht, jedes Video ist eine eigene Geschichte. Morgen kommt die nächste 🙂",
              "Kein Teil 2, aber jeden Tag kommen neue Videos 🙂"],
    "wish": ["Danke für die Idee! Sie steht jetzt auf unserer Themenliste 🙂",
             "Gute Idee, ist notiert 📝", "Danke! Die Idee kommt auf unsere Liste 🙂"],
    "ai": ["Ja, Stimme und Animation entstehen mit KI. Danke, dass du trotzdem reinschaust 🙂",
           "Stimmt, die Stimme ist eine KI-Stimme 🙂 Die Themen werden trotzdem sorgfältig ausgesucht."],
    "first": ["Schnell gewesen ⚡", "Stark, du warst der Schnellste ⚡"],
    "thanks": ["Danke für deinen Kommentar! 🙂", "Danke fürs Schreiben 🙂", "Danke dir fürs Zuschauen! 🙂"],
}
KIND_LABEL = {"praise": "Lob", "praise_en": "Lob", "learned": "Lob", "scared": "Grusel", "real_fiction": "Ist das echt?",
              "real_story": "Ist das echt?", "real_mystery": "Ist das echt?", "part2": "Teil 2?", "wish": "Themenwunsch",
              "ai": "KI-Frage", "first": "Erster", "thanks": "Kommentar"}


def classify(text, vtype=""):
    """Was mit einem Kommentar passiert: ("reply", art), ("todo", grund) oder ("skip", grund)."""
    t = (text or "").strip()
    low = t.lower()
    if not t:
        return "skip", "leer"
    if LINK.search(t) or SPAM.search(t):
        return "skip", "Link oder Werbung"
    if INSULT.search(t):
        return "skip", "Beleidigung"
    if SENSITIVE.search(t):
        return "todo", "Ernstes Thema, bitte selbst lesen"
    if NEGATIVE.search(t) and not PRAISE.search(t):
        return "skip", "Kritik, keine Antwort nötig"
    if len(t) > 220:
        return "todo", "Langer Kommentar"
    horror = vtype == "Horror"
    story = vtype == "Erzählte Geschichte"
    if REAL_Q.search(t):
        if horror:
            return "reply", "real_fiction"
        if story:
            return "reply", "real_story"
        if vtype == "Mystery":
            return "reply", "real_mystery"
        return "todo", "Frage, ob es stimmt"
    if CORRECTION.search(t):
        return "todo", "Frage oder Korrektur zu Fakten"
    letters = re.sub(r"[^a-zäöüß]", "", low)
    if letters and len(ENGLISH.findall(low)) > len(GERMAN.findall(low)) + 1:
        return ("reply", "praise_en") if PRAISE.search(t) and "?" not in t else ("todo", "Englischer Kommentar")
    if PART2.search(t):
        return "reply", "part2"
    if WISH.search(t):
        return "reply", "wish"
    if AI.search(t):
        return "reply", "ai"
    if FIRST.match(t):
        return "reply", "first"
    if "?" in t:
        return "todo", "Frage"
    if (horror or story or not letters) and SCARED.search(t):
        return "reply", "scared"
    if LEARNED.search(t):
        return "reply", "learned"
    if PRAISE.search(t) or not letters:
        return "reply", "praise"
    if len(t) <= 120:
        return "reply", "thanks"
    return "todo", "Nicht sicher, was passt"


def pick(kind, recent):
    """Eine Antwort-Variante, die in den letzten Antworten nicht vorkam (sonst irgendeine)."""
    options = REPLIES[kind]
    fresh = [o for o in options if o not in recent]
    return random.choice(fresh or options)


# --- Speicher ------------------------------------------------------------------

def load():
    d = store.read(FILE, {}) or {}
    return {"settings": {**DEFAULTS, **d.get("settings", {})}, "seen": d.get("seen", {}), "log": d.get("log", []),
            "todo": d.get("todo", []), "wishes": d.get("wishes", []), "status": d.get("status", {})}


def save(d):
    cutoff = (store.now() - dt.timedelta(days=21)).isoformat()
    d["seen"] = {k: v for k, v in d["seen"].items() if v >= cutoff}
    d["log"], d["todo"], d["wishes"] = d["log"][:KEEP_LOG], d["todo"][:KEEP_TODO], d["wishes"][:KEEP_WISHES]
    store.write(FILE, d)


def set_settings(on=None, mode=None, per_day=None):
    with store.LOCK:
        d = load()
        s = d["settings"]
        if on is not None:
            s["on"] = bool(on)
        if mode is not None:
            if mode not in MODES:
                raise ValueError("Unbekannter Modus.")
            s["mode"] = mode
        if per_day is not None:
            s["per_day"] = max(PER_DAY[0], min(PER_DAY[1], int(per_day)))
        save(d)
        return s


def replied_today(d):
    today = store.now().date().isoformat()
    return sum(1 for e in d["log"] if e.get("sent") and e.get("at", "")[:10] == today)


def _niches():
    """slug → (Video-Typ) aus den hochgeladenen Skripten, damit die Antwort zum Video passt."""
    import learn
    out = {}
    for f in glob.glob(store.path("posted", "*.json")):
        try:
            spec = __import__("json").load(open(f, encoding="utf-8"))
            out[spec.get("slug") or os.path.basename(f)[5:-5]] = learn.video_type(spec)
        except (OSError, ValueError):
            continue
    return out


def videos():
    """video_id → {title, type} für die Videos des Hauptkanals."""
    types = _niches()
    return {u["video_id"]: {"title": u.get("title", ""), "type": types.get(u.get("slug"), "")}
            for u in store.state()["uploads"] if u.get("channel") != "clips"}


# --- Ablauf --------------------------------------------------------------------

def access(cfg):
    """"ok", "zugang" (Berechtigung fehlt: Zuschauer-Daten neu verbinden) oder "kanal" (anderer Kanal verbunden)."""
    if not cfg.get("refresh_token"):
        return "kanal_fehlt"
    if not (cfg.get("analytics_token") and "youtube.force-ssl" in cfg.get("analytics_scopes", "")):
        return "zugang"
    return "ok"


def due(d, now=None):
    now = now or store.now()
    s = d["settings"]
    if not s["on"] or not (HOURS[0] <= now.hour < HOURS[1]):
        return False
    last = d["status"].get("checked_at")
    pause = d["status"].get("pause_until")
    if pause and now.isoformat() < pause:
        return False
    return not last or (now - dt.datetime.fromisoformat(last)).total_seconds() >= CHECK_MIN * 60


def process(threads, d, own_channel, vids, now=None):
    """Sortiert neue Kommentare ein. Gibt die zu sendenden Antworten zurück: [(eintrag, text)].

    threads: yt.comment_threads(...) – je {id, video_id, author, author_channel, text, at, own_reply}.
    Verändert d (seen, todo, wishes, log für Übersprungenes).
    """
    now = now or store.now()
    s = d["settings"]
    budget = min(MAX_PER_RUN, max(0, s["per_day"] - replied_today(d)))
    oldest = (now - dt.timedelta(days=MAX_AGE_DAYS)).isoformat()
    recent = [e.get("reply", "") for e in d["log"][:20]]
    today = now.date().isoformat()
    authors_today = {e.get("author_channel") for e in d["log"] if e.get("sent") and e.get("at", "")[:10] == today}
    send = []
    for c in sorted(threads, key=lambda x: x["at"]):
        if c["id"] in d["seen"] or c["author_channel"] == own_channel or c.get("own_reply"):
            continue
        if _iso(c["at"]) < oldest:
            d["seen"][c["id"]] = now.isoformat(timespec="seconds")
            continue
        v = vids.get(c["video_id"], {})
        what, why = classify(c["text"], v.get("type", ""))
        base = {"id": c["id"], "video_id": c["video_id"], "video": v.get("title", ""), "author": c["author"],
                "author_channel": c["author_channel"], "text": c["text"][:500], "comment_at": c["at"]}
        if what == "reply":
            if len(send) >= budget:
                break  # Rest kommt im nächsten Durchgang dran
            if c["author_channel"] in authors_today:
                continue  # höchstens eine Antwort pro Person und Tag
            text = pick(why, recent)
            recent.insert(0, text)
            if why == "wish":
                d["wishes"].insert(0, {"text": c["text"][:200], "author": c["author"], "video": v.get("title", ""),
                                       "at": now.isoformat(timespec="seconds")})
            entry = {**base, "kind": why, "label": KIND_LABEL.get(why, why)}
            if s["mode"] == "freigabe":
                d["todo"].insert(0, {**entry, "draft": text, "why": "Entwurf zum Freigeben",
                                     "at": now.isoformat(timespec="seconds")})
            else:
                send.append((entry, text))
                authors_today.add(c["author_channel"])
        elif what == "todo":
            d["todo"].insert(0, {**base, "why": why, "at": now.isoformat(timespec="seconds")})
        else:
            d["log"].insert(0, {**base, "at": now.isoformat(timespec="seconds"), "sent": False, "skip": why})
        d["seen"][c["id"]] = now.isoformat(timespec="seconds")
    return send


def _iso(stamp):
    """YouTube-Zeit (UTC, …Z) als deutsche Zeit im ISO-Format, damit sie mit store.now() vergleichbar ist."""
    try:
        return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(store.TZ).isoformat()
    except ValueError:
        return ""


def record_sent(d, entry, text, by="app"):
    d["log"].insert(0, {**entry, "reply": text, "sent": True, "by": by, "at": store.now().isoformat(timespec="seconds")})
    d["todo"] = [t for t in d["todo"] if t["id"] != entry["id"]]
    d["seen"][entry["id"]] = store.now().isoformat(timespec="seconds")


def error_text(e):
    text = str(e)
    if "insufficient" in text.lower() or "ACCESS_TOKEN_SCOPE_INSUFFICIENT" in text:
        return "zugang", "Google erlaubt noch keine Antworten. Bitte im Reiter Zuschauer einmal neu verbinden."
    if "quotaExceeded" in text or "dailyLimitExceeded" in text:
        return "quota", "Das YouTube-Tageslimit ist erreicht. Morgen geht es weiter."
    if "commentsDisabled" in text:
        return "aus", "Unter diesem Video sind Kommentare ausgeschaltet."
    if "processingFailure" in text or "invalidCommentMetadata" in text:
        return "text", "YouTube hat diese Antwort nicht angenommen."
    return "fehler", f"Kommentare: {text[:200]}"


def overview(cfg):
    d = load()
    acc = access(cfg)
    if acc == "ok" and d["status"].get("reason") in ("zugang", "kanal"):
        acc = d["status"]["reason"]
    return {"settings": d["settings"], "access": acc, "status": d["status"], "today": replied_today(d),
            "log": d["log"][:40], "todo": d["todo"][:30], "wishes": d["wishes"][:20],
            "sent_total": sum(1 for e in d["log"] if e.get("sent")), "has_client": bool(cfg.get("analytics_client_id"))}
