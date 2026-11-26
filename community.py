"""Community-Posts für den Hauptkanal: Umfragen und Bild-Posts, fertig zum Posten.

YouTube hat keine offizielle Schnittstelle, mit der eine App Community-Posts erstellen kann
(die Data API kann Videos hochladen, aber keine Posts). Darum schlägt die Zentrale jeden Tag
ein paar Posts vor: Text zum Kopieren, Umfrage-Antworten und ein fertiges Bild zum Herunterladen.
Julius postet sie in YouTube Studio > Erstellen > Beitrag erstellen.

Alle Inhalte kommen aus echten Daten (geplante Shorts, Aufrufe, Abos) oder sind Meinungsfragen.
Keine erfundenen Fakten.

  python3 community.py out/   speichert Beispielbilder
"""
import datetime as dt
import hashlib
import os
import random
import re
import sys

from PIL import Image, ImageDraw

import branding
from branding import ACCENT, FONT_BOLD, FONT_SEMI, RED, _emoji, _font, _glow, _gradient

FILE = "community.json"
SIZE = 1080             # YouTube zeigt Bilder in Beiträgen quadratisch am besten
OPTION_MAX = 65         # YouTube erlaubt pro Umfrage-Antwort höchstens 65 Zeichen
PER_DAY = 3             # so viele Posts plant die Zentrale am Tag ein (einstellbar 1 bis 5)
TIMES = {1: [17], 2: [12, 20], 3: [10, 14, 19], 4: [9, 14, 17, 20], 5: [9, 12, 15, 19, 21]}  # nicht zu den Shorts-Zeiten
MILESTONES = [10, 25, 50, 100, 150, 200, 250, 300, 400, 500, 750, 1000, 1500, 2000, 2500, 5000, 10000]

TYPE_LABEL = {"umfrage": "Umfrage", "bild": "Bild-Post", "text": "Beitrag"}

# Meinungsfragen ohne Fakten: funktionieren immer, auch ohne Daten.
OPINION_POLLS = [
    ("Was schaust du hier am liebsten? 👇",
     ["Was passiert, wenn …? 🤯", "Ungelöste Rätsel 🕵️", "Horror-Geschichten 👻", "Warum ist das so? 🤔"]),
    ("Welche Superkraft würdest du nehmen?",
     ["Gedanken lesen 🧠", "Fliegen 🕊️", "Zeit anhalten ⏸️", "Unsichtbar sein 👻"]),
    ("Wie lange hältst du ohne Handy aus? 📵",
     ["1 Stunde", "1 Tag", "1 Woche", "Ich würde es nicht schaffen 😅"]),
    ("Glaubst du an Geister? 👻", ["Ja", "Nein", "Ein bisschen 👀"]),
    ("Wie viele Stunden schläfst du meistens? 😴", ["Weniger als 6", "6 bis 8", "Mehr als 8"]),
    ("Würdest du eine Nacht allein in einem verlassenen Haus bleiben? 🏚️",
     ["Sofort", "Nur mit Freunden", "Niemals"]),
    ("Welches Rätsel willst du gelöst sehen? 🕵️",
     ["Verschwundene Menschen", "Geheimnisvolle Orte", "Seltsame Funde", "Unerklärte Signale"]),
    ("Kurz oder lang? ⏱️", ["Shorts 📱", "Lange Videos 🎬", "Beides 🔥"]),
    ("Wovor hast du am meisten Angst? 😨", ["Dunkelheit", "Höhe", "Tiefes Wasser", "Spinnen 🕷️"]),
    ("Wann schaust du am liebsten Shorts? 📱", ["Morgens", "Nach der Schule", "Abends im Bett 🛏️"]),
]

FIRMS = [("🚗", "Abo Motors"), ("🍔", "Abo Burger"), ("🚀", "Abo Space"), ("🎮", "Abo Games")]


# --- Hilfen -----------------------------------------------------------------------------------

def _clean(text):
    return re.sub(r"\s+", " ", str(text or "").replace("*", "")).strip()


_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]+")


def split_emoji(title):
    """'Was passiert, wenn …? 🌍' -> ('Was passiert, wenn …?', '🌍')."""
    title = _clean(title)
    found = _EMOJI_RE.findall(title)
    text = _EMOJI_RE.sub("", title).strip()
    return re.sub(r"\s{2,}", " ", text), (found[-1] if found else "")


def short_option(title):
    text, emo = split_emoji(title)
    text = re.sub(r"\s*\(Teil \d+\)", "", text)
    if len(text) > OPTION_MAX:
        text = text[:OPTION_MAX - 1].rsplit(" ", 1)[0].rstrip(",.:;!?-") + "…"
    return text


def _pid(kind, *parts):
    return kind + "-" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def _nf(n):
    return f"{int(n):,}".replace(",", ".")


def _day_word(when, today):
    if not when:
        return "bald"
    d = (when.date() - today).days
    return "heute" if d <= 0 else "morgen" if d == 1 else "bald"


def _upcoming_slots(hours, at, n):
    out, day = [], 0
    while len(out) < n and day < 30:
        for h in sorted(hours):
            slot = (at + dt.timedelta(days=day)).replace(hour=int(h), minute=0, second=0, microsecond=0)
            if slot > at:
                out.append(slot)
        day += 1
    return out[:n]


# --- Vorschläge -------------------------------------------------------------------------------

def suggestions(posted, planned, channel=None, hours=(), now=None, shuffle=0, firma=False):
    """Bis zu 5 Posts für heute. posted: Uploads (store.posted_items), planned: geplante Specs in Reihenfolge."""
    now = now or dt.datetime.now()
    today = now.date()
    rnd = random.Random(f"{today.isoformat()}|{shuffle}")
    channel = channel or {}
    name = channel.get("title") or "60 Sekunden Wissen"
    shorts = [v for v in posted if v.get("kind") != "clip" and v.get("video_id")]
    slots = _upcoming_slots(hours or [8, 11, 13, 16, 18], now, len(planned))
    posts = []

    # 1) Frage-Bild: die Frage eines geplanten Erklärvideos, Auflösung kommt als Short
    teasers = [(i, s) for i, s in enumerate(planned)
               if str(s.get("title", "")).lower().startswith(("was passiert", "warum"))]
    if teasers:
        i, spec = teasers[shuffle % len(teasers)]
        q, emo = split_emoji(spec["title"])
        when = _day_word(slots[i] if i < len(slots) else None, today)
        posts.append({
            "id": _pid("frage", spec.get("slug"), today), "type": "bild", "image": "frage",
            "title": "Frage an deine Zuschauer",
            "why": "Leute raten in den Kommentaren. Später sehen sie die Auflösung im Short.",
            "text": f"{q} {emo}".strip() + f"\n\nWas glaubst du? Schreib es in die Kommentare 👇\n"
                    f"Die Auflösung kommt {when} als Short.",
            "img": {"emoji": emo or "🤯", "big": q, "label": "WAS GLAUBST DU?",
                    "foot": f"Auflösung {when} als Short"},
        })

    # 2) Umfrage: welches geplante Video zuerst?
    titles = []
    for s in planned:
        o = short_option(s.get("title", ""))
        if o and o not in titles:
            titles.append(o)
    if len(titles) >= 2:
        pick = titles[:6]
        rnd.shuffle(pick)
        posts.append({
            "id": _pid("wahl", today, *pick[:3]), "type": "umfrage",
            "title": "Welches Video zuerst?",
            "why": "Zuschauer stimmen über kommende Shorts ab und schauen dann nach, ob ihres kommt.",
            "text": "Diese Videos kommen bald. Welches willst du zuerst sehen? 👇",
            "options": pick[:3],
        })

    # 3) Bild: meistgesehener Short der letzten 7 Tage
    week = [v for v in shorts if (v.get("views") or 0) > 0 and str(v.get("posted_at", ""))[:10] >= (today - dt.timedelta(days=7)).isoformat()]
    pool = week or [v for v in shorts if (v.get("views") or 0) > 0]
    if pool:
        top = max(pool, key=lambda v: v.get("views") or 0)
        t, emo = split_emoji(top.get("title", ""))
        posts.append({
            "id": _pid("top", top["video_id"], today), "type": "bild", "image": "top",
            "title": "Bestes Video zeigen",
            "why": "Schickt neue Leute zu dem Short, der schon am besten läuft.",
            "text": f"🔥 {_nf(top['views'])} Leute haben das schon gesehen:\n{t} {emo}".rstrip()
                    + f"\n\n👉 https://youtube.com/shorts/{top['video_id']}",
            "img": {"emoji": emo or "🔥", "big": t, "label": "MEISTGESEHEN" + (" DIESE WOCHE" if week else ""),
                    "foot": f"{_nf(top['views'])} Aufrufe"},
            "video_id": top["video_id"],
        })

    # 4) Meinungs-Umfrage (wechselt täglich)
    q, opts = OPINION_POLLS[(today.toordinal() + shuffle) % len(OPINION_POLLS)]
    posts.append({"id": _pid("meinung", q, today), "type": "umfrage", "title": "Meinungsfrage",
                  "why": "Leicht zu beantworten. Jede Stimme zeigt YouTube, dass der Kanal lebt.",
                  "text": q, "options": list(opts)})

    # 5) Danke-Bild beim letzten erreichten Abo-Ziel
    subs = int(channel.get("subscribers") or 0)
    reached = [m for m in MILESTONES if m <= subs]
    if reached:
        m = reached[-1]
        nxt = next((x for x in MILESTONES if x > subs), None)
        posts.append({
            "id": _pid("danke", m), "type": "bild", "image": "danke",
            "title": f"Danke für {_nf(m)} Abos",
            "why": "Einmal pro Abo-Ziel posten. Macht neugierig und zeigt, dass der Kanal wächst.",
            "text": f"Danke! Wir sind jetzt über {_nf(m)} Abonnenten ❤️\n"
                    + (f"Schaffen wir die {_nf(nxt)}? Erzähl deinen Freunden von {name} 🙌" if nxt else ""),
            "img": {"emoji": "❤️", "big": _nf(m), "label": "DANKE", "foot": "Abonnenten"},
        })

    # 6) Firmen-Spiel: welche Firma ist am besten?
    if firma:
        posts.append({"id": _pid("firma", today), "type": "umfrage", "title": "Firmen-Spiel",
                      "why": "Jeder Abonnent arbeitet in den Firmen mit. Wer abstimmt, fühlt sich als Teil davon.",
                      "text": "In welcher Firma würdest du am liebsten arbeiten? 👇\nAbonnieren = du bist dabei.",
                      "options": [f"{e} {n}" for e, n in FIRMS]})

    # 7) Beitrag: Ankündigung des Tages mit den echten Sendezeiten
    todays = [(sl, sp) for sl, sp in zip(slots, planned) if sl.date() == today]
    if todays:
        first = split_emoji(todays[0][1].get("title", ""))
        times = ", ".join(f"{sl.hour}" for sl, _ in todays)
        posts.append({"id": _pid("heute", today, len(todays)), "type": "text", "title": "Ankündigung für heute",
                      "why": "Erinnert Abonnenten daran, heute wiederzukommen.",
                      "text": f"Heute kommen noch {len(todays)} neue Shorts 🔔\nUm {times} Uhr.\n\n"
                              f"Als Nächstes: {first[0]} {first[1]}".rstrip()})

    # 8) Beitrag: Frage an die Community (Kommentare = neue Themen)
    asks = [
        ("Was soll ich als Nächstes erklären? 🤔",
         "Schreib deine Frage in die Kommentare. Am besten so: „Was passiert, wenn …?“\n"
         "Die besten Fragen werden zu Shorts 👇"),
        ("Welches Rätsel hat dich nie losgelassen? 🕵️",
         "Ein verschwundenes Schiff, ein seltsamer Fund, ein Ort, über den keiner spricht?\n"
         "Schreib es in die Kommentare. Vielleicht wird es der nächste Short 👇"),
        ("Was ist das Gruseligste, das dir je passiert ist? 👻",
         "Schreib es in die Kommentare. Die besten Geschichten lesen wir alle 👇"),
    ]
    q, body = asks[(today.toordinal() + shuffle) % len(asks)]
    posts.append({"id": _pid("frag", q, today), "type": "text", "title": "Frage an die Community",
                  "why": "Kommentare zeigen YouTube, dass der Kanal lebt, und bringen dir neue Themen.",
                  "text": f"{q}\n\n{body}"})

    # 9) Beitrag: Wusstest du? Ein Satz aus einem eigenen Short (keine neuen Fakten), mit Link
    facts = [v for v in shorts if len(v.get("sentences") or []) >= 3 and v.get("video_id")]
    if facts:
        facts.sort(key=lambda v: v.get("views") or 0, reverse=True)
        v = facts[(today.toordinal() + shuffle) % min(len(facts), 8)]
        fact = _clean(v["sentences"][1])
        posts.append({"id": _pid("wusst", v["video_id"], today), "type": "text", "title": "Wusstest du?",
                      "why": "Ein Satz aus einem deiner Shorts macht neugierig auf das ganze Video.",
                      "text": f"Wusstest du? 🤯\n{fact}\n\nDie ganze Geschichte in 22 Sekunden:\n"
                              f"👉 https://youtube.com/shorts/{v['video_id']}"})

    # 10) Beitrag: Hinter den Kulissen (ehrlich, mit KI-Hinweis)
    posts.append({"id": _pid("kulisse", today.isocalendar()[1]), "type": "text", "title": "Hinter den Kulissen",
                  "why": "Einmal pro Woche reicht. Zuschauer mögen sehen, wie die Videos entstehen.",
                  "text": "So entsteht ein Short bei uns 🎬\n1. Eine Frage, die keiner beantworten kann\n"
                          "2. Recherche und ein Skript mit ca. 22 Sekunden\n3. Strichmännchen animieren\n"
                          "4. Vertonen mit KI-Stimme und Untertitel dazu\n\n"
                          "Welche Frage sollen wir als Nächstes nehmen? 👇"})

    for p in posts:
        p["label"] = TYPE_LABEL[p["type"]]
    # gemischt: erst die starken Posts, Beiträge dazwischen
    order = ["frage", "heute", "wahl", "frag", "top", "wusst", "meinung", "danke", "firma", "kulisse"]
    posts.sort(key=lambda p: order.index(p["id"].split("-")[0]))
    return posts


# --- Bilder -----------------------------------------------------------------------------------

def _wrap(d, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit(d, text, width, max_h, start=104, low=48):
    size = start
    while size > low:
        f = _font(FONT_BOLD, size)
        lines = _wrap(d, text, f, width)
        if len(lines) * size * 1.12 <= max_h and all(d.textlength(x, font=f) <= width for x in lines):
            return f, lines, size
        size -= 4
    f = _font(FONT_BOLD, low)
    return f, _wrap(d, text, f, width), low


def render(post, channel_title="60 Sekunden Wissen"):
    """Quadratisches Bild (1080x1080) im Look des Kanals."""
    s = SIZE
    info = post.get("img") or {}
    img = _gradient(s, s)
    _glow(img, (s * 0.22, s * 0.18), s * 0.42, (120, 80, 255), 90)
    _glow(img, (s * 0.85, s * 0.9), s * 0.45, (255, 120, 80), 45)
    d = ImageDraw.Draw(img, "RGBA")
    pad = 84
    # Kopf: Kanal-Name mit kleinem Timer-Ring
    branding._timer_ring(d, pad + 26, pad + 26, 24, 7, 0.78)
    d.text((pad + 70, pad + 26), channel_title.upper(), font=_font(FONT_SEMI, 32), anchor="lm", fill=(255, 255, 255, 215))

    kind = post.get("image")
    if kind == "danke":
        em = _emoji(info.get("emoji") or "❤️", 150)
        img.alpha_composite(em, (s // 2 - em.width // 2, 250))
        d.text((s / 2, 500), info.get("label", "DANKE"), font=_font(FONT_SEMI, 46), anchor="mm", fill=ACCENT)
        big = info.get("big", "")
        size = 300
        while d.textlength(big, font=_font(FONT_BOLD, size)) > s - 2 * pad and size > 120:
            size -= 10
        d.text((s / 2, 680), big, font=_font(FONT_BOLD, size), anchor="mm", fill=(255, 255, 255))
        d.text((s / 2, 870), info.get("foot", ""), font=_font(FONT_SEMI, 58), anchor="mm", fill=(225, 225, 235))
    else:
        em = _emoji(info.get("emoji") or "🤯", 170)
        img.alpha_composite(em, (pad, 200))
        d.text((pad, 420), info.get("label", ""), font=_font(FONT_SEMI, 40), anchor="lm", fill=ACCENT)
        f, lines, size = _fit(d, info.get("big", ""), s - 2 * pad, 360)
        y = 470
        for line in lines:
            d.text((pad, y), line, font=f, fill=(255, 255, 255), stroke_width=2, stroke_fill=(10, 10, 20))
            y += int(size * 1.12)
        # Fuß: Pille mit rotem Punkt
        foot = info.get("foot", "")
        if foot:
            ff = _font(FONT_SEMI, 38)
            w = int(d.textlength(foot, font=ff)) + 96
            y0 = s - pad - 74
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))  # eigene Ebene: durchscheinend über dem Verlauf
            ImageDraw.Draw(layer).rounded_rectangle((pad, y0, pad + w, y0 + 74), radius=37, fill=(255, 255, 255, 30),
                                                    outline=(255, 255, 255, 70), width=2)
            img.alpha_composite(layer)
            d.ellipse((pad + 30, y0 + 28, pad + 48, y0 + 46), fill=RED)
            d.text((pad + 66, y0 + 37), foot, font=ff, anchor="lm", fill=(255, 255, 255))
    return img.convert("RGB")


def watermark(size=300):
    """Wasserzeichen für YouTube (Kanal > Branding > Wasserzeichen): quadratisch, durchsichtig, unter 1 MB.

    Ein runder Knopf mit dem Timer-Ring und der 60, wie das Profilbild. Dunkel gefüllt, damit er auf
    hellen und dunklen Videos gut zu sehen ist.
    """
    k = 4  # groß zeichnen, dann verkleinern: glatte Kanten
    big = size * k
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    c, r = big / 2, big * 0.47
    d.ellipse((c - r, c - r, c + r, c + r), fill=(22, 16, 52, 235))
    rr, w = big * 0.40, int(big * 0.07)
    d.ellipse((c - rr, c - rr, c + rr, c + rr), outline=(86, 78, 128, 255), width=w)
    d.arc((c - rr, c - rr, c + rr, c + rr), start=-90, end=-90 + 360 * 0.78, fill=RED + (255,), width=w)
    d.text((c, c - big * 0.04), "60", font=_font(FONT_BOLD, int(big * 0.36)), anchor="mm", fill=(255, 255, 255))
    d.text((c, c + big * 0.2), "SEK", font=_font(FONT_SEMI, int(big * 0.1)), anchor="mm", fill=ACCENT)
    return img.resize((size, size), Image.LANCZOS)


# --- Gepostet abhaken -------------------------------------------------------------------------

def load(store):
    data = store.read(FILE, {})
    done = data.get("done") if isinstance(data, dict) else None
    try:
        per_day = max(1, min(5, int((data or {}).get("per_day") or PER_DAY)))
    except (TypeError, ValueError):
        per_day = PER_DAY
    return {**(data if isinstance(data, dict) else {}), "done": done if isinstance(done, dict) else {}, "shuffle": int((data or {}).get("shuffle") or 0),
            "shuffle_day": (data or {}).get("shuffle_day"), "per_day": per_day}


def mark(store, pid, done=True):
    if not re.fullmatch(r"[a-z]+-[0-9a-f]{10}", str(pid)):
        raise ValueError("Unbekannter Post.")
    with store.LOCK:
        data = load(store)
        if done:
            data["done"][pid] = store.now().isoformat(timespec="seconds")
        else:
            data["done"].pop(pid, None)
        # nur die letzten 200 merken
        data["done"] = dict(sorted(data["done"].items(), key=lambda x: x[1])[-200:])
        store.write(FILE, data)


def reshuffle(store):
    with store.LOCK:
        data = load(store)
        today = store.now().date().isoformat()
        data["shuffle"] = (data["shuffle"] + 1) if data.get("shuffle_day") == today else 1
        data["shuffle_day"] = today
        store.write(FILE, data)


def post_times(per_day, short_hours=()):
    """Uhrzeiten für die Posts. Fällt eine auf einen Shorts-Termin, rückt sie eine Stunde weiter."""
    taken, out = set(int(h) for h in short_hours or ()), []
    for base in TIMES[max(1, min(5, int(per_day)))]:
        # nächste freie Stunde in den 2 Stunden danach; sendet der Kanal jede Stunde, bleibt die Uhrzeit
        h = next((x for x in (base, base + 1, base + 2) if x not in taken and x not in out and x <= 22), base)
        out.append(h)
    return sorted(set(out)) if len(set(out)) == len(out) else TIMES[max(1, min(5, int(per_day)))]


def day_plan(posts, per_day, short_hours=()):
    """Wählt per_day Posts für heute, gemischt (Bild, Umfrage, Beitrag), und gibt jedem eine Uhrzeit."""
    per_day = max(1, min(5, int(per_day)))
    pick, left = [], list(posts)
    while left and len(pick) < per_day:
        for kind in ("bild", "umfrage", "text"):
            p = next((x for x in left if x["type"] == kind), None)
            if p and len(pick) < per_day:
                pick.append(p)
                left.remove(p)
        if not any(x["type"] in ("bild", "umfrage", "text") for x in left):
            break
    times = post_times(per_day, short_hours)
    pick.sort(key=lambda p: posts.index(p))
    for p, hour in zip(pick, times):
        p["hour"] = hour
    return pick + left


def set_per_day(store, n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        raise ValueError("Bitte eine Zahl von 1 bis 5.")
    if not 1 <= n <= 5:
        raise ValueError("Bitte eine Zahl von 1 bis 5.")
    with store.LOCK:
        data = load(store)
        data["per_day"] = n
        store.write(FILE, data)


def overview(store, posted, planned, channel, hours, firma=False):
    data = load(store)
    now = store.now()
    shuffle = data["shuffle"] if data.get("shuffle_day") == now.date().isoformat() else 0
    # Der Plan eines Tages bleibt fest, auch wenn inzwischen ein Short hochgeladen wurde.
    key = f"{now.date().isoformat()}|{shuffle}|{data['per_day']}|{','.join(map(str, hours))}|{int(bool(firma))}"
    raw = store.read(FILE, {}) or {}
    if raw.get("plan_key") == key and isinstance(raw.get("plan"), list):
        posts = raw["plan"]
    else:
        posts = day_plan(suggestions(posted, planned, channel, hours, now.replace(tzinfo=None), shuffle, firma),
                         data["per_day"], hours)
        with store.LOCK:
            raw = store.read(FILE, {}) or {}
            raw.update(plan_key=key, plan=posts)
            store.write(FILE, raw)
    for p in posts:
        p["done"] = data["done"].get(p["id"])
    week = sum(1 for v in data["done"].values() if v[:10] >= (now.date() - dt.timedelta(days=6)).isoformat())
    return {"posts": posts, "week": week, "per_day": data["per_day"], "times": post_times(data["per_day"], hours)}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "community-test"
    os.makedirs(out, exist_ok=True)
    demo_posted = [{"video_id": "abc123", "title": "Was passiert, wenn du tagelang nicht schläfst? 😵", "views": 1500,
                    "posted_at": dt.date.today().isoformat()}]
    demo_planned = [{"slug": "a", "title": "Was passiert, wenn sich die Erde plötzlich nicht mehr dreht? 🌍"},
                    {"slug": "b", "title": "Das Schiff, das niemand mehr fand 🚢"},
                    {"slug": "c", "title": "Warum gähnen wir, wenn andere gähnen? 🥱"}]
    for p in suggestions(demo_posted, demo_planned, {"title": "60 Sekunden Wissen", "subscribers": 57}, firma=True):
        print(p["label"], "|", p["title"], "|", p["text"].replace("\n", " / "), "|", p.get("options"))
        if p["type"] == "bild":
            render(p).save(os.path.join(out, p["id"] + ".png"))
    watermark().save(os.path.join(out, "wasserzeichen.png"))
