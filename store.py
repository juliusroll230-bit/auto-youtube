"""Alles, was auf dem Server gespeichert wird, liegt in DATA_DIR (im Container: /data).

  config.json    Zugang zu YouTube, Sendezeiten, Sichtbarkeit
  state.json     erledigte Sendeplätze, Uploads, Aktivitätsprotokoll
  stats.json     Aufrufe/Likes je Video
  channel.json   Name, Bild und Abonnenten des Kanals
  history.json   Verlauf von Aufrufen und Abonnenten (für das Diagramm auf der Website)
  analytics.json Zuschauerbindung je Video (wann Zuschauer abschalten), von YouTube Analytics
  queue/         Skripte, die noch gepostet werden
  posted/        Skripte, die schon online sind
  thumbs/        Vorschaubilder
"""
import datetime as dt
import glob
import json
import os
import re
import shutil
import threading
from zoneinfo import ZoneInfo

import learn

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA_DIR", os.path.join(HERE, "data"))
SEED = os.path.join(HERE, "seed")
TZ = ZoneInfo(os.environ.get("TZ_NAME", "Europe/Berlin"))
EARLY_MIN = 25   # so früh vor dem Sendeplatz wird schon gerendert und hochgeladen
LATE_MIN = 100   # bis so spät danach wird ein verpasster Platz nachgeholt

LOCK = threading.RLock()
DEFAULT_CONFIG = {"client_id": "", "client_secret": "", "refresh_token": "",
                  "post_hours": [8, 11, 13, 16, 18, 20], "privacy": "public", "expired": False,
                  # zweiter Zugang nur für Zuschauer-Daten (siehe yt.py, Abschnitt YouTube Analytics)
                  "analytics_client_id": "", "analytics_client_secret": "", "analytics_token": "",
                  # Einstellungen der Agenten (agents.py) und Freigabe-Pflicht für neue Videos
                  "agents": {}, "approval": False}
FILE_RE = re.compile(r"\d{4}-[a-z0-9-]+\.json")
PAUSE_S = 0.18     # wie make_short.PAUSE; für geschätzte Satzanfänge älterer Videos
WORDS_PER_S = 2.8


def path(*parts):
    return os.path.join(DATA, *parts)


def read(name, default):
    try:
        with open(path(name), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write(name, data):
    tmp = path(name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path(name))


def now():
    return dt.datetime.now(TZ)


def init():
    for d in ("queue", "posted", "thumbs", "out", "rejected"):
        os.makedirs(path(d), exist_ok=True)
    with LOCK:
        cfg = {**DEFAULT_CONFIG, **read("config.json", {})}
        # Alte Standardzeiten (3 pro Tag) einmalig auf 6 pro Tag umstellen, eigene Zeiten bleiben
        if not cfg.get("hours_v2"):
            if cfg["post_hours"] == [12, 17, 20]:
                cfg["post_hours"] = DEFAULT_CONFIG["post_hours"]
            cfg["hours_v2"] = True
        write("config.json", cfg)
        try:
            os.chmod(path("config.json"), 0o600)
        except OSError:
            pass
        add_scripts({os.path.basename(f): open(f, encoding="utf-8").read()
                     for f in sorted(glob.glob(os.path.join(SEED, "*.json")))})


def config():
    return {**DEFAULT_CONFIG, **read("config.json", {})}


def save_config(**changes):
    with LOCK:
        cfg = config()
        cfg.update(changes)
        write("config.json", cfg)
        return cfg


def state():
    return {"done_slots": [], "uploads": [], "events": [], "known": [], "approved": [], "agent_runs": {},
            **read("state.json", {})}


def agent_done(agent, error=None):
    """Merkt sich, wann ein Agent zuletzt gearbeitet hat (und wie oft erfolgreich)."""
    with LOCK:
        st = state()
        run = st["agent_runs"].get(agent, {"count": 0})
        run.update(at=now().isoformat(timespec="seconds"), error=str(error)[:200] if error else None)
        if not error:
            run["count"] = run.get("count", 0) + 1
        st["agent_runs"][agent] = run
        write("state.json", st)


# --- Freigaben ---------------------------------------------------------------

def _check_name(name):
    if not FILE_RE.fullmatch(name or ""):
        raise ValueError("Unbekanntes Skript.")


def approve(name):
    _check_name(name)
    with LOCK:
        if not os.path.exists(path("queue", name)):
            raise ValueError("Das Skript ist nicht mehr in der Warteschlange.")
        st = state()
        st["approved"] = sorted(set(st["approved"]) | {name})
        write("state.json", st)


def reject(name):
    """Nimmt ein Skript aus der Warteschlange (es landet in rejected/ und kann zurückgeholt werden)."""
    _check_name(name)
    with LOCK:
        if not os.path.exists(path("queue", name)):
            raise ValueError("Das Skript ist nicht mehr in der Warteschlange.")
        shutil.move(path("queue", name), path("rejected", name))
        st = state()
        st["approved"] = [a for a in st["approved"] if a != name]
        write("state.json", st)


def restore(name):
    _check_name(name)
    with LOCK:
        if not os.path.exists(path("rejected", name)):
            raise ValueError("Das Skript wurde nicht gefunden.")
        shutil.move(path("rejected", name), path("queue", name))


def log(level, text):
    with LOCK:
        st = state()
        st["events"] = (st["events"] + [{"at": now().isoformat(timespec="seconds"), "level": level, "text": text}])[-80:]
        write("state.json", st)
    print(f"[{level}] {text}", flush=True)


def add_scripts(files):
    """Legt neue Skripte in die Warteschlange. Schon bekannte Dateien werden übersprungen."""
    added = 0
    with LOCK:
        st = state()
        known = set(st["known"])
        for name, text in files.items():
            if name in known or not name.endswith(".json"):
                continue
            spec = json.loads(text)
            if not spec.get("segments"):
                continue
            with open(path("queue", name), "w", encoding="utf-8") as f:
                f.write(text)
            known.add(name)
            added += 1
        st["known"] = sorted(known)
        write("state.json", st)
    return added


def queue_files():
    return sorted(glob.glob(path("queue", "*.json")))


def load_spec(file):
    with open(file, encoding="utf-8") as f:
        return json.load(f)


def find_spec(slug):
    for f in queue_files() + glob.glob(path("posted", "*.json")):
        if os.path.basename(f)[5:-5] == slug or load_spec(f).get("slug") == slug:
            return load_spec(f)
    return None


def due_slot(at=None):
    at = at or now()
    st, hours = state(), config()["post_hours"]
    for h in hours:
        slot = at.replace(hour=int(h), minute=0, second=0, microsecond=0)
        key = slot.strftime("%Y-%m-%d-%H")
        if key in st["done_slots"]:
            continue
        if slot - dt.timedelta(minutes=EARLY_MIN) <= at <= slot + dt.timedelta(minutes=LATE_MIN):
            return key
    return None


def sentence_marks(spec):
    """Geschätzte Satzanfänge als Anteil der Videolänge (0..1), wenn die echten Zeiten fehlen."""
    t, starts = 0.0, []
    for seg in spec.get("segments", []):
        starts.append(t)
        t += len(seg["text"].split()) / WORDS_PER_S + PAUSE_S
    return [round(x / t, 4) for x in starts] if t else []


def mark_posted(file, slot, spec, video_id, marks=None, duration=None, look=None):
    with LOCK:
        shutil.move(file, path("posted", os.path.basename(file)))
        st = state()
        if slot:
            st["done_slots"] = (st["done_slots"] + [slot])[-90:]
        st["uploads"].append({"slot": slot, "slug": spec["slug"], "video_id": video_id, "title": spec["title"],
                              "posted_at": now().isoformat(timespec="seconds"),
                              "marks": marks, "duration": duration, "look": look})
        write("state.json", st)


def card(spec):
    words = sum(len(s["text"].split()) for s in spec["segments"])
    return {
        "slug": spec["slug"], "title": spec["title"], "niche": spec["niche"],
        "style": spec.get("style", "gradient"), "colors": spec.get("colors", []),
        "car_color": spec.get("car_color", ""), "accent": spec.get("accent", ""),
        "emoji": spec["segments"][0].get("emoji", ""), "hook": spec["segments"][0]["text"].replace("*", ""),
        "seconds": round(words / 2.5 + 0.3 * len(spec["segments"])),
    }


def posted_items():
    """Alle Uploads mit Thema und den letzten Zahlen von YouTube, älteste zuerst."""
    stats = read("stats.json", {"videos": {}, "updated_at": None})
    ana = read("analytics.json", {}).get("videos", {})
    posted = []
    for u in state()["uploads"]:
        spec = find_spec(u["slug"])
        base = card(spec) if spec else {"slug": u["slug"], "title": u["title"]}
        item = {**base, **u, **stats["videos"].get(u["video_id"], {}), **ana.get(u["video_id"], {})}
        if spec:  # Satztexte für die Abschalt-Kurve auf der Website
            item["sentences"] = [seg["text"].replace("*", "") for seg in spec.get("segments", [])]
        if spec:  # Merkmale für "Was am besten funktioniert"
            item["features"] = learn.features(spec, u.get("look") or learn.default_look(spec))
        if not item.get("marks") and spec:
            item["marks"] = sentence_marks(spec)
            item["marks_estimated"] = True
        posted.append(item)
    return posted


def record_history(views, subs):
    """Merkt sich Aufrufe und Abonnenten für das Verlaufs-Diagramm, höchstens ein Punkt pro Stunde."""
    with LOCK:
        hist = read("history.json", [])
        point = {"at": now().isoformat(timespec="minutes"), "views": views, "subs": subs}
        if hist and hist[-1]["at"][:13] == point["at"][:13]:
            hist[-1] = point
        else:
            hist.append(point)
        write("history.json", hist[-24 * 180:])


def planned_queue(posted=None, ready_only=False):
    """Warteschlange als (datei, skript) in der Reihenfolge, die der Lernmodus vorgibt.

    ready_only: mit Freigabe-Pflicht nur freigegebene Skripte (für den Upload).
    """
    import agents

    posted = posted if posted is not None else posted_items()
    cfg = config()
    queue = [(f, load_spec(f)) for f in queue_files()]
    if ready_only and cfg["approval"]:
        ok = set(state()["approved"])
        queue = [q for q in queue if os.path.basename(q[0]) in ok]
    planer = agents.settings(cfg)["planer"]
    if not planer["on"]:
        return queue  # Lernmodus aus: einfach in Dateireihenfolge
    history = [p["niche"] for p in posted if p.get("niche")]
    return learn.plan(queue, history, learn.niche_scores(posted, now()), planer["explore_every"])


def next_look(posted=None):
    """Untertitel-Stil und Übergang für das nächste Video, nach dem was bisher am besten lief."""
    posted = posted if posted is not None else posted_items()
    return learn.choose_look(learn.feature_scores(posted, now()), len(posted))


def next_slot(hours, at=None):
    at = at or now()
    for day in range(2):
        for h in sorted(hours):
            slot = (at + dt.timedelta(days=day)).replace(hour=int(h), minute=0, second=0, microsecond=0)
            if slot > at:
                return slot
    return None


def dashboard(extra=None, working=(), repo=True):
    import agents

    cfg = config()
    st = state()
    stats = read("stats.json", {"videos": {}, "updated_at": None})
    posted = posted_items()
    planned = planned_queue(posted)
    approved = set(st["approved"])
    scores = learn.niche_scores(posted, now())
    ag = agents.settings(cfg)
    queue = [{**card(spec), "file": os.path.basename(f), "approved": os.path.basename(f) in approved}
             for f, spec in planned]
    rejected = []
    for f in sorted(glob.glob(path("rejected", "*.json"))):
        try:
            rejected.append({**card(load_spec(f)), "file": os.path.basename(f)})
        except (OSError, ValueError, KeyError):
            continue
    return {
        "source": "server",
        "updated_at": now().isoformat(timespec="seconds"),
        "stats_updated_at": stats.get("updated_at"),
        "slots": cfg["post_hours"],
        "privacy": cfg["privacy"],
        "has_client": bool(cfg["client_id"] and cfg["client_secret"]),
        "connected": bool(cfg["refresh_token"]),
        "expired": bool(cfg["expired"]) and not cfg["refresh_token"],
        "channel": read("channel.json", None),
        "queue": queue,
        "approval": bool(cfg["approval"]),
        "rejected": rejected,
        "agents": agents.overview(cfg, st["agent_runs"], {
            "connected": bool(cfg["refresh_token"]), "analytics": bool(cfg["analytics_token"]),
            "working": set(working), "queue": len(queue), "posted": len(posted), "favorite": learn.favorite(scores),
            "next_slot": next_slot(cfg["post_hours"]), "now": now(), "repo": repo,
            "branding_at": st.get("branding_at")}),
        "posted": posted,
        "branding_at": st.get("branding_at"),
        "learning": learn.summary(scores, ag["planer"]["explore_every"]) if ag["planer"]["on"]
        else {**learn.summary(scores, ag["planer"]["explore_every"]), "favorite": None, "off": True},
        "looks": learn.feature_summary(learn.feature_scores(posted, now())),
        "history": read("history.json", []),
        "analytics": {
            "connected": bool(cfg["analytics_token"]),
            "has_client": bool(cfg["analytics_client_id"] and cfg["analytics_client_secret"]),
            "updated_at": read("analytics.json", {}).get("updated_at"),
            "error": read("analytics.json", {}).get("error"),
        },
        "events": list(reversed(st["events"][-30:])),
        **(extra or {}),
    }
