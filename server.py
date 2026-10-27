"""Shorts-Zentrale: Website, Zeitplan und Uploads in einem Prozess.

  python3 server.py        startet auf Port 8080 (änderbar mit PORT)

Umgebungsvariablen:
  DATA_DIR       Speicherort (Standard ./data, im Container /data)
  PASSWORD       optional: schützt die Website mit Benutzer "admin" und diesem Passwort
  SCRIPTS_REPO   optional: GitHub-Repo, aus dem neue Skripte geholt werden (z. B. name/auto-youtube)
  GITHUB_TOKEN   optional: nur nötig, wenn dieses Repo privat ist
  OAUTH_PAGE     optional: Weiterleitungsseite für die Zuschauer-Daten
                 (Standard: https://<besitzer>.github.io/<repo>/oauth.html aus SCRIPTS_REPO)

Video-Webhook (für Kampagnen): POST /webhook/video mit dem Schlüssel aus dem Bereich Kampagnen
  (Header X-Webhook-Token oder ?token=...). Entweder die Videodatei als Body (…?name=Titel&rights=1)
  oder JSON {"url": "http://…/video.mp4", "name": "…", "credit": "@kanal", "rights": true}
  bzw. {"file": "datei.mp4"} für ein Video, das schon im Eingangsordner liegt.
"""
import base64
import datetime as dt
import glob
import json
import os
import re
import secrets
import threading
import time
import traceback
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import agents
import clips
import store
import yt

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
PAGE_HEAD = ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
             '<link rel="icon" href="icon.png"><link rel="apple-touch-icon" href="icon.png">'
             '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);'
             'padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui}'
             'img{max-width:100%}[hidden]{display:none!important}</style></head><body>')
PORT = int(os.environ.get("PORT", "8080"))
PASSWORD = os.environ.get("PASSWORD", "")
SCRIPTS_REPO = os.environ.get("SCRIPTS_REPO", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
OAUTH_PAGE = os.environ.get("OAUTH_PAGE", "").strip() or (
    "https://{}.github.io/{}/oauth.html".format(*SCRIPTS_REPO.split("/", 1)) if "/" in SCRIPTS_REPO else "")
VERSION = {"sha": os.environ.get("APP_VERSION", "dev")[:7], "built": os.environ.get("APP_BUILT", "")}

work_lock = threading.Lock()   # es läuft immer nur ein Upload gleichzeitig
status = {"busy": "", "connect": {"status": "idle"}, "oauth_states": {}}
_tts = None
_tts_lock = threading.Lock()

# Live-Ansicht der Zentrale: wer gerade arbeitet (mit Aufgabe für die Sprechblase) und die letzten Ereignisse.
# Die Website fragt alle paar Sekunden /api/live?since=<seq> und animiert, was neu ist.
_live = {"seq": 0, "events": [], "working": {}}   # working: agent -> (wie oft gerade, Aufgabe)
_live_lock = threading.RLock()


class working:
    """Markiert Agenten als „arbeitet gerade“, solange der Block läuft (für die Website).
    task: kurzer Text für die Sprechblase über dem Agenten, z. B. „Rendert Video #12“."""

    def __init__(self, *ids, task=None):
        self.ids, self.task = ids, task

    def __enter__(self):
        start_work(*self.ids, task=self.task)
        return self

    def __exit__(self, *exc):
        stop_work(*self.ids)


def start_work(*ids, task=None):
    with _live_lock:
        for a in ids:
            n, old = _live["working"].get(a, (0, None))
            _live["working"][a] = (n + 1, task or old)


def stop_work(*ids):
    with _live_lock:
        for a in ids:
            n, task = _live["working"].get(a, (1, None))
            if n <= 1:
                _live["working"].pop(a, None)
            else:
                _live["working"][a] = (n - 1, task)


def set_task(agent, task):
    """Neuer Text für die Sprechblase eines Agenten, der schon arbeitet (z. B. Fortschritt)."""
    with _live_lock:
        if agent in _live["working"]:
            _live["working"][agent] = (_live["working"][agent][0], task)


def tasks_now():
    """{agent: Aufgabe} aller Agenten, die gerade arbeiten."""
    with _live_lock:
        return {a: task or "" for a, (n, task) in _live["working"].items()}


def live_push(entry):
    """Wird für jedes neue Ereignis aus store.log aufgerufen."""
    with _live_lock:
        _live["seq"] += 1
        _live["events"] = (_live["events"] + [{**entry, "seq": _live["seq"]}])[-60:]


def live_since(seq):
    with _live_lock:
        return {"seq": _live["seq"], "events": [e for e in _live["events"] if e["seq"] > seq],
                "working": tasks_now(), "busy": status["busy"]}


def tts():
    global _tts
    with _tts_lock:
        if _tts is None:
            from make_short import load_tts
            _tts = load_tts()
    return _tts


# --- Arbeit ------------------------------------------------------------------

def post_next(slot, manual=False):
    """Rendert das nächste Skript und lädt es hoch."""
    if not work_lock.acquire(blocking=False):
        return
    try:
        with working("planer", task="Wählt das nächste Video"):
            planned = store.planned_queue(ready_only=True)  # Reihenfolge nach Lernmodus
            cfg = store.config()
            clip = clips.choose_for_slot(slot, cfg["post_hours"], agents.settings(cfg)["publisher"]["clips_per_day"],
                                         store.state()["uploads"], scripts_left=bool(planned))
        if clip:
            return post_clip(clip, slot, manual)
        if not planned:
            store.log("warn", "Sendeplatz verpasst: Kein freigegebenes Video in der Warteschlange."
                      if store.config()["approval"] else "Sendeplatz verpasst: Die Warteschlange ist leer.")
            if slot:
                st = store.state()
                st["done_slots"].append(slot)
                store.write("state.json", st)
            return
        file, spec = planned[0]
        n = len(store.state()["uploads"]) + 1  # laufende Nummer für die Sprechblasen
        status["busy"] = "Prüft die Verbindung zu YouTube"
        with working("publisher", task="Prüft die YouTube-Verbindung"):
            yt.check(store.config())
        status["busy"] = f"Erstelle Video: {spec['title']}"
        from make_short import build_video
        ag = agents.settings(store.config())
        # Untertitel-Stil, Übergang und Kopfzeile, die bisher am besten liefen (oder fest im Video-Studio)
        look = agents.apply_look(store.next_look(), ag)
        with working("sprecher", task=f"Spricht Video #{n}"), working("studio", task=f"Rendert Video #{n}"):
            video, total, timings = build_video({**spec, **look, "voice_speed": agents.voice_speed(ag)},
                                                store.path("out"), tts())
        status["busy"] = f"Lade hoch: {spec['title']}"
        with working("publisher", task=f"Lädt Video #{n} hoch"):
            video_id = yt.upload(store.config(), video, spec)
        marks = [round(s / total, 4) for s, _ in timings]  # Satzanfänge, für die Abschalt-Kurve
        store.mark_posted(file, slot, spec, video_id, marks=marks, duration=round(total, 1), look=look)
        for a in ("planer", "sprecher", "studio", "publisher"):
            store.agent_done(a)
        os.remove(video)
        store.log("ok", f"Gepostet: {spec['title']}" + (" (manuell)" if manual else ""),
                  agent="publisher", kind="posted", source="youtube")
        refresh_stats()
    except Exception as e:
        if yt.is_expired(e):
            connection_expired()
            return  # Sendeplatz bleibt offen und wird nach dem Neu-Verbinden nachgeholt
        traceback.print_exc()
        store.agent_done("publisher", error=e)
        store.log("error", f"Upload fehlgeschlagen: {e}", agent="publisher", kind="error")
        if slot:  # nicht endlos wiederholen, der nächste Platz versucht es erneut
            st = store.state()
            st["done_slots"].append(slot)
            store.write("state.json", st)
    finally:
        status["busy"] = ""
        work_lock.release()


def post_clip(item, slot, manual=False):
    """Lädt einen freigegebenen Clip hoch (läuft innerhalb von post_next bzw. mit work_lock)."""
    c, clip = item
    status["busy"] = f"Lade Clip hoch: {clip['title']}"
    with working("publisher", task="Prüft die YouTube-Verbindung"):
        yt.check(store.config())
    with working("publisher", task=f"Lädt Clip „{clip['title'][:28]}“ hoch"):
        video_id = yt.upload(store.config(), clips.clip_path(c, clip), clips.upload_spec(c, clip))
    clips.mark_posted(c["id"], clip["n"], video_id)
    store.mark_clip_posted(slot, clips.upload_record(c, clip, slot, video_id))
    store.agent_done("publisher")
    store.log("ok", f"Clip gepostet: {clip['title']}" + (" (manuell)" if manual else ""),
              agent="publisher", kind="posted", source="youtube")
    refresh_stats()


def post_clip_now(cid, n):
    """„Jetzt posten“ für einen einzelnen Clip aus der Freigabe-Station."""
    if not work_lock.acquire(blocking=False):
        return
    try:
        c = clips.load(cid)
        clip = next(x for x in c["clips"] if x["n"] == n)
        if clip["status"] == "neu":
            clips.set_clip(cid, n, "approve")
            clip["status"] = "freigegeben"
        post_clip((c, clip), None, manual=True)
    except Exception as e:
        if yt.is_expired(e):
            connection_expired()
            return
        traceback.print_exc()
        store.agent_done("publisher", error=e)
        store.log("error", f"Clip-Upload fehlgeschlagen: {e}", agent="publisher", kind="error")
    finally:
        status["busy"] = ""
        work_lock.release()


# --- Video-Clipper -----------------------------------------------------------------

_clip_wake = threading.Event()


def clip_worker():
    """Eigener Faden: holt Videos aus dem Eingangsordner und schneidet bestätigte Kampagnen, eine nach der anderen."""
    while True:
        try:
            ag = agents.settings(store.config())["clipper"]
            if ag["on"]:
                clips.scan_inbox(auto_start=ag["auto_start"])
            job = clips.next_job()
            if job:
                run_clip_job(job["id"], ag)
                continue
        except Exception:
            traceback.print_exc()
        _clip_wake.wait(20)
        _clip_wake.clear()


def run_clip_job(cid, settings):
    start_work("clipper", task="Startet")
    try:
        c = clips.process(cid, settings, task=lambda text: set_task("clipper", text))
        n = len(c["clips"])
        store.agent_done("clipper")
        wait = ", er wartet auf deine Freigabe." if n == 1 else ", sie warten auf deine Freigabe."
        store.log("ok", f"{n} Clip{'s' if n != 1 else ''} aus „{c['name']}“ fertig"
                  + (wait if settings["freigabe"] else " und freigegeben."),
                  agent="clipper", kind="clips", source="clipper")
    except Exception as e:
        traceback.print_exc()
        store.agent_done("clipper", error=e)
        store.log("error", f"Clipping fehlgeschlagen: {e}", agent="clipper", kind="error")
    finally:
        stop_work("clipper")


def webhook_video(h):
    """POST /webhook/video: neues Video für eine Kampagne (geschützt mit dem Webhook-Schlüssel)."""
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(h.path).query)
    token = h.headers.get("X-Webhook-Token") or q.get("token", [""])[0]
    expected = store.config().get("webhook_token") or ""
    if not expected or not secrets.compare_digest(token.encode(), expected.encode()):
        return h.send(401, {"error": "Falscher oder fehlender Schlüssel (X-Webhook-Token)."})
    try:
        length = int(h.headers.get("Content-Length") or 0)
    except ValueError:
        length = 0
    one = lambda k, d="": q.get(k, [d])[0]
    try:
        if (h.headers.get("Content-Type") or "").startswith("application/json"):
            if length > 100_000:
                return h.send(413, {"error": "Zu groß."})
            data = json.loads(h.rfile.read(length) or b"{}")
            rights, credit, name = bool(data.get("rights")), str(data.get("credit") or ""), data.get("name")
            if data.get("file"):
                path = os.path.join(clips.inbox_dir(), os.path.basename(str(data["file"])))
                if not os.path.isfile(path):
                    return h.send(404, {"error": "Datei nicht im Eingangsordner gefunden."})
                c = clips.add_file(path, "webhook", rights, credit, name)
            elif data.get("url"):
                url = str(data["url"])
                clips.check_url(url)
                background(_download, url, rights, credit, name)
                return h.send(202, {"ok": True, "text": "Video wird geladen, die Kampagne erscheint gleich."})
            else:
                return h.send(400, {"error": "Bitte url, file oder die Videodatei selbst schicken."})
        else:
            filename = one("filename") or h.headers.get("X-Filename") or "video.mp4"
            c = clips.add_stream(h.rfile, length, filename, "webhook", one("rights") in ("1", "true", "ja"),
                                 one("credit"), one("name") or None)
    except ValueError as e:
        return h.send(400, {"error": str(e)})
    _clip_wake.set()
    h.send(200, {"ok": True, "campaign": c["id"], "status": c["status"],
                 "text": "Wird geschnitten." if c["status"] == "wartet" else "Bitte im Bereich Kampagnen die Rechte bestätigen."})


def _download(url, rights, credit, name):
    try:
        clips.add_url(url, rights, credit, name)
        _clip_wake.set()
    except Exception as e:
        store.log("error", f"Video vom Webhook konnte nicht geladen werden: {e}", agent="clipper", kind="error")


_last_refresh = [0.0]


def refresh_stats():
    cfg = store.config()
    if not cfg["refresh_token"]:
        return
    _last_refresh[0] = time.time()
    try:
        with working("analyst", task="Holt Aufrufe und Likes"):
            ch = yt.channel(cfg)
            store.write("channel.json", ch)
            ids = [u["video_id"] for u in store.state()["uploads"]]
            videos = yt.video_stats(cfg, ids) if ids else {}
        store.write("stats.json", {"updated_at": store.now().isoformat(timespec="seconds"), "videos": videos})
        store.record_history(sum(v["views"] for v in videos.values()), ch.get("subscribers", 0))
        store.agent_done("analyst")
    except Exception as e:
        store.agent_done("analyst", error=e)
        if yt.is_expired(e):
            return connection_expired()
        store.log("error", f"Statistiken konnten nicht geladen werden: {e}", agent="analyst", kind="error")


def refresh_analytics():
    """Holt von YouTube Analytics, wie lange Zuschauer dranbleiben (Ø angesehen und Kurve je Video).

    YouTube liefert diese Daten mit 1 bis 3 Tagen Verzögerung. Kurven werden je Video höchstens
    alle 12 Stunden neu geholt, damit es schnell bleibt.
    """
    cfg = store.config()
    if not cfg["analytics_token"]:
        return
    data = store.read("analytics.json", {"videos": {}})
    videos = data.get("videos", {})
    uploads = store.state()["uploads"]
    today = store.now().date()
    start = min([u["posted_at"][:10] for u in uploads] or [str(today - dt.timedelta(days=28))])
    start_work("zuschauer", task="Holt Zuschauer-Daten")
    try:
        summary = yt.analytics_summary(cfg, start, str(today))
        fetched = 0
        for u in reversed(uploads):  # neueste zuerst
            vid, age_h = u["video_id"], (store.now() - dt.datetime.fromisoformat(u["posted_at"])).total_seconds() / 3600
            entry = {**videos.get(vid, {}), **summary.get(vid, {})}
            stale = time.time() - entry.get("curve_ts", 0) > 12 * 3600
            if age_h >= 24 and stale and fetched < 30:
                curve = yt.retention_curve(cfg, vid, u["posted_at"][:10], str(today))
                fetched += 1
                if curve:
                    entry["curve"] = [[r, w] for i, (r, w) in enumerate(curve) if i % 2 == 1 or len(curve) <= 50]
                entry["curve_ts"] = time.time()
            if entry:
                videos[vid] = entry
        store.write("analytics.json", {"updated_at": store.now().isoformat(timespec="seconds"),
                                       "videos": videos, "error": None})
        store.agent_done("zuschauer")
    except Exception as e:
        text = str(e)
        if yt.is_expired(e):
            store.save_config(analytics_token="")
            error = "Der Zugang für die Zuschauer-Daten ist abgelaufen. Bitte im Reiter Kanal neu verbinden."
        elif "accessNotConfigured" in text or "has not been used" in text or "is disabled" in text:
            error = "Die YouTube Analytics API ist im Google-Projekt noch nicht aktiviert."
        else:
            error = f"Zuschauer-Daten konnten nicht geladen werden: {text[:200]}"
        store.write("analytics.json", {**data, "error": error})
        store.agent_done("zuschauer", error=error)
        store.log("error", error, agent="zuschauer", kind="error")
    finally:
        stop_work("zuschauer")


def connection_expired():
    """Google nimmt den Zugang nicht mehr an: Kanal als getrennt markieren, damit die Website es anzeigt."""
    store.save_config(refresh_token="", expired=True)
    status["connect"] = {"status": "idle"}
    store.log("warn", "Die Verbindung zu YouTube ist abgelaufen. Bitte im Reiter Kanal neu verbinden.")


def sync_scripts():
    """Holt neue Skripte aus dem GitHub-Repo (Ordner seed/)."""
    if not SCRIPTS_REPO:
        return 0
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "shorts-zentrale"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    def get(url):
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            return json.load(r)

    start_work("autor", task="Holt neue Skripte")
    try:
        listing = get(f"https://api.github.com/repos/{SCRIPTS_REPO}/contents/seed")
        known = set(store.state()["known"])
        files = {}
        for item in listing:
            if item["name"].endswith(".json") and item["name"] not in known:
                blob = get(item["url"])
                files[item["name"]] = base64.b64decode(blob["content"]).decode("utf-8")
        added = store.add_scripts(files)
        store.agent_done("autor")
        if added:
            store.log("ok", f"{added} neue Skripte in die Warteschlange gelegt.", agent="autor", kind="scripts",
                      source="github")
            warm_thumbs()
        return added
    except Exception as e:
        store.agent_done("autor", error=e)
        store.log("error", f"Neue Skripte konnten nicht geladen werden: {e}", agent="autor", kind="error")
        return 0
    finally:
        stop_work("autor")


def connect_channel():
    cfg = store.config()
    try:
        code = yt.device_start(cfg["client_id"])
        status["connect"] = {"status": "code", "user_code": code["user_code"],
                             "verification_url": code.get("verification_url", "https://www.google.com/device"),
                             "expires_at": code["expires_at"]}
        token = yt.device_wait(cfg["client_id"], cfg["client_secret"], code)
        store.save_config(refresh_token=token, expired=False)
        refresh_stats()
        ch = store.read("channel.json", {}) or {}
        status["connect"] = {"status": "verbunden"}
        store.log("ok", f"Kanal verbunden: {ch.get('title', 'YouTube')}")
        apply_branding()
    except Exception as e:
        status["connect"] = {"status": "fehler", "message": str(e)}
        store.log("error", f"Kanal-Verbindung fehlgeschlagen: {e}")


def apply_branding(force=False):
    """Setzt Banner, Beschreibung und Stichwörter auf YouTube, einmal je Design-Version."""
    import branding

    cfg, st = store.config(), store.state()
    if not cfg["refresh_token"] or (not force and st.get("branding_version") == branding.VERSION):
        return
    start_work("designer", task="Setzt Banner und Beschreibung")
    try:
        title = (store.read("channel.json", {}) or {}).get("title") or "60 Sekunden Wissen"
        banner, profile = branding.render_all(title, cfg["post_hours"], store.path("branding"))
        yt.set_branding(cfg, banner, branding.description(title, cfg["post_hours"]), branding.KEYWORDS)
        with store.LOCK:
            st = store.state()
            st["branding_version"] = branding.VERSION
            st["branding_at"] = store.now().isoformat(timespec="seconds")
            store.write("state.json", st)
        store.agent_done("designer")
        store.log("ok", "Kanal-Design gesetzt: Banner, Beschreibung und Stichwörter.", agent="designer",
                  kind="branding", source="youtube")
    except Exception as e:
        store.agent_done("designer", error=e)
        if yt.is_expired(e):
            return connection_expired()
        store.log("error", f"Kanal-Design konnte nicht gesetzt werden: {e}", agent="designer", kind="error")
    finally:
        stop_work("designer")


def warm_thumbs():
    """Erstellt fehlende Vorschaubilder im Hintergrund, damit die Website sofort Bilder zeigt."""
    from make_short import render_thumbnail
    for f in store.queue_files() + glob.glob(store.path("posted", "*.json")):
        try:
            spec = store.load_spec(f)
            target = store.path("thumbs", spec["slug"] + ".jpg")
            if not os.path.exists(target):
                render_thumbnail(spec, target)
        except Exception as e:
            print(f"Vorschaubild fehlgeschlagen ({f}): {e}", flush=True)


def background(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


def scheduler():
    last_stats = last_sync = last_analytics = 0.0
    while True:
        try:
            cfg = store.config()
            ag = agents.settings(cfg)
            if cfg["refresh_token"]:
                slot = store.due_slot() if ag["publisher"]["on"] else None
                if slot and not status["busy"]:
                    post_next(slot)
                if time.time() - last_stats > ag["analyst"]["minutes"] * 60:  # kostet kaum API-Quote
                    refresh_stats()
                    if ag["designer"]["on"]:
                        apply_branding()
                    last_stats = time.time()
            if cfg["analytics_token"] and time.time() - last_analytics > ag["zuschauer"]["hours"] * 3600:
                last_analytics = time.time()
                refresh_analytics()
            if ag["autor"]["on"] and time.time() - last_sync > ag["autor"]["hours"] * 3600:
                sync_scripts()
                last_sync = time.time()
        except Exception:
            traceback.print_exc()
        time.sleep(30)


# --- Website -----------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "ShortsZentrale"

    def log_message(self, *args):
        pass

    def authorized(self):
        if not PASSWORD:
            return True
        expected = "Basic " + base64.b64encode(f"admin:{PASSWORD}".encode()).decode()
        if self.headers.get("Authorization") == expected:
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Shorts-Zentrale"')
        self.end_headers()
        return False

    def send(self, code, body, ctype="application/json; charset=utf-8", cache="no-store"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def send_file(self, path, ctype, download=None):
        """Datei mit Range-Unterstützung (damit man im Video-Player spulen kann)."""
        size = os.path.getsize(path)
        start, end, code = 0, size - 1, 200
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
            else:
                start = max(0, size - int(m.group(2)))
            if start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            code = 206
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-cache")
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if download:
            safe = re.sub(r"[^A-Za-z0-9._-]+", "-", download).strip("-") or "clip"
            self.send_header("Content-Disposition", f"attachment; filename=\"{safe}.mp4\"; "
                             f"filename*=UTF-8''{urllib.parse.quote(download)}.mp4")
        self.end_headers()
        try:
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(left, 256 * 1024))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path.startswith("/webhook/"):
            return self.send(200, {"ok": True, "info": "Shorts-Zentrale: Video-Webhook. Videos per POST schicken."})
        if not self.authorized():
            return
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            page = PAGE_HEAD + open(os.path.join(WEB, "index.html"), encoding="utf-8").read() + "</body></html>"
            return self.send(200, page, "text/html; charset=utf-8")
        if p in ("/icon.png", "/favicon.ico"):
            return self.send(200, open(os.path.join(WEB, "icon.png"), "rb").read(), "image/png", cache="max-age=86400")
        if p == "/api/dashboard":
            if time.time() - _last_refresh[0] > 5 * 60:  # Website offen: Aufrufe frisch holen
                _last_refresh[0] = time.time()
                background(refresh_stats)
            return self.send(200, store.dashboard({"busy": status["busy"], "connect": status["connect"],
                                                   "version": VERSION, "oauth_page": OAUTH_PAGE,
                                                   "live_seq": live_since(10 ** 12)["seq"]},
                                                  working=tasks_now(), repo=bool(SCRIPTS_REPO)))
        if p == "/api/live":
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            try:
                since = int(q.get("since", ["0"])[0])
            except ValueError:
                since = 0
            return self.send(200, live_since(since))
        m = re.fullmatch(r"/api/clip/([a-z0-9-]+)/(\d+)\.(mp4|jpg)", p)
        if m:
            return self.clip_file(m.group(1), int(m.group(2)), m.group(3))
        if p == "/api/voice-sample.wav":
            return self.voice_sample()
        if p == "/api/preview.jpg":
            return self.preview()
        if p == "/api/analytics/callback":
            return self.analytics_callback()
        m = re.fullmatch(r"/api/thumb/([a-z0-9-]+)\.jpg", p)
        if m:
            return self.thumb(m.group(1))
        self.send(404, {"error": "Nicht gefunden"})

    def analytics_callback(self):
        """Google hat über die Weiterleitungsseite einen Code geschickt: gegen einen Zugang tauschen."""
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        nonce = (q.get("state", [""])[0]).split(".")[0]
        ok = nonce and status["oauth_states"].pop(nonce, None)
        note = ""
        if q.get("error"):
            note = "abgebrochen"
        elif not ok:
            note = "ungueltig"
        else:
            cfg = store.config()
            try:
                token = yt.analytics_exchange(cfg["analytics_client_id"], cfg["analytics_client_secret"],
                                              OAUTH_PAGE, q.get("code", [""])[0])
                store.save_config(analytics_token=token)
                store.write("analytics.json", {**store.read("analytics.json", {"videos": {}}), "error": None})
                store.log("ok", "Zuschauer-Daten verbunden. Die ersten Werte kommen in den nächsten Minuten.")
                background(refresh_analytics)
                note = "ok"
            except Exception as e:
                store.log("error", f"Zuschauer-Daten: Verbindung fehlgeschlagen: {e}")
                note = "fehler"
        self.send_response(303)
        self.send_header("Location", f"/?analytics={note}#zuschauer")
        self.end_headers()

    def voice_sample(self):
        """Ein Satz mit dem eingestellten Sprechtempo, zum Probehören im Panel des Sprechers."""
        import io
        import wave

        import numpy as np
        from piper import SynthesisConfig

        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        ag = agents.settings(store.config())
        try:
            tempo = agents.validate("sprecher", {"tempo": q.get("tempo", [ag["sprecher"]["tempo"]])[0]})["tempo"]
        except ValueError:
            tempo = ag["sprecher"]["tempo"]
        voice = tts()
        cfg = SynthesisConfig(length_scale=round(agents.BASE_SPEED * 100 / tempo, 3))
        text = "Hallo! So klingt die Stimme deiner Shorts mit diesem Sprechtempo."
        with working("sprecher", task="Spricht eine Hörprobe"):
            audio = np.concatenate([c.audio_float_array for c in voice.synthesize(text, syn_config=cfg)])
        buf = io.BytesIO()
        with wave.open(buf, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(voice.config.sample_rate)
            f.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
        self.send(200, buf.getvalue(), "audio/wav")

    def preview(self):
        """Bild aus dem nächsten Video mit dem Look, den das Video-Studio gerade wählen würde."""
        import io

        from make_short import Scene, estimated_timings

        planned = store.planned_queue()
        if not planned:
            return self.send(404, {"error": "Die Warteschlange ist leer."})
        spec = planned[0][1]
        look = agents.apply_look(store.next_look(), agents.settings(store.config()))
        spec = {**spec, **look}
        timings, total = estimated_timings(spec)
        with working("studio", task="Rendert eine Vorschau"):
            img = Scene(spec, timings, total).frame(min(2.2, timings[0][1]))
        buf = io.BytesIO()
        img.resize((540, 960)).save(buf, "JPEG", quality=86)
        self.send(200, buf.getvalue(), "image/jpeg")

    def clip_file(self, cid, n, ext):
        try:
            c = clips.load(cid)
            clip = next(x for x in c["clips"] if x["n"] == n)
            path = clips.clip_path(c, clip, ext)
        except (OSError, ValueError, StopIteration):
            return self.send(404, {"error": "Clip nicht gefunden"})
        if not os.path.exists(path):
            return self.send(404, {"error": "Clip nicht gefunden"})
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        if ext == "jpg":
            return self.send(200, open(path, "rb").read(), "image/jpeg", cache="max-age=3600")
        self.send_file(path, "video/mp4", download=clip["title"] if q.get("download") else None)

    def thumb(self, slug):
        if slug.startswith("clip-"):  # geposteter Clip: Vorschaubild aus der Kampagne
            file = clips.thumb_file(slug)
            if file and os.path.exists(file):
                return self.send(200, open(file, "rb").read(), "image/jpeg", cache="max-age=86400")
            return self.send(404, {"error": "Unbekanntes Video"})
        file = store.path("thumbs", slug + ".jpg")
        if not os.path.exists(file):
            spec = store.find_spec(slug)
            if not spec:
                return self.send(404, {"error": "Unbekanntes Video"})
            from make_short import render_thumbnail
            render_thumbnail(spec, file)
        self.send(200, open(file, "rb").read(), "image/jpeg", cache="max-age=86400")

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/webhook/video":
            return webhook_video(self)
        if not self.authorized():
            return
        if path == "/api/campaign/upload":
            return self.campaign_upload()
        p, data = self.path, self.body()
        if p == "/api/settings":
            changes = {}
            for key in ("client_id", "client_secret", "analytics_client_id", "analytics_client_secret"):
                if isinstance(data.get(key), str) and data[key].strip():
                    changes[key] = data[key].strip()
            if any(c in changes.get(k, "") for k in ("client_secret", "analytics_client_secret") for c in "*•"):
                return self.send(400, {"error": "Das ist nur die verdeckte Anzeige. Bitte in Google Cloud "
                                                "„Secret hinzufügen“ klicken und den neuen Schlüssel kopieren."})
            if any(changes.get(k) and not changes[k].endswith(".apps.googleusercontent.com")
                   for k in ("client_id", "analytics_client_id")):
                return self.send(400, {"error": "Die Client-ID endet auf .apps.googleusercontent.com. Bitte prüfen."})
            if changes.get("client_id") and changes["client_id"] != store.config()["client_id"]:
                changes["refresh_token"] = ""  # die alte Verbindung gehört zum alten Client
            if "post_hours" in data:
                hours = sorted({int(h) for h in data["post_hours"] if 0 <= int(h) <= 23})
                if not 1 <= len(hours) <= 6:
                    return self.send(400, {"error": "Bitte 1 bis 6 Sendezeiten wählen."})
                changes["post_hours"] = hours
            if data.get("privacy") in ("public", "unlisted", "private"):
                changes["privacy"] = data["privacy"]
            store.save_config(**changes)
            return self.send(200, {"ok": True})
        if p == "/api/connect":
            cfg = store.config()
            if not (cfg["client_id"] and cfg["client_secret"]):
                return self.send(400, {"error": "Bitte zuerst Client-ID und Clientschlüssel speichern."})
            status["connect"] = {"status": "start"}
            background(connect_channel)
            return self.send(200, {"ok": True})
        if p == "/api/analytics/start":
            cfg = store.config()
            if not (cfg["analytics_client_id"] and cfg["analytics_client_secret"]):
                return self.send(400, {"error": "Bitte zuerst Client-ID und Clientschlüssel der Webanwendung speichern."})
            if not OAUTH_PAGE:
                return self.send(400, {"error": "Keine Weiterleitungsseite eingestellt (SCRIPTS_REPO oder OAUTH_PAGE)."})
            origin = str(data.get("origin", ""))
            if not re.fullmatch(r"https?://[\w.\-\[\]:]+", origin):
                return self.send(400, {"error": "Ungültige Adresse."})
            nonce = secrets.token_urlsafe(16)
            status["oauth_states"] = {**dict(list(status["oauth_states"].items())[-5:]), nonce: origin}
            state = nonce + "." + base64.urlsafe_b64encode(origin.encode()).decode().rstrip("=")
            return self.send(200, {"url": yt.analytics_auth_url(cfg["analytics_client_id"], OAUTH_PAGE, state)})
        if p == "/api/analytics/disconnect":
            store.save_config(analytics_token="")
            store.log("warn", "Zuschauer-Daten getrennt.")
            return self.send(200, {"ok": True})
        if p == "/api/disconnect":
            store.save_config(refresh_token="", expired=False)
            store.write("channel.json", None)
            status["connect"] = {"status": "idle"}
            store.log("warn", "Kanal getrennt.")
            return self.send(200, {"ok": True})
        if p == "/api/post-now":
            if not store.config()["refresh_token"]:
                return self.send(400, {"error": "Es ist noch kein Kanal verbunden."})
            if status["busy"]:
                return self.send(409, {"error": "Es läuft gerade schon ein Upload."})
            status["busy"] = "Startet …"
            background(post_next, None, True)
            return self.send(200, {"ok": True})
        if p == "/api/agent":
            try:
                agent = str(data.get("id", ""))
                changes = agents.validate(agent, data.get("settings") or {})
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            saved = store.config().get("agents") or {}
            saved[agent] = {**(saved.get(agent) or {}), **changes}
            store.save_config(agents=saved)
            return self.send(200, {"ok": True, "settings": agents.settings(store.config())[agent]})
        if p == "/api/agent/run":
            return self.run_agent(str(data.get("id", "")))
        if p == "/api/approval":
            store.save_config(approval=bool(data.get("on")))
            store.log("info", "Freigabe-Pflicht eingeschaltet: Nur freigegebene Videos gehen online."
                      if data.get("on") else "Freigabe-Pflicht ausgeschaltet: Alle Videos gehen automatisch online.")
            return self.send(200, {"ok": True})
        if p in ("/api/approve", "/api/reject", "/api/restore"):
            name = str(data.get("file", ""))
            try:
                {"/api/approve": store.approve, "/api/reject": store.reject, "/api/restore": store.restore}[p](name)
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            if p == "/api/reject":
                store.log("warn", f"Skript abgelehnt: {name}")
            return self.send(200, {"ok": True})
        if p in ("/api/campaign/confirm", "/api/campaign/retry", "/api/campaign/delete"):
            cid = str(data.get("id", ""))
            try:
                if p.endswith("confirm"):
                    c = clips.confirm(cid, data.get("credit"))
                    store.log("info", f"Rechte bestätigt, wird geschnitten: {c['name']}", agent="clipper", kind="input")
                elif p.endswith("retry"):
                    clips.retry(cid)
                else:
                    name = clips.load(cid)["name"]
                    clips.delete(cid)
                    store.log("warn", f"Kampagne gelöscht: {name}", agent="clipper")
            except (OSError, ValueError) as e:
                return self.send(400, {"error": str(e) if isinstance(e, ValueError) else "Unbekannte Kampagne."})
            _clip_wake.set()
            return self.send(200, {"ok": True})
        if p == "/api/clip":
            try:
                c = clips.set_clip(str(data.get("id", "")), int(data.get("n", 0)), str(data.get("action", "")),
                                   data.get("title"))
            except (OSError, ValueError, TypeError) as e:
                return self.send(400, {"error": str(e) if isinstance(e, ValueError) else "Unbekannter Clip."})
            if data.get("action") == "reject":
                store.log("warn", f"Clip abgelehnt: {c['name']} #{data.get('n')}", agent="clipper")
            return self.send(200, {"ok": True})
        if p == "/api/clip/post":
            if not store.config()["refresh_token"]:
                return self.send(400, {"error": "Es ist noch kein Kanal verbunden."})
            if status["busy"]:
                return self.send(409, {"error": "Es läuft gerade schon ein Upload."})
            try:
                cid, n = str(data.get("id", "")), int(data.get("n", 0))
                clip = next(x for x in clips.load(cid)["clips"] if x["n"] == n)
            except (OSError, ValueError, TypeError, StopIteration):
                return self.send(400, {"error": "Unbekannter Clip."})
            if clip["status"] in ("gepostet", "abgelehnt"):
                return self.send(400, {"error": "Dieser Clip kann nicht gepostet werden."})
            status["busy"] = "Startet …"
            background(post_clip_now, cid, n)
            return self.send(200, {"ok": True, "text": "Der Clip wird hochgeladen."})
        if p == "/api/sync":
            background(sync_scripts)
            background(refresh_stats)
            background(refresh_analytics)
            return self.send(200, {"ok": True})
        self.send(404, {"error": "Nicht gefunden"})


    def campaign_upload(self):
        """Upload eines Videos von der Website, als Datei-Body (?name=…&credit=…&rights=1&filename=…)."""
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        one = lambda k: q.get(k, [""])[0]
        if one("rights") != "1":
            return self.send(400, {"error": "Bitte bestätigen, dass du das Video verwenden darfst."})
        try:
            c = clips.add_stream(self.rfile, int(self.headers.get("Content-Length") or 0), one("filename"),
                                 "upload", True, one("credit"), one("name") or None)
        except ValueError as e:
            return self.send(400, {"error": str(e)})
        _clip_wake.set()
        return self.send(200, {"ok": True, "campaign": c["id"]})


RUNNERS = {"autor": sync_scripts, "analyst": refresh_stats, "zuschauer": refresh_analytics,
           "designer": lambda: apply_branding(force=True)}


def _run_agent(self, agent):
    cfg = store.config()
    if agent == "publisher":
        if not cfg["refresh_token"]:
            return self.send(400, {"error": "Es ist noch kein Kanal verbunden."})
        if status["busy"]:
            return self.send(409, {"error": "Es läuft gerade schon ein Upload."})
        status["busy"] = "Startet …"
        background(post_next, None, True)
        return self.send(200, {"ok": True, "text": "Das nächste Video wird erstellt und hochgeladen. Das dauert ein paar Minuten."})
    if agent == "clipper":
        background(clips.scan_inbox, agents.settings(cfg)["clipper"]["auto_start"])
        _clip_wake.set()
        return self.send(200, {"ok": True, "text": "Der Clipper prüft den Eingang. Neue Videos erscheinen gleich im Bereich Kampagnen."})
    if agent not in RUNNERS:
        return self.send(400, {"error": "Dieser Agent lässt sich nicht von Hand starten."})
    if agent in tasks_now():
        return self.send(409, {"error": "Der Agent arbeitet gerade schon."})
    if agent in ("analyst", "designer") and not cfg["refresh_token"]:
        return self.send(400, {"error": "Es ist noch kein Kanal verbunden."})
    if agent == "zuschauer" and not cfg["analytics_token"]:
        return self.send(400, {"error": "Die Zuschauer-Daten sind noch nicht verbunden."})
    if agent == "autor" and not SCRIPTS_REPO:
        return self.send(400, {"error": "Kein Skript-Repo eingestellt (SCRIPTS_REPO)."})
    start_work(agent)  # sofort sichtbar, auch bevor der Thread startet

    def job():
        try:
            RUNNERS[agent]()
        finally:
            stop_work(agent)
    background(job)
    return self.send(200, {"ok": True, "text": "Läuft."})


Handler.run_agent = _run_agent


def main():
    store.init()
    store.LISTENERS.append(live_push)
    clips.stale_cleanup()
    threading.Thread(target=scheduler, daemon=True).start()
    threading.Thread(target=clip_worker, daemon=True).start()
    background(warm_thumbs)
    print(f"Shorts-Zentrale läuft auf Port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
