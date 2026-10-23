"""YouTube: Anmeldung per Geräte-Code, Upload, Statistiken."""
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request

SCOPE = "https://www.googleapis.com/auth/youtube"


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
            raise RuntimeError("Die Anmeldung wurde bei Google abgelehnt.")
        elif tok.get("error") != "authorization_pending":
            raise RuntimeError(tok.get("error_description") or tok.get("error"))
    raise RuntimeError("Der Code ist abgelaufen. Bitte noch einmal verbinden.")


def client(cfg):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(token=None, refresh_token=cfg["refresh_token"], client_id=cfg["client_id"],
                        client_secret=cfg["client_secret"], token_uri="https://oauth2.googleapis.com/token")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(cfg, video_path, spec):
    from googleapiclient.http import MediaFileUpload

    title = spec["title"]
    if "#shorts" not in title.lower() and len(title) <= 90:
        title += " #shorts"
    body = {
        "snippet": {"title": title[:100], "description": spec.get("description", ""), "tags": spec.get("tags", []),
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
