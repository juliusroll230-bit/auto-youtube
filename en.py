"""Englischer Kanal „EN“ (Phase H, seit 26.11.2026, Julius' Wunsch).

Ein eigener YouTube-Kanal (eigener Token `en_token`, Reiter Kanäle > Englisch) bekommt englische Fassungen
der deutschen Shorts, die schon gut liefen: mindestens 1.500 Aufrufe oder unter den besten 10 %.
Nicht übersetzt werden erzählte Ich-Geschichten (zu deutsch, „Mama packt zwei Brote ein“) und Kampagnen-Clips.

Die Skripte schreibt die tägliche Skript-Aufgabe (höchstens 2 am Tag) nach `seed-en/` (CLAUDE.md), mit Feld
"quelle" = slug des deutschen Shorts. Sie kommen wie `sleep/` mit dem nächtlichen Update auf den Server.

Die App rendert sie mit der englischen Piper-Stimme (en_GB, wie die Einschlaf-Geschichten) und englischen
Untertiteln, lädt 2 am Tag zu US/UK-Abendzeiten hoch (21 Uhr = 20 Uhr London / 15 Uhr New York,
1 Uhr = 19 Uhr New York / 16 Uhr Los Angeles) und lernt nur aus den eigenen EN-Uploads (eigener Lernmodus:
Soundeffekte, Musik, Übergang, Dranbleiben). Die Beschreibung sagt, dass die Stimme synthetisch ist.
Ohne verbundenen Kanal passiert nichts. Die EN-Uploads stehen in en.json, nicht in den Uploads des Hauptkanals,
damit sie dort weder den Lernmodus noch die 15-am-Tag-Grenze verfälschen.
"""
import datetime as dt
import glob
import json
import os

import learn
import store

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.environ.get("EN_SEED_DIR", os.path.join(HERE, "seed-en"))
FILE = "en.json"
HOURS = (21, 1)          # Berliner Zeit, siehe oben
WINDOW_H = 3             # ein Sendeplatz bleibt 3 Stunden offen (Rendern kann dauern)
PER_DAY_SCRIPTS = 2      # so viele Skripte schreibt die tägliche Aufgabe höchstens
MIN_VIEWS = 1500
TOP_SHARE = 0.10
VOICE = "english"
DISCLOSURE = "Voice: synthetic AI voice (text-to-speech). Animation: our own. Facts checked before upload."
FOOTER = "🔔 Subscribe for a new short every day."
SKIP_TYPES = ("Erzählte Geschichte",)
NO_VOICE = ("Die englische Stimme fehlt auf dem Server (Bau ohne Download). Shorts-Updater neu starten, "
            "dann lädt das neue Image sie mit. Bis dahin wird nichts Englisches gerendert.")   # Ich-Geschichten aus dem deutschen Alltag: nicht übersetzen


# --- Skripte ----------------------------------------------------------------------------------

def scripts():
    """Alle englischen Skripte aus seed-en/, nach Dateiname. Kaputte Dateien werden übersprungen."""
    out = []
    for p in sorted(glob.glob(os.path.join(DIR, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                spec = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(spec, dict) and spec.get("segments") and spec.get("slug"):
            out.append((os.path.basename(p), {**spec, "language": "en", "stil": spec.get("stil", "cartoon")}))
    return out


def used_sources():
    return {s.get("quelle") for _, s in scripts() if s.get("quelle")}


def load():
    d = store.read(FILE, {}) or {}
    return {"uploads": [], "done": [], "ready": None, "failed": [], "stats_at": None, **d}


def save(d):
    with store.LOCK:
        store.write(FILE, d)


def next_script(d=None):
    d = d or load()
    used = {u.get("name") for u in d["uploads"]} | set(d.get("failed") or [])
    if d.get("ready"):
        used.add(d["ready"].get("name"))
    return next(((n, s) for n, s in scripts() if n not in used), None)


def waiting(d=None):
    d = d or load()
    used = {u.get("name") for u in d["uploads"]} | set(d.get("failed") or [])
    return [n for n, _ in scripts() if n not in used]


# --- Sendeplan ---------------------------------------------------------------------------------

def hours(cfg):
    return [int(h) for h in (cfg.get("en_hours") or HOURS)]


def slot_times(cfg, now):
    """Sendeplätze rund um jetzt (gestern bis morgen), als Zeitpunkte."""
    out = []
    for day in (-1, 0, 1):
        base = (now + dt.timedelta(days=day)).replace(minute=0, second=0, microsecond=0)
        out += [base.replace(hour=h) for h in hours(cfg)]
    return sorted(out)


def due_slot(cfg, now=None, d=None):
    """Schlüssel „JJJJ-MM-TT-HH“ eines offenen Sendeplatzes (seit höchstens 3 Std.), sonst None."""
    now = now or store.now()
    d = d or load()
    for at in slot_times(cfg, now):
        key = at.strftime("%Y-%m-%d-%H")
        if at <= now < at + dt.timedelta(hours=WINDOW_H) and key not in d["done"]:
            return key
    return None


def next_slot(cfg, now=None):
    now = now or store.now()
    d = load()
    for at in slot_times(cfg, now):
        if at + dt.timedelta(hours=WINDOW_H) > now and at.strftime("%Y-%m-%d-%H") not in d["done"]:
            return at
    return None


def active(cfg):
    return bool(cfg.get("en_token")) and bool(cfg.get("en_on", True))


def wants_render(cfg, d=None):
    """Soll der EN-Kanal als Nächstes rendern? (Dann wartet der Vorrat des Hauptkanals kurz.)"""
    d = d or load()
    return active(cfg) and not d.get("ready") and next_script(d) is not None


def mark_done(slot):
    with store.LOCK:
        d = load()
        d["done"] = (d["done"] + [slot])[-60:]
        store.write(FILE, d)


# --- Eigener Lernmodus -------------------------------------------------------------------------

def posted(d=None):
    """EN-Uploads mit Aufrufen und Merkmalen (wie store.posted_items, nur für diesen Kanal)."""
    d = d or load()
    specs = {s["slug"]: s for _, s in scripts()}
    out = []
    for u in d["uploads"]:
        spec = specs.get(u.get("slug"))
        item = dict(u)
        if spec:
            item["features"] = learn.features(spec, u.get("look") or {})
        out.append(item)
    return out


def choose_look(spec, d=None):
    """Soundeffekte, Musik, Übergang und Dranbleiben: gelernt nur aus EN-Uploads (erst testen, dann Thompson)."""
    d = d or load()
    items = posted(d)
    fs = learn.feature_scores(items, store.now())
    n = len(d["uploads"]) + (1 if d.get("ready") else 0)
    return {"stimme": VOICE, "effekte": learn.choose(learn.EFFECTS, fs.get("effekte", {}), n),
            "musik": learn.choose_music(fs, n, spec), "uebergang": learn.choose_transition(fs, n),
            "halten": learn.choose_hold(fs, n), "aufbau": "normal", "tempo": "normal", "abo": "ohne",
            "hintergrund": "animation"}


LEARN_SHOWN = ("typ", "effekte", "musik", "uebergang", "halten", "welt")


def learn_rows(d=None):
    fs = learn.feature_scores(posted(d), store.now())
    rows = []
    for name in LEARN_SHOWN:
        vals = fs.get(name) or {}
        if not vals:
            continue
        best = max(vals.items(), key=lambda kv: (kv[1].get("mu", 0), kv[1]["score"]))
        rows.append({"label": learn.FEATURE_NAMES.get(name, name), "best": best[0], "videos": best[1]["videos"],
                     "values": len(vals)})
    return rows


# --- Quellen: welche deutschen Shorts eine englische Fassung bekommen ---------------------------

def sources(rated, find, used=(), top=10):
    """rated: [{title, views, slug?}] deutscher Shorts; find(v) -> deutsches Skript oder None.
    Mindestens 1.500 Aufrufe oder unter den besten 10 %, keine Ich-Geschichten, keine Clips, noch nicht übersetzt."""
    pool = []
    for v in rated:
        spec = find(v)
        if not spec or v.get("kind") == "clip" or v.get("channel") == "clips" or v.get("lang") or v.get("abgabe"):
            continue
        if spec.get("format") == "firma" or spec.get("laenge") == "lang" or learn.video_type(spec) in SKIP_TYPES:
            continue
        pool.append((int(v.get("views") or 0), v, spec))
    if not pool:
        return []
    views = sorted(x[0] for x in pool)
    cut = views[min(len(views) - 1, int(len(views) * (1 - TOP_SHARE)))]
    out = []
    for n, v, spec in sorted(pool, key=lambda x: -x[0]):
        slug = spec.get("slug")
        if slug in used or n <= 0 or (n < MIN_VIEWS and n < cut):
            continue
        out.append({"slug": slug, "title": v.get("title") or spec.get("title"), "views": n, "typ": learn.video_type(spec),
                    "skript": spec.get("_file") or f"seed/{slug}.json"})
    return out[:top]


# --- Upload -----------------------------------------------------------------------------------

def upload_spec(spec):
    """Titel, Beschreibung (mit Hinweis auf die synthetische Stimme), Sprache Englisch."""
    desc = (spec.get("description") or "").rstrip()
    return {**spec, "language": "en", "description": (desc + "\n\n" if desc else "") + DISCLOSURE, "footer": FOOTER}


def record(name, spec, video_id, slot, look, duration, thumb=None, now=None):
    now = now or store.now()
    with store.LOCK:
        d = load()
        d["uploads"].append({"name": name, "slug": spec["slug"], "quelle": spec.get("quelle"), "video_id": video_id,
                             "title": spec["title"], "posted_at": now.isoformat(timespec="seconds"), "slot": slot,
                             "look": look, "duration": duration, "thumb": thumb, "channel": "en"})
        if slot:
            d["done"] = (d["done"] + [slot])[-60:]
        d["ready"] = None
        store.write(FILE, d)


def set_stats(videos):
    """videos: {video_id: {views, likes, ...}} von yt.video_stats mit dem EN-Token."""
    with store.LOCK:
        d = load()
        for u in d["uploads"]:
            s = videos.get(u["video_id"])
            if s:
                u.update({k: s[k] for k in ("views", "likes", "comments") if k in s})
        d["stats_at"] = store.now().isoformat(timespec="seconds")
        store.write(FILE, d)


def overview(cfg, main_posted=None):
    """Für den Reiter Kanäle > Englisch."""
    d = load()
    nxt = next_slot(cfg) if active(cfg) else None
    src = []
    if main_posted is not None:
        try:
            index = store.spec_index()
            src = sources(main_posted, lambda v: store.find_spec(v.get("slug"), index), used_sources(), top=6)
        except Exception:  # noqa: BLE001
            src = []
    ups = sorted(d["uploads"], key=lambda u: u.get("posted_at") or "", reverse=True)
    return {
        "connected": bool(cfg.get("en_token")), "expired": bool(cfg.get("en_expired")) and not cfg.get("en_token"),
        "on": bool(cfg.get("en_on", True)), "channel": store.read("enchannel.json", None) if cfg.get("en_token") else None,
        "hours": hours(cfg), "next": nxt.isoformat(timespec="minutes") if nxt else None,
        "ready": (d.get("ready") or {}).get("title"), "waiting": len(waiting(d)),
        "uploads": [{k: u.get(k) for k in ("title", "video_id", "posted_at", "views", "quelle")} for u in ups[:10]],
        "total": len(d["uploads"]), "views": sum(int(u.get("views") or 0) for u in d["uploads"]),
        "learn": learn_rows(d), "sources": src, "error": d.get("error"),
    }
