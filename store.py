"""Alles, was auf dem Server gespeichert wird, liegt in DATA_DIR (im Container: /data).

  config.json    Zugang zu YouTube, Sendezeiten, Sichtbarkeit
  state.json     erledigte Sendeplätze, Uploads, Aktivitätsprotokoll
  stats.json     Aufrufe/Likes je Video
  channel.json   Name, Bild und Abonnenten des Kanals
  history.json   Verlauf von Aufrufen und Abonnenten (für das Diagramm auf der Website)
  analytics.json Zuschauerbindung je Video (wann Zuschauer abschalten), von YouTube Analytics
  inbox/         Eingangsordner: Videos hier ablegen, der Video-Clipper macht Clips daraus (clips.py)
  campaigns/     je Eingangsvideo eine Kampagne mit Original, Mitschrift und fertigen Clips
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

import hookcheck
import learn

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA_DIR", os.path.join(HERE, "data"))
SEED = os.path.join(HERE, "seed")
TZ = ZoneInfo(os.environ.get("TZ_NAME", "Europe/Berlin"))
EARLY_MIN = 25   # so früh vor dem Sendeplatz wird schon gerendert und hochgeladen
LATE_MIN = 100   # bis so spät danach wird ein verpasster Platz nachgeholt

LOCK = threading.RLock()
DEFAULT_CONFIG = {"client_id": "", "client_secret": "", "refresh_token": "",
                  # Sendezeiten (volle Stunden, deutsche Zeit): Mo bis Fr und Sa/So getrennt.
                  # 15.11.: nach YouTube Studio "Wann deine Zuschauer auf YouTube sind" (28 Tage):
                  # werktags ab 15 Uhr viel los, Spitze 16 bis 21 Uhr; Sa/So schon ab ca. 10 Uhr stark.
                  # 16.11.: Julius will 15 Shorts am Tag (10 Strichmännchen, 5 Blockwelt): jede volle Stunde 8 bis 22 Uhr.
                  "post_hours": list(range(8, 23)), "post_hours_weekend": list(range(8, 23)),
                  # davon so viele Blockwelt (3D), der Rest Strichmännchen. 0 = Lernmodus wählt frei.
                  "block_per_day": 5,
                  "privacy": "public", "expired": False,
                  # zweiter Zugang nur für Zuschauer-Daten (siehe yt.py, Abschnitt YouTube Analytics)
                  "analytics_client_id": "", "analytics_client_secret": "", "analytics_token": "",
                  # welche Berechtigungen der zweite Zugang hat (mit youtube.force-ssl darf die App auf Kommentare antworten)
                  "analytics_scopes": "",
                  # Pixabay- oder Pexels-Schlüssel für echte Videoclips als Hintergrund (stock.py), leer = nur Animation
                  "stock_key": "",
                  # Fish Audio (fishtts.py): API-Schlüssel und Stimmen-IDs, leer = eingebaute Piper-Stimme
                  "fish_key": "", "fish_voice": "", "fish_voice_dark": "", "fish_voice_warm": "",
                  # Einstellungen der Agenten (agents.py) und Freigabe-Pflicht für neue Videos
                  "agents": {}, "approval": False,
                  # Schlüssel für den Video-Webhook (POST /webhook/video), wird beim ersten Start erzeugt
                  "webhook_token": "",
                  # zweiter YouTube-Kanal nur für Clips (leer = Clips laufen auf dem Hauptkanal mit)
                  "clip_token": "", "clip_expired": False,
                  # Profile auf TikTok und Instagram (nur zum Verlinken, dort wird von Hand gepostet)
                  "socials": {"tiktok": "", "instagram": ""},
                  # Firmen-Spiel (firma.py): eine Folge pro Tag zusätzlich (vier Firmen reihum), ab dieser Uhrzeit, None = aus
                  "firma_hour": 20}
FILE_RE = re.compile(r"\d{4}-[a-z0-9-]+\.json")
LISTENERS = []     # bekommen jedes neue Ereignis aus log() (server.py: Live-Animation in der Zentrale)
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
    for d in ("queue", "posted", "thumbs", "out", "rejected", "inbox", "campaigns", "share", "ready"):
        os.makedirs(path(d), exist_ok=True)
    with LOCK:
        raw = read("config.json", {})
        cfg = {**DEFAULT_CONFIG, **raw}
        # Alte Standardzeiten (3 pro Tag) einmalig auf 6 pro Tag umstellen, eigene Zeiten bleiben
        if not cfg.get("hours_v2"):
            if cfg["post_hours"] == [12, 17, 20]:
                cfg["post_hours"] = DEFAULT_CONFIG["post_hours"]
            cfg["hours_v2"] = True
        # Alte Standardzeiten (6 oder 7 pro Tag) einmalig auf die neuen 10 Zeiten umstellen, eigene Zeiten bleiben
        if not cfg.get("hours_v4"):
            if cfg["post_hours"] in ([8, 11, 13, 16, 18, 20], [7, 11, 13, 15, 17, 19, 21]):
                cfg["post_hours"] = DEFAULT_CONFIG["post_hours"]
            cfg["hours_v4"] = True
        # 13.11.: weniger, dafür bessere Videos (5 statt 10 pro Tag), eigene Zeiten bleiben
        if not cfg.get("hours_v5"):
            if cfg["post_hours"] == [7, 9, 11, 13, 14, 15, 17, 18, 19, 21]:
                cfg["post_hours"] = DEFAULT_CONFIG["post_hours"]
            cfg["hours_v5"] = True
        # 15.11.: Zeiten nach Zuschauer-Aktivität, am Wochenende eigene Zeiten. Eigene Zeiten bleiben,
        # dann gelten sie auch am Wochenende (wie bisher).
        if not cfg.get("hours_v6"):
            if cfg["post_hours"] in ([8, 11, 13, 16, 18], DEFAULT_CONFIG["post_hours"]):
                cfg["post_hours"] = DEFAULT_CONFIG["post_hours"]
                cfg["post_hours_weekend"] = DEFAULT_CONFIG["post_hours_weekend"]
            elif "post_hours" in raw and "post_hours_weekend" not in raw:
                cfg["post_hours_weekend"] = list(cfg["post_hours"])
            cfg["hours_v6"] = True
        # 16.11.: 15 statt 5 Shorts am Tag. Alte Standardzeiten werden umgestellt, eigene Zeiten bleiben.
        if not cfg.get("hours_v7"):
            if cfg["post_hours"] == [12, 15, 16, 17, 18] and cfg.get("post_hours_weekend") in (None, [11, 13, 15, 17, 18]):
                cfg["post_hours"] = DEFAULT_CONFIG["post_hours"]
                cfg["post_hours_weekend"] = DEFAULT_CONFIG["post_hours_weekend"]
            cfg["hours_v7"] = True
        # 19.11.: Julius will sicher 15 Shorts am Tag (jede volle Stunde 8 bis 22 Uhr). Gespeicherte Zeiten mit
        # weniger Plätzen (z. B. 10) hätten den neuen Standard überdeckt, darum einmalig für alle Tage umstellen.
        if not cfg.get("hours_v8"):
            for key in ("post_hours", "post_hours_weekend"):
                if len(cfg.get(key) or []) < len(DEFAULT_CONFIG[key]):
                    cfg[key] = list(DEFAULT_CONFIG[key])
            cfg["hours_v8"] = True
        if not cfg.get("webhook_token"):
            import secrets
            cfg["webhook_token"] = secrets.token_urlsafe(18)
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


def log(level, text, agent=None, **extra):
    """Ereignis für Live-Feed und Aktivität. agent: welcher Agent es ausgelöst hat (für die Animation),
    extra: z. B. kind ("posted", "input", "clips" …) und source ("youtube", "ordner" …)."""
    entry = {"at": now().isoformat(timespec="seconds"), "level": level, "text": text}
    if agent:
        entry["agent"] = agent
    for key in ("kind", "source"):
        if extra.get(key):
            entry[key] = extra[key]
    with LOCK:
        st = state()
        st["events"] = (st["events"] + [entry])[-80:]
        write("state.json", st)
    print(f"[{level}] {text}", flush=True)
    for fn in LISTENERS:
        try:
            fn({**extra, **entry})
        except Exception as e:  # die Website darf das Protokoll nie aufhalten
            print(f"Live-Ereignis fehlgeschlagen: {e}", flush=True)


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
            spec, changed = hookcheck.clean(spec)  # Humanizer: Gedankenstriche und leere Floskeln raus
            if changed:
                text = json.dumps(spec, ensure_ascii=False, indent=2)
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


def is_weekend(day):
    return day.weekday() >= 5


def hours_for(cfg, day):
    """Sendezeiten (volle Stunden) für diesen Tag: Sa/So eigene Zeiten, sonst die normalen."""
    if is_weekend(day) and cfg.get("post_hours_weekend"):
        return cfg["post_hours_weekend"]
    return cfg["post_hours"]


def due_slot(at=None, done="done_slots"):
    """Der Sendeplatz, der gerade dran ist. done="clip_slots" für den eigenen Clip-Kanal."""
    at = at or now()
    st, hours = state(), hours_for(config(), at)
    for h in hours:
        slot = at.replace(hour=int(h), minute=0, second=0, microsecond=0)
        key = slot.strftime("%Y-%m-%d-%H")
        if key in st.get(done, []):
            continue
        if slot - dt.timedelta(minutes=EARLY_MIN) <= at <= slot + dt.timedelta(minutes=LATE_MIN):
            return key
    return None


CLIPI_WINDOW = (7 * 60, 23 * 60)  # Clipi postet zwischen 7 und 23 Uhr


def clipi_times(per_day):
    """Sendezeiten des Clip-Kanals (Minuten nach Mitternacht), gleichmäßig zwischen 7 und 23 Uhr, auf 5 Min gerundet."""
    per_day = max(1, int(per_day))
    a, b = CLIPI_WINDOW
    if per_day == 1:
        return [13 * 60]
    step = (b - a) / (per_day - 1)
    grid = 5 if step >= 10 else 1  # bei sehr vielen Posts pro Tag minutengenau, sonst fallen Zeiten zusammen
    return sorted({int(round((a + i * step) / grid) * grid) for i in range(per_day)})


CLIPI_GAP_MIN = 10   # mindestens so viele Minuten zwischen zwei Clipi-Posts, auch beim Nachholen


def clipi_gap(per_day):
    """Mindestabstand zwischen zwei Clipi-Posts: 10 Minuten, bei sehr vielen Posts pro Tag etwas weniger."""
    a, b = CLIPI_WINDOW
    return max(3, min(CLIPI_GAP_MIN, int((b - a) / max(1, per_day) * 0.8)))


def _clipi_open(per_day, at, st):
    """Heutige Clipi-Plätze (datetime, Schlüssel), die noch frei sind. Plätze vor dem Ende einer Pause zählen nicht."""
    pause = st.get("clipi_pause") or ""
    start = at.replace(hour=0, minute=0, second=0, microsecond=0)
    if pause and pause[:10] == at.date().isoformat():
        start = max(start, dt.datetime.fromisoformat(pause))
    done = set(st.get("clipi_slots", []))
    out = []
    for m in clipi_times(per_day):
        slot = at.replace(hour=m // 60, minute=m % 60, second=0, microsecond=0)
        key = slot.strftime("%Y-%m-%d-%H-%M")
        if slot >= start and key not in done:
            out.append((slot, key))
    return out


def due_clipi(per_day, at=None):
    """Der Clipi-Sendeplatz, der jetzt gepostet werden soll (Schlüssel JJJJ-MM-TT-HH-MM), sonst None.

    Verpasste Plätze von heute werden nachgeholt (z. B. wenn der Server gerade ein Video gebaut hat),
    aber höchstens einer alle CLIPI_GAP_MIN Minuten, damit nicht alles auf einmal hochgeht."""
    at = at or now()
    st = state()
    if (st.get("clipi_pause") or "") > at.isoformat(timespec="seconds"):
        return None
    last = st.get("clipi_last") or ""
    if last and dt.datetime.fromisoformat(last) > at - dt.timedelta(minutes=clipi_gap(per_day)):
        return None
    for slot, key in _clipi_open(per_day, at, st):
        if slot - dt.timedelta(minutes=5) <= at:
            return key
    return None


def clipi_posted(at=None):
    """Merkt sich die Zeit des letzten Clipi-Posts (für den Abstand beim Nachholen)."""
    with LOCK:
        st = state()
        st["clipi_last"] = (at or now()).isoformat(timespec="seconds")
        write("state.json", st)


def next_clipi(per_day, at=None):
    """Nächste Clipi-Sendezeit als ISO-Text (für die Anzeige)."""
    at = at or now()
    st = state()
    pause = st.get("clipi_pause") or ""
    if pause > at.isoformat(timespec="seconds"):
        at = dt.datetime.fromisoformat(pause)
    soon = at
    last = st.get("clipi_last") or ""
    if last:
        soon = max(soon, dt.datetime.fromisoformat(last) + dt.timedelta(minutes=clipi_gap(per_day)))
    open_today = _clipi_open(per_day, at, st)
    if open_today:
        return max(open_today[0][0], soon).replace(second=0, microsecond=0).isoformat(timespec="minutes")
    tomorrow = (at + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    m = clipi_times(per_day)[0]
    return tomorrow.replace(hour=m // 60, minute=m % 60).isoformat(timespec="minutes")


PROJECT_DAILY = 100   # YouTube-Upload-Topf pro Google-Projekt und Tag, Hauptkanal und Clipi teilen ihn


def clipi_room(cfg, st, at=None):
    """Wie viele Clipi-Uploads heute noch Platz haben, ohne dem Hauptkanal den Tagestopf wegzunehmen.

    Der Hauptkanal (KI-Shorts, langes Video, Firmen-Folge) behält seine Plätze für heute reserviert."""
    at = at or now()
    today = at.date().isoformat()
    ups = [u for u in st.get("uploads", []) if (u.get("posted_at") or "")[:10] == today]
    clip_done = sum(1 for u in ups if u.get("channel") == "clips")
    main_done = len(ups) - clip_done
    main_total = len(hours_for(cfg, at) or []) + 2  # + langes Video + Firmen-Folge
    main_left = max(0, main_total - main_done)
    return max(0, PROJECT_DAILY - main_done - main_left - clip_done)


def clipi_overview(cfg, st):
    """Clipi-Warteschlange für die Website: wartende Videos, Tageslimit, nächste Sendezeit, heute gepostet."""
    import agents
    import clips
    per = agents.settings(cfg)["publisher"]["clipi_per_day"]
    today = now().date().isoformat()
    info = clips.queue_info(per)
    done = sum(1 for u in st["uploads"] if u.get("channel") == "clips" and (u.get("posted_at") or "")[:10] == today)
    pause = st.get("clipi_pause") or ""
    why = None  # Warum gerade nichts gepostet wird (für die Website)
    if not cfg["clip_token"]:
        why = "Der Clip-Kanal ist nicht verbunden. Verbinde ihn im Reiter Kanäle."
    elif not agents.settings(cfg)["publisher"]["on"]:
        why = "Der Publisher ist ausgeschaltet. Schalte ihn bei den Agenten wieder ein."
    elif pause > now().isoformat(timespec="seconds"):
        why = "YouTube nimmt auf dem Clip-Kanal heute nichts mehr an (Tageslimit). Weiter am %s um %s Uhr." % (
            pause[8:10] + "." + pause[5:7] + ".", pause[11:16])
    elif clipi_room(cfg, st) <= 0:
        why = "Heute ist der YouTube-Tagestopf fast voll (100 Uploads für beide Kanäle). Der Rest ist für den Hauptkanal reserviert. Morgen geht es weiter."
    elif done >= per:
        why = "Heute sind schon %d von %d Clips online. Morgen ab 7 Uhr geht es weiter." % (done, per)
    return {**info, "per_day": per, "why": why, "times": ["%02d:%02d" % (m // 60, m % 60) for m in clipi_times(per)],
            "next": next_clipi(per) if cfg["clip_token"] else None, "pause": st.get("clipi_pause"),
            "learn": clips.learn_summary(),
            "today": done}


def pause_clipi(until):
    with LOCK:
        st = state()
        st["clipi_pause"] = until.isoformat(timespec="seconds")
        write("state.json", st)


def sentence_marks(spec):
    """Geschätzte Satzanfänge als Anteil der Videolänge (0..1), wenn die echten Zeiten fehlen."""
    t, starts = 0.0, []
    for seg in spec.get("segments", []):
        starts.append(t)
        t += len(seg["text"].split()) / WORDS_PER_S + PAUSE_S
    return [round(x / t, 4) for x in starts] if t else []


def mark_posted(file, slot, spec, video_id, marks=None, duration=None, look=None, done="done_slots", thumb=None):
    with LOCK:
        shutil.move(file, path("posted", os.path.basename(file)))
        st = state()
        if slot:
            st[done] = (st.get(done, []) + [slot])[-90:]
        rec = {"slot": slot, "slug": spec["slug"], "video_id": video_id, "title": spec["title"],
               "posted_at": now().isoformat(timespec="seconds"),
               "marks": marks, "duration": duration, "look": look}
        if is_long(spec):
            rec["lang"] = True
        if thumb:
            rec["thumb"] = thumb   # eigenes Thumbnail: {"set": "A"/"B"/None, "error": ...}
        st["uploads"].append(rec)
        write("state.json", st)


SHARE_KEEP = 36  # so viele fertige Shorts bleiben zum Weiterposten auf TikTok und Instagram liegen (ca. 2,4 Tage bei 15 am Tag)


def share_path(video_id):
    return path("share", video_id + ".mp4")


def keep_for_share(video, video_id):
    """Legt eine Kopie des hochgeladenen Videos ab und räumt alte Kopien auf (Speicher sparen)."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id or ""):
        return
    shutil.copyfile(video, share_path(video_id))
    old = sorted(glob.glob(path("share", "*.mp4")), key=os.path.getmtime, reverse=True)[SHARE_KEEP:]
    for f in old:
        try:
            os.remove(f)
        except OSError:
            pass


def set_short_shared(video_id, platform, done):
    """Merkt sich, dass ein KI-Short von Hand auf TikTok oder Instagram gepostet wurde."""
    if platform not in ("tiktok", "instagram"):
        raise ValueError("Unbekannte Plattform.")
    with LOCK:
        st = state()
        u = next((x for x in st["uploads"] if x.get("video_id") == video_id), None)
        if not u:
            raise ValueError("Unbekanntes Video.")
        shared = dict(u.get("shared") or {})
        if done:
            shared[platform] = now().isoformat(timespec="seconds")
        else:
            shared.pop(platform, None)
        u["shared"] = shared
        write("state.json", st)


def share_caption(spec, u):
    """Text zum Einfügen bei TikTok und Instagram: Titel und die Hashtags des Videos."""
    tags = re.findall(r"#\w+", (spec or {}).get("description", ""))
    if not tags:
        tags = ["#" + re.sub(r"\W+", "", t) for t in (spec or {}).get("tags", [])[:4]]
    tags = list(dict.fromkeys(tags + ["#shorts", "#fyp"]))[:6]
    return (u.get("title", "") + "\n\n" + " ".join(tags)).strip()


def mark_slot(slot, done="done_slots"):
    with LOCK:
        st = state()
        st[done] = (st.get(done, []) + [slot])[-120:]
        write("state.json", st)


def mark_clip_posted(slot, record, done="done_slots"):
    """Ein Clip ist online: wie mark_posted, nur ohne Skriptdatei."""
    with LOCK:
        st = state()
        if slot:
            st[done] = (st.get(done, []) + [slot])[-120:]
        st["uploads"].append(record)
        write("state.json", st)


def learnable(posted):
    """Clips zählen nicht für den Lernmodus (sie haben kein Thema und keinen Look der KI-Shorts)."""
    return [p for p in posted if p.get("kind") != "clip" and not p.get("lang")]


def card(spec):
    words = sum(len(s["text"].split()) for s in spec["segments"])
    return {
        "slug": spec["slug"], "title": spec["title"], "niche": spec["niche"],
        "style": spec.get("style", "gradient"), "colors": spec.get("colors", []),
        "car_color": spec.get("car_color", ""), "accent": spec.get("accent", ""),
        "emoji": spec["segments"][0].get("emoji", ""), "hook": spec["segments"][0]["text"].replace("*", ""),
        "seconds": round(words / 2.5 + 0.3 * len(spec["segments"])),
        "hook_check": _safe(lambda: hookcheck.check(spec), None),
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
        if u.get("kind") != "clip" and os.path.exists(share_path(u["video_id"])):
            item["share"] = share_caption(spec, u)  # Kopie liegt bereit: Download und Text für TikTok/Instagram
        if u.get("kind") == "clip" and u.get("campaign"):
            item["thumb"] = f"api/clip/{u['campaign']}/{u['n']}.jpg"
        posted.append(item)
    return posted


def record_history(views, subs, clip=None):
    """Merkt sich Aufrufe und Abonnenten für das Verlaufs-Diagramm, höchstens ein Punkt pro Stunde.

    clip: Kanaldaten des Clip-Kanals (yt.channel), dann kommen clip_views/clip_subs dazu.
    """
    with LOCK:
        hist = read("history.json", [])
        point = {"at": now().isoformat(timespec="minutes"), "views": views, "subs": subs}
        if clip:
            point.update(clip_views=clip.get("views", 0), clip_subs=clip.get("subscribers", 0))
        if hist and hist[-1]["at"][:13] == point["at"][:13]:
            hist[-1] = point
        else:
            hist.append(point)
        write("history.json", hist[-24 * 180:])


def is_long(spec):
    return (spec or {}).get("laenge") == "lang"


def long_days(per_week):
    """Wochentage (0 = Montag) für lange Videos, gleichmäßig verteilt: 4 pro Woche = Mo, Mi, Fr, Sa."""
    per_week = max(0, min(7, int(per_week or 0)))
    return sorted({round(i * 7 / per_week) % 7 for i in range(per_week)}) if per_week else []


def due_long(per_week, hour=19, at=None):
    """Schlüssel des Tages, an dem ein langes Video dran ist (ab hour Uhr bis kurz vor Mitternacht), sonst None."""
    at = at or now()
    if at.weekday() not in long_days(per_week) or at.hour < hour:
        return None
    key = at.strftime("%Y-%m-%d")
    return None if key in state().get("long_slots", []) else key


def due_firma(hour, at=None):
    """Schlüssel des Tages, wenn die Folge des Firmen-Spiels dran ist (ab hour Uhr bis Mitternacht), sonst None."""
    if hour is None:
        return None
    at = at or now()
    if at.hour < int(hour):
        return None
    key = at.strftime("%Y-%m-%d")
    return None if key in state().get("firma_slots", []) else key


# --- Vorrat: fertig gerenderte Shorts ----------------------------------------
# Ein Short braucht auf dem Server rund eine Stunde zum Rendern. Damit trotzdem jede Stunde einer kommt,
# rendert die App in freien Minuten (auch nachts) vor und lädt zum Sendeplatz nur noch hoch.

READY_MAX = 6  # so viele fertige Shorts liegen höchstens bereit


def ready_items():
    """Fertig gerenderte Shorts, älteste zuerst. Räumt Videos weg, deren Skript nicht mehr wartet
    (abgelehnt, gelöscht oder schon gepostet)."""
    items = []
    for meta in sorted(glob.glob(path("ready", "*.json"))):
        try:
            item = read_json(meta)
            ok = os.path.exists(item["video"]) and os.path.exists(path("queue", item["file"]))
        except (OSError, ValueError, KeyError, TypeError):
            item, ok = {}, False
        if not ok:
            for f in (meta, item.get("video")):
                try:
                    if f:
                        os.remove(f)
                except OSError:
                    pass
            continue
        items.append({**item, "meta": meta})
    return items


def add_ready(file, rendered):
    """Legt einen fertig gerenderten Short in den Vorrat. file: Dateiname des Skripts in queue/."""
    stamp = now().strftime("%Y%m%d-%H%M%S-%f")
    meta = path("ready", f"{stamp}-{file}")
    tmp = meta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({**rendered, "file": file, "rendered_at": now().isoformat(timespec="seconds")}, f, ensure_ascii=False)
    os.replace(tmp, meta)


def drop_ready(item):
    for f in (item.get("meta"), item.get("video")):
        try:
            if f:
                os.remove(f)
        except OSError:
            pass


def ready_failed(item):
    """Upload aus dem Vorrat ist schiefgegangen: einmal noch versuchen, danach verwerfen (wird neu gerendert)."""
    tries = int(item.get("tries", 0)) + 1
    if tries >= 2:
        return drop_ready(item)
    data = {k: v for k, v in item.items() if k != "meta"}
    with open(item["meta"], "w", encoding="utf-8") as f:
        json.dump({**data, "tries": tries}, f, ensure_ascii=False)


def read_json(file):
    with open(file, encoding="utf-8") as f:
        return json.load(f)


def _worlds(posted):
    """Look der bisherigen Shorts (True = Blockwelt), älteste zuerst. Firmen-Spiel und Clips zählen nicht."""
    firma = set(state().get("firma_slots", []))
    out = []
    for p in learnable(posted):
        w = (p.get("features") or {}).get("welt")
        if w and p.get("slot") not in firma:
            out.append(w == "Blockwelt 3D")
    return out


def block_share(cfg, at=None):
    n = int(cfg.get("block_per_day") or 0)
    slots = len(hours_for(cfg, at or now())) or 1
    return min(1.0, n / slots) if n > 0 else None


def planned_queue(posted=None, ready_only=False, long=False, with_ready=True):
    """Warteschlange als (datei, skript) in der Reihenfolge, die der Lernmodus vorgibt.

    ready_only: mit Freigabe-Pflicht nur freigegebene Skripte (für den Upload).
    with_ready: fertig gerenderte Shorts (Vorrat) vorne mit aufführen; False = nur, was noch gerendert werden muss.
    """
    import agents

    posted = posted if posted is not None else posted_items()
    cfg = config()
    queue = [(f, load_spec(f)) for f in queue_files()]
    queue = [q for q in queue if is_long(q[1]) == long]  # lange Videos haben eine eigene Warteschlange
    ready = [] if long else ready_items()
    ready_files = [r["file"] for r in ready]
    in_ready = [q for f in ready_files for q in queue if os.path.basename(q[0]) == f]
    head = in_ready if with_ready else []
    queue = [q for q in queue if os.path.basename(q[0]) not in ready_files]
    if ready_only and cfg["approval"]:
        ok = set(state()["approved"])
        queue = [q for q in queue if os.path.basename(q[0]) in ok]
    # Skripte mit "vorrang": true (z. B. "heute noch rausbringen") kommen vor allen anderen dran
    first = [q for q in queue if q[1].get("vorrang")]
    queue = [q for q in queue if not q[1].get("vorrang")]
    planer = agents.settings(cfg)["planer"]
    share = None if long else block_share(cfg)
    if not planer["on"]:
        if share:  # auch ohne Lernmodus: Blockwelt-Anteil halten, sonst Dateireihenfolge
            return head + first + learn.plan(queue, [], None, worlds=_worlds(posted) + [
                learn.is_block(s) for _, s in in_ready + first], block_share=share)
        return head + first + queue  # Lernmodus aus: einfach in Dateireihenfolge
    worlds = _worlds(posted) + [learn.is_block(s) for _, s in in_ready + first]
    posted = learnable(posted)
    history = [p["niche"] for p in posted if p.get("niche")]
    return head + first + learn.plan(queue, history, learn.niche_scores(posted, now()), planer["explore_every"],
                                     worlds=worlds, block_share=share)


def next_look(posted=None):
    """Untertitel-Stil und Übergang für das nächste Video, nach dem was bisher am besten lief."""
    posted = learnable(posted if posted is not None else posted_items())
    return learn.choose_look(learn.feature_scores(posted, now()), len(posted))


def next_thumb(long, posted=None):
    """Thumbnail-Variante für das nächste Video. Lange Videos lernen getrennt von den Shorts."""
    posted = posted if posted is not None else posted_items()
    pool = [p for p in posted if p.get("lang")] if long else learnable(posted)
    return learn.choose_thumb(learn.feature_scores(pool, now()), len(pool))


def thumb_path(slug, variant):
    return path("thumbs", "custom", f"{slug}-{variant}.jpg")


def set_thumb_status(ok, reason="", detail=""):
    """Merkt sich, ob YouTube eigene Thumbnails annimmt (für den Hinweis in der Zentrale).

    detail: der genaue Fehlertext von YouTube, damit man in der Zentrale sieht, woran es liegt.
    """
    with LOCK:
        st = state()
        st["thumb_status"] = {"ok": bool(ok), "reason": reason, "detail": str(detail)[:400],
                              "at": now().isoformat(timespec="seconds")}
        write("state.json", st)


def set_upload_thumb(video_id, variant):
    """Nach einem Wechsel von Hand: Variante beim Upload eintragen (zählt dann fürs Lernen)."""
    import thumbnail
    with LOCK:
        st = state()
        for u in st["uploads"]:
            if u.get("video_id") == video_id:
                u["thumb"] = {"set": variant}
                u["look"] = {**(u.get("look") or {}), "thumbnail": thumbnail.VARIANTS["AB".index(variant)]}
        write("state.json", st)


THUMB_RETRY_MAX = 30   # so viele der letzten Uploads holt „Fehlende nachholen“ höchstens nach


def thumbs_overview(posted, long_queue):
    """Für die Karte „Thumbnails“: Status, nächstes langes Video und die letzten Uploads."""
    recent = [p for p in posted if p.get("kind") != "clip" and p.get("video_id")]
    longs = [p for p in recent if p.get("lang")][-6:]
    shorts = [p for p in recent if not p.get("lang")][-4:]
    pick = lambda p: {"slug": p["slug"], "title": p.get("title", ""), "video_id": p["video_id"],  # noqa: E731
                      "lang": bool(p.get("lang")), "set": (p.get("thumb") or {}).get("set"),
                      "posted_at": p.get("posted_at")}
    missing = sum(1 for p in recent[-THUMB_RETRY_MAX:] if not (p.get("thumb") or {}).get("set"))
    return {"status": state().get("thumb_status"), "missing": missing,
            "next_long": {"slug": long_queue[0]["slug"], "title": long_queue[0]["title"]} if long_queue else None,
            "recent": [pick(p) for p in reversed(longs + shorts)]}


def next_effects(posted=None):
    """Soundeffekte (dezent/stark) für den nächsten Cartoon-Short, nach dem was bisher besser lief."""
    posted = learnable(posted if posted is not None else posted_items())
    return learn.choose_effects(learn.feature_scores(posted, now()), len(posted) + 1)


def next_layout(posted=None):
    """"normal" oder "spannung" (Herzschlag + Countdown). Zählt jeden Cartoon-Short mit,
    auch die vorgerenderten, damit pro 15 Shorts genau der Test-Platz drankommt."""
    posted = learnable(posted if posted is not None else posted_items())
    fs = learn.feature_scores(posted, now())
    with LOCK:
        st = state()
        n = st.get("aufbau_n", 0)
        st["aufbau_n"] = n + 1
        write("state.json", st)
    return learn.choose_layout(n, fs)


def next_voice(spec, posted=None):
    """Stimme für ein Cartoon-Video, nach dem was bisher am besten lief."""
    posted = learnable(posted if posted is not None else posted_items())
    return learn.choose_voice(learn.feature_scores(posted, now()), len(posted), spec)


def next_slot(cfg, at=None):
    at = at or now()
    for day in range(2):
        d = at + dt.timedelta(days=day)
        for h in sorted(int(x) for x in hours_for(cfg, d)):
            slot = d.replace(hour=h, minute=0, second=0, microsecond=0)
            if slot > at:
                return slot
    return None


def _safe(fn, default):
    """Ein kaputter Zusatz-Teil soll nie die ganze Zentrale lahmlegen."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        print("Dashboard-Teil fehlgeschlagen:", repr(e), flush=True)
        return default


def dashboard(extra=None, working=None, repo=True):
    """working: {agent: was er gerade tut} für alle Agenten, die gerade arbeiten."""
    import agents
    import clips

    working = dict(working or {})
    cfg = config()
    st = state()
    stats = read("stats.json", {"videos": {}, "updated_at": None})
    posted = posted_items()
    planned = planned_queue(posted)
    long_planned = planned_queue(posted, long=True)
    approved = set(st["approved"])
    scores = learn.niche_scores(learnable(posted), now())
    ag = agents.settings(cfg)
    ready = {r["file"] for r in ready_items()}
    queue = [{**card(spec), "file": os.path.basename(f), "approved": os.path.basename(f) in approved,
              "ready": os.path.basename(f) in ready, "block": learn.is_block(spec)}
             for f, spec in planned]
    rejected = []
    for f in sorted(glob.glob(path("rejected", "*.json"))):
        try:
            rejected.append({**card(load_spec(f)), "file": os.path.basename(f)})
        except (OSError, ValueError, KeyError):
            continue
    camp = clips.summary()
    return {
        "source": "server",
        "updated_at": now().isoformat(timespec="seconds"),
        "stats_updated_at": stats.get("updated_at"),
        "slots": hours_for(cfg, now()),  # heutige Zeiten
        "slots_weekday": cfg["post_hours"], "slots_weekend": cfg.get("post_hours_weekend") or cfg["post_hours"],
        "privacy": cfg["privacy"],
        "has_client": bool(cfg["client_id"] and cfg["client_secret"]),
        "has_stock": bool(cfg.get("stock_key")),
        "fish": {"has_key": bool(cfg.get("fish_key")), "voice": cfg.get("fish_voice", ""),
                 "voice_dark": cfg.get("fish_voice_dark", ""), "voice_warm": cfg.get("fish_voice_warm", "")},
        "connected": bool(cfg["refresh_token"]),
        "expired": bool(cfg["expired"]) and not cfg["refresh_token"],
        "channel": read("channel.json", None),
        "clip_channel": {"connected": bool(cfg["clip_token"]), "expired": bool(cfg["clip_expired"]) and not cfg["clip_token"],
                         "channel": read("clipchannel.json", None) if cfg["clip_token"] else None},
        "socials": cfg["socials"],
        "queue": queue,
        "long_queue": [{**card(spec), "file": os.path.basename(f)} for f, spec in long_planned],
        "approval": bool(cfg["approval"]),
        "rejected": rejected,
        "agents": agents.overview(cfg, st["agent_runs"], {
            "connected": bool(cfg["refresh_token"]), "analytics": bool(cfg["analytics_token"]),
            "working": set(working), "tasks": working, "queue": len(queue), "posted": len(posted),
            "favorite": learn.favorite(scores), "next_slot": next_slot(cfg), "now": now(), "repo": repo,
            "branding_at": st.get("branding_at"), "clips": camp["totals"]}),
        "campaigns": camp["campaigns"],
        "clipi": _safe(lambda: clipi_overview(cfg, st), {}),
        "comments": _safe(lambda: __import__("comments").overview(cfg), {}),
        "money": _safe(lambda: __import__("money").load(), {"payouts": []}),
        "clip_totals": camp["totals"],
        "clips_running": camp["running"],
        "webhook_token": cfg["webhook_token"],
        "posted": posted,
        "branding_at": st.get("branding_at"),
        "learning": learn.summary(scores, ag["planer"]["explore_every"]) if ag["planer"]["on"]
        else {**learn.summary(scores, ag["planer"]["explore_every"]), "favorite": None, "off": True},
        "looks": learn.feature_summary(learn.feature_scores(learnable(posted), now())) + [
            {**row, "key": "thumbnail_lang", "label": "Thumbnail (lange Videos)"} for row in learn.feature_summary(
                learn.feature_scores([p for p in posted if p.get("lang")], now())) if row["key"] == "thumbnail"],
        "thumbs": _safe(lambda: thumbs_overview(posted, [card(s) for _, s in long_planned]), {}),
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
