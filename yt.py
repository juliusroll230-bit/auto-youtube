"""YouTube: Anmeldung per Geräte-Code, Upload, Statistiken."""
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request

SCOPE = "https://www.googleapis.com/auth/youtube"


def is_expired(error):
    """True, wenn Google den gespeicherten Zugang nicht mehr annimmt (z. B. nach 7 Tagen im Testmodus)."""
    from google.auth.exceptions import RefreshError
    return isinstance(error, RefreshError) and "invalid_grant" in str(error)


def _post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


def device_start(client_id):
    code = _post("https://oauth2.googleapis.com/device/code", {"client_id": client_id, "scope": SCOPE})
    if "device_code" not in code:
        if code.get("error") in ("invalid_client", "unauthorized_client"):
            raise RuntimeError("Google kennt diese Client-ID nicht. Bitte die Client-ID aus Google Cloud → Clients "
                               "neu kopieren. Der Client muss vom Typ „Fernseher und Geräte mit begrenzter Eingabe“ sein.")
        raise RuntimeError(code.get("error_description") or code.get("error") or "Google hat keinen Code geliefert.")
    code["expires_at"] = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=code.get("expires_in", 1800))).isoformat()
    return code


def device_wait(client_id, client_secret, code):
    """Wartet, bis der Code auf google.com/device bestätigt wurde, und gibt den Refresh-Token zurück."""
    interval = code.get("interval", 5)
    deadline = time.time() + code.get("expires_in", 1800)
    while time.time() < deadline:
        time.sleep(interval)
        tok = _post("https://oauth2.googleapis.com/token", {
            "client_id": client_id, "client_secret": client_secret, "device_code": code["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        if "refresh_token" in tok:
            return tok["refresh_token"]
        if tok.get("error") == "slow_down":
            interval += 5
        elif tok.get("error") == "access_denied":
            raise RuntimeError("Google hat die Anmeldung abgelehnt. Steht das Google-Konto deines Kanals in "
                               "Google Cloud unter Zielgruppe → Testnutzer? Dann einfach nochmal verbinden.")
        elif tok.get("error") == "invalid_client":
            raise RuntimeError("Client-ID und Clientschlüssel passen nicht zusammen. In Google Cloud → Clients → "
                               "deinen Client öffnen, „Secret hinzufügen“ klicken und Client-ID plus neuen "
                               "Schlüssel (beginnt mit GOCSPX-) hier eintragen.")
        elif tok.get("error") != "authorization_pending":
            raise RuntimeError(tok.get("error_description") or tok.get("error"))
    raise RuntimeError("Der Code ist abgelaufen. Bitte noch einmal verbinden.")


def _credentials(cfg):
    from google.oauth2.credentials import Credentials

    return Credentials(token=None, refresh_token=cfg["refresh_token"], client_id=cfg["client_id"],
                       client_secret=cfg["client_secret"], token_uri="https://oauth2.googleapis.com/token")


def check(cfg):
    """Prüft vor der Arbeit, ob der Zugang noch gilt. Wirft RefreshError, wenn nicht."""
    from google.auth.transport.requests import Request

    _credentials(cfg).refresh(Request())


def client(cfg):
    from googleapiclient.discovery import build

    return build("youtube", "v3", credentials=_credentials(cfg), cache_discovery=False)


FOOTER = ("🔔 Abonnieren für täglich neue Fakten!\n"
          "Erstellt mit KI-Stimme und eigenen Animationen.")


def upload(cfg, video_path, spec):
    from googleapiclient.http import MediaFileUpload

    title = spec["title"]
    description = spec.get("description", "").rstrip()
    if FOOTER.splitlines()[0] not in description:
        description += "\n\n" + FOOTER
    if "#shorts" not in title.lower() and len(title) <= 90:
        title += " #shorts"
    body = {
        "snippet": {"title": title[:100], "description": description[:4900], "tags": spec.get("tags", []),
                    "categoryId": "27", "defaultLanguage": "de", "defaultAudioLanguage": "de"},
        "status": {"privacyStatus": cfg.get("privacy", "public"), "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", chunksize=-1, resumable=True)
    request = client(cfg).videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]


def channel(cfg):
    items = client(cfg).channels().list(part="snippet,statistics", mine=True).execute().get("items", [])
    if not items:
        raise RuntimeError("Für dieses Google-Konto gibt es keinen YouTube-Kanal.")
    ch = items[0]
    thumbs = ch["snippet"].get("thumbnails", {})
    return {
        "id": ch["id"], "title": ch["snippet"]["title"], "handle": ch["snippet"].get("customUrl", ""),
        "thumbnail": (thumbs.get("medium") or thumbs.get("default") or {}).get("url", ""),
        "subscribers": int(ch["statistics"].get("subscriberCount", 0)),
        "views": int(ch["statistics"].get("viewCount", 0)),
        "videos": int(ch["statistics"].get("videoCount", 0)),
    }


def video_stats(cfg, ids):
    yt, out = client(cfg), {}
    for i in range(0, len(ids), 50):
        for v in yt.videos().list(part="statistics,status", id=",".join(ids[i:i + 50])).execute().get("items", []):
            s = v.get("statistics", {})
            out[v["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                            "comments": int(s.get("commentCount", 0)),
                            "privacy": v.get("status", {}).get("privacyStatus", "")}
    return out


def set_branding(cfg, banner_path, description, keywords):
    """Lädt das Kanalbanner hoch und setzt Beschreibung und Stichwörter.

    Das Profilbild lässt sich über die YouTube-Schnittstelle nicht ändern, das geht nur in YouTube Studio.
    """
    from googleapiclient.http import MediaFileUpload

    yt = client(cfg)
    media = MediaFileUpload(banner_path, mimetype="image/jpeg", resumable=False)
    banner_url = yt.channelBanners().insert(media_body=media).execute()["url"]
    ch = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]
    # Beim Speichern ersetzt YouTube alle brandingSettings, darum die bestehenden übernehmen
    branding = ch.get("brandingSettings", {})
    channel_settings = {**branding.get("channel", {}), "description": description, "keywords": keywords}
    channel_settings.setdefault("defaultLanguage", "de")
    channel_settings.setdefault("country", "DE")
    body = {"id": ch["id"], "brandingSettings": {"channel": channel_settings,
                                                 "image": {"bannerExternalUrl": banner_url}}}
    yt.channels().update(part="brandingSettings", body=body).execute()
