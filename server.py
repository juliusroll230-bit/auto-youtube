"""Shorts-Zentrale: Website, Zeitplan und Uploads in einem Prozess.

  python3 server.py        startet auf Port 8080 (änderbar mit PORT)

Umgebungsvariablen:
  DATA_DIR       Speicherort (Standard ./data, im Container /data)
  PASSWORD       optional: schützt die Website mit Benutzer "admin" und diesem Passwort
  SCRIPTS_REPO   optional: GitHub-Repo, aus dem neue Skripte geholt werden (z. B. name/auto-youtube)
  GITHUB_TOKEN   optional: nur nötig, wenn dieses Repo privat ist
"""
import base64
import glob
import json
import os
import re
import threading
import time
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
VERSION = {"sha": os.environ.get("APP_VERSION", "dev")[:7], "built": os.environ.get("APP_BUILT", "")}

work_lock = threading.Lock()   # es läuft immer nur ein Upload gleichzeitig
status = {"busy": "", "connect": {"status": "idle"}}
_tts = None


# --- Arbeit ------------------------------------------------------------------

def post_next(slot, manual=False):
    """Rendert das nächste Skript und lädt es hoch."""
    global _tts
    if not work_lock.acquire(blocking=False):
        return
    try:
        planned = store.planned_queue()  # Reihenfolge nach Lernmodus
        if not planned:
            store.log("warn", "Sendeplatz verpasst: Die Warteschlange ist leer.")
            if slot:
                st = store.state()
                st["done_slots"].append(slot)
                store.write("state.json", st)
            return
        file, spec = planned[0]
        status["busy"] = "Prüft die Verbindung zu YouTube"
        yt.check(store.config())
        status["busy"] = f"Erstelle Video: {spec['title']}"
        from make_short import build_video, load_tts
        _tts = _tts or load_tts()
        video, _ = build_video(spec, store.path("out"), _tts)
        status["busy"] = f"Lade hoch: {spec['title']}"
        video_id = yt.upload(store.config(), video, spec)
        store.mark_posted(file, slot, spec, video_id)
        os.remove(video)
        store.log("ok", f"Gepostet: {spec['title']}" + (" (manuell)" if manual else ""))
        refresh_stats()
    except Exception as e:
        if yt.is_expired(e):
            connection_expired()
            return  # Sendeplatz bleibt offen und wird nach dem Neu-Verbinden nachgeholt
        traceback.print_exc()
        store.log("error", f"Upload fehlgeschlagen: {e}")
        if slot:  # nicht endlos wiederholen, der nächste Platz versucht es erneut
            st = store.state()
            st["done_slots"].append(slot)
            store.write("state.json", st)
    finally:
        status["busy"] = ""
        work_lock.release()


def refresh_stats():
    cfg = store.config()
    if not cfg["refresh_token"]:
        return
    try:
        store.write("channel.json", yt.channel(cfg))
        ids = [u["video_id"] for u in store.state()["uploads"]]
        store.write("stats.json", {"updated_at": store.now().isoformat(timespec="seconds"),
                                   "videos": yt.video_stats(cfg, ids) if ids else {}})
    except Exception as e:
        if yt.is_expired(e):
            return connection_expired()
        store.log("error", f"Statistiken konnten nicht geladen werden: {e}")


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

    try:
        listing = get(f"https://api.github.com/repos/{SCRIPTS_REPO}/contents/seed")
        known = set(store.state()["known"])
        files = {}
        for item in listing:
            if item["name"].endswith(".json") and item["name"] not in known:
                blob = get(item["url"])
                files[item["name"]] = base64.b64decode(blob["content"]).decode("utf-8")
        added = store.add_scripts(files)
        if added:
            store.log("ok", f"{added} neue Skripte in die Warteschlange gelegt.")
            warm_thumbs()
        return added
    except Exception as e:
        store.log("error", f"Neue Skripte konnten nicht geladen werden: {e}")
        return 0


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
    try:
        title = (store.read("channel.json", {}) or {}).get("title") or "60 Sekunden Wissen"
        banner, profile = branding.render_all(title, cfg["post_hours"], store.path("branding"))
        yt.set_branding(cfg, banner, branding.description(title, cfg["post_hours"]), branding.KEYWORDS)
        with store.LOCK:
            st = store.state()
            st["branding_version"] = branding.VERSION
            store.write("state.json", st)
        store.log("ok", "Kanal-Design gesetzt: Banner, Beschreibung und Stichwörter.")
    except Exception as e:
        if yt.is_expired(e):
            return connection_expired()
        store.log("error", f"Kanal-Design konnte nicht gesetzt werden: {e}")


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
    last_stats = last_sync = 0.0
    while True:
        try:
            if store.config()["refresh_token"]:
                slot = store.due_slot()
                if slot and not status["busy"]:
                    post_next(slot)
                if time.time() - last_stats > 3 * 3600:
                    refresh_stats()
                    apply_branding()
                    last_stats = time.time()
            if time.time() - last_sync > 2 * 3600:
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
            return self.send(200, store.dashboard({"busy": status["busy"], "connect": status["connect"],
                                                   "version": VERSION}))
        m = re.fullmatch(r"/api/thumb/([a-z0-9-]+)\.jpg", p)
        if m:
            return self.thumb(m.group(1))
        self.send(404, {"error": "Nicht gefunden"})

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
            for key in ("client_id", "client_secret"):
                if isinstance(data.get(key), str) and data[key].strip():
                    changes[key] = data[key].strip()
            if "*" in changes.get("client_secret", "") or "•" in changes.get("client_secret", ""):
                return self.send(400, {"error": "Das ist nur die verdeckte Anzeige. Bitte in Google Cloud "
                                                "„Secret hinzufügen“ klicken und den neuen Schlüssel kopieren."})
            if changes.get("client_id") and not changes["client_id"].endswith(".apps.googleusercontent.com"):
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
        if p == "/api/sync":
            background(sync_scripts)
            return self.send(200, {"ok": True})
        self.send(404, {"error": "Nicht gefunden"})


def main():
    store.init()
    threading.Thread(target=scheduler, daemon=True).start()
    background(warm_thumbs)
    print(f"Shorts-Zentrale läuft auf Port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
