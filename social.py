"""Die besten Shorts automatisch auf Instagram (Reels) und als Entwurf zu TikTok schicken.

Nur offizielle Schnittstellen, nur eigene Videos (die KI-Shorts der App):

Instagram (Meta, „Instagram API with Facebook Login“): Reels auf das eigene Creator- oder
Business-Konto, das mit einer Facebook-Seite verbunden ist. Eine Meta-App im Entwicklungsmodus
reicht, wenn nur Julius (als Admin oder Tester der App) sie benutzt. Einrichtung: App-ID,
App-Geheimnis und ein kurzer Nutzer-Token aus dem Graph-API-Explorer einfügen. Die App tauscht
ihn gegen einen Seiten-Token, der nicht abläuft. Das Video geht per „resumable upload“ direkt
vom Server zu Meta (rupload.facebook.com), braucht also keine öffentliche Adresse.

TikTok (Content Posting API, „Upload to inbox“, Berechtigung video.upload): Das Video landet als
Entwurf in der TikTok-App, Julius tippt dort auf Posten. Direktes Posten erlaubt TikTok nur
geprüften Firmen-Apps (ungeprüft geht nur privat), darum nur Entwurf. Anmeldung über die
Weiterleitungsseite docs/oauth.html (state beginnt mit "tt").

Was gesendet wurde, steht in state.json beim Upload unter "auto" (z. B. {"instagram": "…", "tiktok": "…"}).
Instagram setzt zusätzlich "shared.instagram" (der Haken in der Zentrale). TikTok nicht: der Haken
kommt erst, wenn Julius den Entwurf wirklich gepostet hat.

Einstellungen und Zugänge liegen in social.json.
"""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import store

FILE = "social.json"
GRAPH = "https://graph.facebook.com/v21.0"
RUPLOAD = "https://rupload.facebook.com/ig-api-upload/v21.0"
TT_AUTH = "https://www.tiktok.com/v2/auth/authorize/"
TT_API = "https://open.tiktokapis.com/v2"
TT_SCOPES = "user.info.basic,video.upload"
IG_SCOPES = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement,business_management"

PER_DAY = (0, 5)               # so viele Shorts je Plattform und Tag (0 = aus)
HOURS = (12, 22)               # nur in dieser Zeit senden (deutsche Zeit)
GAP_H = 3                      # Abstand zwischen zwei automatischen Posts derselben Plattform
WINDOW_H = 48                  # nur Shorts der letzten 2 Tage kommen in Frage
MIN_AGE_H = 3                  # erst ein paar Stunden YouTube-Aufrufe sammeln, dann die besten nehmen
DEFAULTS = {
    "instagram": {"on": False, "per_day": 2, "app_id": "", "app_secret": "", "token": "", "ig_id": "",
                  "username": "", "page": "", "error": None, "last": None},
    "tiktok": {"on": False, "per_day": 2, "client_key": "", "client_secret": "", "access": "", "refresh": "",
               "expires": 0, "open_id": "", "username": "", "error": None, "last": None},
}


# --- Speichern ----------------------------------------------------------------

def load():
    d = store.read(FILE, {}) or {}
    return {k: {**v, **(d.get(k) or {})} for k, v in DEFAULTS.items()}


def save(d):
    store.write(FILE, d)


def summary():
    """Für die Zentrale: ohne Geheimnisse."""
    d = load()
    ig, tt = d["instagram"], d["tiktok"]
    return {
        "instagram": {"on": ig["on"], "per_day": ig["per_day"], "connected": bool(ig["token"] and ig["ig_id"]),
                      "username": ig["username"], "page": ig["page"], "app_id": ig["app_id"],
                      "has_secret": bool(ig["app_secret"]), "error": ig["error"], "last": ig["last"]},
        "tiktok": {"on": tt["on"], "per_day": tt["per_day"], "connected": bool(tt["refresh"]),
                   "username": tt["username"], "client_key": tt["client_key"], "has_secret": bool(tt["client_secret"]),
                   "error": tt["error"], "last": tt["last"]},
    }


def set_settings(platform, on=None, per_day=None, **keys):
    if platform not in DEFAULTS:
        raise ValueError("Unbekannte Plattform.")
    d = load()
    p = d[platform]
    if on is not None:
        p["on"] = bool(on)
    if per_day is not None:
        n = int(per_day)
        if not PER_DAY[0] <= n <= PER_DAY[1]:
            raise ValueError(f"Bitte {PER_DAY[0]} bis {PER_DAY[1]} pro Tag.")
        p["per_day"] = n
    for k, v in keys.items():
        if k in ("app_id", "app_secret", "client_key", "client_secret") and isinstance(v, str) and v.strip():
            v = v.strip()
            if any(c in v for c in "*• "):
                raise ValueError("Bitte den echten Schlüssel einfügen, nicht die verdeckte Anzeige.")
            p[k] = v
    save(d)
    return summary()[platform]


# --- HTTP ---------------------------------------------------------------------

class ApiError(Exception):
    pass


def _req(method, url, data=None, headers=None, body=None, timeout=60):
    headers = dict(headers or {})
    if data is not None:
        if headers.get("Content-Type", "").startswith("application/json"):
            body = json.dumps(data).encode()
        else:
            body = urllib.parse.urlencode(data).encode()
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            j = json.loads(raw or b"{}")
        except ValueError:
            j = {}
        err = j.get("error") or {}
        msg = (err.get("message") if isinstance(err, dict) else None) or j.get("error_description") or raw[:200].decode(errors="ignore")
        raise ApiError(f"{e.code}: {msg}") from None
    return json.loads(raw or b"{}") if raw else {}


# --- Instagram ----------------------------------------------------------------

def ig_connect(app_id, app_secret, short_token):
    """Kurzen Nutzer-Token gegen einen Seiten-Token tauschen, der nicht abläuft, und das Instagram-Konto finden."""
    d = load()
    ig = d["instagram"]
    ig["app_id"] = (app_id or ig["app_id"]).strip()
    ig["app_secret"] = (app_secret or ig["app_secret"]).strip()
    if not (ig["app_id"] and ig["app_secret"] and short_token.strip()):
        raise ValueError("Bitte App-ID, App-Geheimnis und Token einfügen.")
    long = _req("GET", GRAPH + "/oauth/access_token?" + urllib.parse.urlencode({
        "grant_type": "fb_exchange_token", "client_id": ig["app_id"], "client_secret": ig["app_secret"],
        "fb_exchange_token": short_token.strip()}))["access_token"]
    pages = _req("GET", GRAPH + "/me/accounts?" + urllib.parse.urlencode({
        "fields": "name,access_token,instagram_business_account{id,username}", "access_token": long})).get("data", [])
    page = next((p for p in pages if p.get("instagram_business_account")), None)
    if not page:
        raise ValueError("Keine Facebook-Seite mit verbundenem Instagram-Creator-Konto gefunden. "
                         "Instagram muss ein Creator- oder Business-Konto sein und mit der Seite verknüpft.")
    acc = page["instagram_business_account"]
    ig.update(token=page["access_token"], ig_id=acc["id"], username=acc.get("username", ""),
              page=page.get("name", ""), error=None)
    save(d)
    return summary()["instagram"]


def ig_post(video, caption, ig, wait=lambda s: time.sleep(s)):
    """Reel hochladen und veröffentlichen. Gibt die Instagram-Medien-ID zurück."""
    tok, uid = ig["token"], ig["ig_id"]
    c = _req("POST", f"{GRAPH}/{uid}/media", {"media_type": "REELS", "upload_type": "resumable",
                                               "caption": caption[:2200], "share_to_feed": "true",
                                               "access_token": tok})
    cid = c["id"]
    size = os.path.getsize(video)
    with open(video, "rb") as f:
        body = f.read()
    _req("POST", c.get("uri") or f"{RUPLOAD}/{cid}", body=body, timeout=600,
         headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size), "Content-Type": "application/octet-stream"})
    for _ in range(60):  # Meta verarbeitet das Video, meist unter 1 Minute
        st = _req("GET", f"{GRAPH}/{cid}?" + urllib.parse.urlencode({"fields": "status_code,status", "access_token": tok}))
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise ApiError("Instagram konnte das Video nicht verarbeiten: " + str(st.get("status", code)))
        wait(10)
    else:
        raise ApiError("Instagram braucht zu lange für das Video.")
    return _req("POST", f"{GRAPH}/{uid}/media_publish", {"creation_id": cid, "access_token": tok})["id"]


# --- TikTok -------------------------------------------------------------------

def tt_auth_url(redirect_uri, state):
    tt = load()["tiktok"]
    if not (tt["client_key"] and tt["client_secret"]):
        raise ValueError("Bitte zuerst Client Key und Client Secret der TikTok-App speichern.")
    return TT_AUTH + "?" + urllib.parse.urlencode({"client_key": tt["client_key"], "scope": TT_SCOPES,
                                                   "response_type": "code", "redirect_uri": redirect_uri, "state": state})


def _tt_save_token(d, j):
    tt = d["tiktok"]
    tt.update(access=j["access_token"], refresh=j.get("refresh_token") or tt["refresh"],
              expires=time.time() + int(j.get("expires_in", 86400)) - 300, open_id=j.get("open_id", tt["open_id"]), error=None)


def tt_exchange(code, redirect_uri):
    d = load()
    tt = d["tiktok"]
    j = _req("POST", TT_API + "/oauth/token/", {"client_key": tt["client_key"], "client_secret": tt["client_secret"],
                                                "code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri})
    if "access_token" not in j:
        raise ApiError(j.get("error_description") or "TikTok hat keinen Zugang geschickt.")
    _tt_save_token(d, j)
    try:
        u = _req("GET", TT_API + "/user/info/?fields=display_name", headers={"Authorization": "Bearer " + tt["access"]})
        tt["username"] = ((u.get("data") or {}).get("user") or {}).get("display_name", "")
    except ApiError:
        pass
    save(d)
    return summary()["tiktok"]


def tt_access():
    d = load()
    tt = d["tiktok"]
    if tt["access"] and time.time() < tt["expires"]:
        return tt["access"]
    j = _req("POST", TT_API + "/oauth/token/", {"client_key": tt["client_key"], "client_secret": tt["client_secret"],
                                                "grant_type": "refresh_token", "refresh_token": tt["refresh"]})
    if "access_token" not in j:
        raise ApiError("TikTok-Anmeldung abgelaufen. Bitte in der Zentrale neu verbinden.")
    _tt_save_token(d, j)
    save(d)
    return d["tiktok"]["access"]


def tt_draft(video, access):
    """Video als Entwurf in die TikTok-App schicken (Julius postet es dort selbst). Gibt die publish_id zurück."""
    size = os.path.getsize(video)
    init = _req("POST", TT_API + "/post/publish/inbox/video/init/",
                {"source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}},
                headers={"Authorization": "Bearer " + access, "Content-Type": "application/json; charset=UTF-8"})
    data = init.get("data") or {}
    if not data.get("upload_url"):
        raise ApiError(((init.get("error") or {}).get("message")) or "TikTok hat keine Upload-Adresse geschickt.")
    with open(video, "rb") as f:
        body = f.read()
    _req("PUT", data["upload_url"], body=body, timeout=600,
         headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size - 1}/{size}", "Content-Length": str(size)})
    return data.get("publish_id", "")


# --- Auswahl: welcher Short ist dran? ------------------------------------------

def _parse(ts):
    try:
        t = dt.datetime.fromisoformat(ts)
        return t if t.tzinfo else t.replace(tzinfo=store.TZ)
    except (TypeError, ValueError):
        return None


def sent_today(posted, platform, now):
    return sum(1 for u in posted if (_parse((u.get("auto") or {}).get(platform + "_at")) or now - dt.timedelta(days=9)).date() == now.date())


def pick(posted, platform, now, exists=os.path.exists):
    """Der beste Short der letzten 2 Tage (nach Aufrufen), der auf dieser Plattform noch fehlt."""
    best = None
    for u in posted:
        if u.get("kind") == "clip" or u.get("lang") or not u.get("video_id") or u.get("laenge") == "lang":
            continue
        t = _parse(u.get("posted_at"))
        if not t or not (dt.timedelta(hours=MIN_AGE_H) <= now - t <= dt.timedelta(hours=WINDOW_H)):
            continue
        if (u.get("shared") or {}).get(platform) or (u.get("auto") or {}).get(platform):
            continue
        if not exists(store.share_path(u["video_id"])):
            continue
        key = (u.get("views") or 0, u.get("posted_at") or "")
        if best is None or key > best[0]:
            best = (key, u)
    return best[1] if best else None


def due(platform, d, posted, now):
    """Ist jetzt ein automatischer Post für diese Plattform dran? Dann den Short, sonst None."""
    p = d[platform]
    ready = p["token"] and p["ig_id"] if platform == "instagram" else p["refresh"]
    if not (p["on"] and ready and p["per_day"] > 0):
        return None
    if not HOURS[0] <= now.hour < HOURS[1]:
        return None
    last = _parse((p.get("last") or {}).get("at") if isinstance(p.get("last"), dict) else None)
    if last and now - last < dt.timedelta(hours=GAP_H):
        return None
    if sent_today(posted, platform, now) >= p["per_day"]:
        return None
    return pick(posted, platform, now)


def mark(video_id, platform, ref, shared):
    """Merkt sich den automatischen Post beim Upload in state.json."""
    with store.LOCK:
        st = store.state()
        u = next((x for x in st["uploads"] if x.get("video_id") == video_id), None)
        if not u:
            return
        at = store.now().isoformat(timespec="seconds")
        u["auto"] = {**(u.get("auto") or {}), platform: ref, platform + "_at": at}
        if shared:
            u["shared"] = {**(u.get("shared") or {}), platform: at}
        store.write("state.json", st)


def send(platform, u, now=None):
    """Einen Short an Instagram (Reel) oder TikTok (Entwurf) schicken und das Ergebnis merken. Gibt True bei Erfolg."""
    now = now or store.now()
    d = load()
    video = store.share_path(u["video_id"])
    caption = u.get("share") or u.get("title", "")
    name = "Instagram" if platform == "instagram" else "TikTok"
    try:
        if platform == "instagram":
            ref = ig_post(video, caption, d["instagram"])
            mark(u["video_id"], "instagram", ref, shared=True)
            store.log("ok", f"Instagram: „{u.get('title', '')}“ als Reel gepostet.")
        else:
            ref = tt_draft(video, tt_access())
            mark(u["video_id"], "tiktok", ref or "entwurf", shared=False)
            store.log("ok", f"TikTok: „{u.get('title', '')}“ liegt als Entwurf in deiner TikTok-App. "
                            "Dort öffnen, Text einfügen und posten.")
        ok, err = True, None
    except Exception as e:  # nicht abstürzen, nächster Versuch nach GAP_H
        ok, err = False, str(e)[:300]
        store.log("error", f"{name}: Senden fehlgeschlagen: {e}")
    d = load()
    d[platform]["last"] = {"at": now.isoformat(timespec="seconds"), "title": u.get("title", ""), "failed": not ok}
    d[platform]["error"] = err
    save(d)
    return ok


def post_now(platform):
    """Knopf „Jetzt einen senden“: der beste passende Short sofort, ohne Uhrzeit und Abstand."""
    u = pick(store.posted_items(), platform, store.now())
    return send(platform, u) if u else False


def run_once(posted=None, now=None):
    """Einmal nachsehen und höchstens je Plattform einen Short senden. Läuft alle 5 Minuten (server.scheduler)."""
    now = now or store.now()
    posted = posted if posted is not None else store.posted_items()
    for platform in ("instagram", "tiktok"):
        u = due(platform, load(), posted, now)
        if u:
            send(platform, u, now)
