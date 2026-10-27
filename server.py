"""Shorts-Zentrale: Website, Zeitplan und Uploads in einem Prozess.

  python3 server.py        startet auf Port 8080 (änderbar mit PORT)

Umgebungsvariablen:
  DATA_DIR       Speicherort (Standard ./data, im Container /data)
  PASSWORD       optional: schützt die Website mit Benutzer "admin" und diesem Passwort
  SCRIPTS_REPO   optional: GitHub-Repo, aus dem neue Skripte geholt werden (z. B. name/auto-youtube)
  GITHUB_TOKEN   optional: nur nötig, wenn dieses Repo privat ist
  OAUTH_PAGE     optional: Weiterleitungsseite für die Zuschauer-Daten
                 (Standard: https://<besitzer>.github.io/<repo>/oauth.html aus SCRIPTS_REPO)
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
status = {"busy": "", "connect": {"status": "idle"}, "oauth_states": {}, "working": set()}
_tts = None
_tts_lock = threading.Lock()


class working:
    """Markiert Agenten als „arbeitet gerade“, solange der Block läuft (für die Website)."""

    def __init__(self, *ids):
        self.ids = ids

    def __enter__(self):
        status["working"].update(self.ids)

    def __exit__(self, *exc):
        status["working"].difference_update(self.ids)


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
        with working("planer"):
            planned = store.planned_queue(ready_only=True)  # Reihenfolge nach Lernmodus
        if not planned:
            store.log("warn", "Sendeplatz verpasst: Kein freigegebenes Video in der Warteschlange."
                      if store.config()["approval"] else "Sendeplatz verpasst: Die Warteschlange ist leer.")
            if slot:
                st = store.state()
                st["done_slots"].append(slot)
                store.write("state.json", st)
            return
        file, spec = planned[0]
        status["busy"] = "Prüft die Verbindung zu YouTube"
        with working("publisher"):
            yt.check(store.config())
        status["busy"] = f"Erstelle Video: {spec['title']}"
        from make_short import build_video
        ag = agents.settings(store.config())
        # Untertitel-Stil, Übergang und Kopfzeile, die bisher am besten liefen (oder fest im Video-Studio)
        look = agents.apply_look(store.next_look(), ag)
        with working("sprecher", "studio"):
            video, total, timings = build_video({**spec, **look, "voice_speed": agents.voice_speed(ag)},
                                                store.path("out"), tts())
        status["busy"] = f"Lade hoch: {spec['title']}"
        with working("publisher"):
            video_id = yt.upload(store.config(), video, spec)
        marks = [round(s / total, 4) for s, _ in timings]  # Satzanfänge, für die Abschalt-Kurve
        store.mark_posted(file, slot, spec, video_id, marks=marks, duration=round(total, 1), look=look)
        for a in ("planer", "sprecher", "studio", "publisher"):
            store.agent_done(a)
        os.remove(video)
        store.log("ok", f"Gepostet: {spec['title']}" + (" (manuell)" if manual else ""))
        refresh_stats()
    except Exception as e:
        if yt.is_expired(e):
            connection_expired()
            return  # Sendeplatz bleibt offen und wird nach dem Neu-Verbinden nachgeholt
        traceback.print_exc()
        store.agent_done("publisher", error=e)
        store.log("error", f"Upload fehlgeschlagen: {e}")
        if slot:  # nicht endlos wiederholen, der nächste Platz versucht es erneut
            st = store.state()
            st["done_slots"].append(slot)
            store.write("state.json", st)
    finally:
        status["busy"] = ""
        work_lock.release()


_last_refresh = [0.0]


def refresh_stats():
    cfg = store.config()
    if not cfg["refresh_token"]:
        return
    _last_refresh[0] = time.time()
    try:
        with working("analyst"):
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
        store.log("error", f"Statistiken konnten nicht geladen werden: {e}")


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
    status["working"].add("zuschauer")
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
        store.log("error", error)
    finally:
        status["working"].discard("zuschauer")


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

    status["working"].add("autor")
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
            store.log("ok", f"{added} neue Skripte in die Warteschlange gelegt.")
            warm_thumbs()
        return added
    except Exception as e:
        store.agent_done("autor", error=e)
        store.log("error", f"Neue Skripte konnten nicht geladen werden: {e}")
        return 0
    finally:
        status["working"].discard("autor")


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
    status["working"].add("designer")
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
        store.log("ok", "Kanal-Design gesetzt: Banner, Beschreibung und Stichwörter.")
    except Exception as e:
        store.agent_done("designer", error=e)
        if yt.is_expired(e):
            return connection_expired()
        store.log("error", f"Kanal-Design konnte nicht gesetzt werden: {e}")
    finally:
        status["working"].discard("designer")


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

    def do_GET(self):
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
                                                   "version": VERSION, "oauth_page": OAUTH_PAGE},
                                                  working=status["working"], repo=bool(SCRIPTS_REPO)))
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
        with working("sprecher"):
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
        with working("studio"):
            img = Scene(spec, timings, total).frame(min(2.2, timings[0][1]))
        buf = io.BytesIO()
        img.resize((540, 960)).save(buf, "JPEG", quality=86)
        self.send(200, buf.getvalue(), "image/jpeg")

    def thumb(self, slug):
        file = store.path("thumbs", slug + ".jpg")
        if not os.path.exists(file):
            spec = store.find_spec(slug)
            if not spec:
                return self.send(404, {"error": "Unbekanntes Video"})
            from make_short import render_thumbnail
            render_thumbnail(spec, file)
        self.send(200, open(file, "rb").read(), "image/jpeg", cache="max-age=86400")

    def do_POST(self):
        if not self.authorized():
            return
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
        if p == "/api/sync":
            background(sync_scripts)
            background(refresh_stats)
            background(refresh_analytics)
            return self.send(200, {"ok": True})
        self.send(404, {"error": "Nicht gefunden"})


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
    if agent not in RUNNERS:
        return self.send(400, {"error": "Dieser Agent lässt sich nicht von Hand starten."})
    if agent in status["working"]:
        return self.send(409, {"error": "Der Agent arbeitet gerade schon."})
    if agent in ("analyst", "designer") and not cfg["refresh_token"]:
        return self.send(400, {"error": "Es ist noch kein Kanal verbunden."})
    if agent == "zuschauer" and not cfg["analytics_token"]:
        return self.send(400, {"error": "Die Zuschauer-Daten sind noch nicht verbunden."})
    if agent == "autor" and not SCRIPTS_REPO:
        return self.send(400, {"error": "Kein Skript-Repo eingestellt (SCRIPTS_REPO)."})
    status["working"].add(agent)  # sofort sichtbar, auch bevor der Thread startet

    def job():
        try:
            RUNNERS[agent]()
        finally:
            status["working"].discard(agent)
    background(job)
    return self.send(200, {"ok": True, "text": "Läuft."})


Handler.run_agent = _run_agent


def main():
    store.init()
    threading.Thread(target=scheduler, daemon=True).start()
    background(warm_thumbs)
    print(f"Shorts-Zentrale läuft auf Port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
