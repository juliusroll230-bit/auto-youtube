"""Verbindet den YouTube-Kanal über den Google-Geräte-Login.

Im Workflow "Kanal verbinden" (Standard):
    python3 connect_channel.py
  schreibt den Code nach content/connect.json (die Website zeigt ihn an), wartet auf die Freigabe
  und speichert den Zugang verschlüsselt in content/channel.enc.

Von Hand:
    python3 connect_channel.py --print CLIENT_ID CLIENT_SECRET
  gibt Code und Refresh-Token im Terminal aus.

Der OAuth-Client muss vom Typ "Fernseher und Geräte mit begrenzter Eingabe" sein.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(HERE, "content", "connect.json")
SCOPE = "https://www.googleapis.com/auth/youtube"


def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def publish_status(status, **extra):
    """Schreibt den Stand nach content/connect.json und pusht ihn, damit die Website ihn sieht."""
    data = {"status": status, "updated_at": now_iso(), **extra}
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    paths = ["content/connect.json"] + [p for p in ("content/channel.enc", "content/channel.json")
                                        if os.path.exists(os.path.join(HERE, p))]
    subprocess.run(["git", "add", *paths], cwd=HERE, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=HERE).returncode:
        subprocess.run(["git", "commit", "-qm", f"Kanal verbinden: {status}"], cwd=HERE, check=True)
        subprocess.run(["git", "pull", "-q", "--rebase"], cwd=HERE, check=True)
        subprocess.run(["git", "push", "-q"], cwd=HERE, check=True)


def device_login(client_id, client_secret, on_code):
    code = post("https://oauth2.googleapis.com/device/code", {"client_id": client_id, "scope": SCOPE})
    if "device_code" not in code:
        raise RuntimeError(f"Google hat keinen Code geliefert: {code.get('error_description') or code}")
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=code.get("expires_in", 1800))
    on_code(code["user_code"], code["verification_url"], expires.replace(microsecond=0).isoformat())
    interval = code.get("interval", 5)
    while dt.datetime.now(dt.timezone.utc) < expires:
        time.sleep(interval)
        tok = post("https://oauth2.googleapis.com/token", {
            "client_id": client_id, "client_secret": client_secret, "device_code": code["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        if "refresh_token" in tok:
            return tok["refresh_token"]
        if tok.get("error") == "slow_down":
            interval += 5
        elif tok.get("error") != "authorization_pending":
            raise RuntimeError(f"Anmeldung abgelehnt: {tok.get('error_description') or tok.get('error')}")
    raise RuntimeError("Der Code ist abgelaufen. Bitte noch einmal auf 'Kanal verbinden' tippen.")


def save_channel_info():
    from fetch_stats import fetch_channel

    info = fetch_channel()
    with open(os.path.join(HERE, "content", "channel.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    return info


def main():
    if "--print" in sys.argv:
        client_id, client_secret = sys.argv[2], sys.argv[3]
        token = device_login(client_id, client_secret,
                             lambda c, url, _: print(f"Öffne {url} und gib diesen Code ein: {c}", flush=True))
        print(f"YT_REFRESH_TOKEN={token}")
        return

    client_id = os.environ.get("YT_CLIENT_ID")
    client_secret = os.environ.get("YT_CLIENT_SECRET")
    if not client_id or not client_secret:
        publish_status("fehler", message="Client-ID oder Clientschlüssel fehlen in den GitHub-Secrets.")
        sys.exit(1)
    try:
        token = device_login(client_id, client_secret,
                             lambda c, url, exp: publish_status("code", user_code=c, verification_url=url, expires_at=exp))
        from yt_auth import encrypt_token
        encrypt_token(token)
        info = save_channel_info()
        publish_status("verbunden", channel_title=info.get("title"))
    except Exception as e:  # der Fehler soll auf der Website sichtbar werden
        publish_status("fehler", message=str(e))
        raise


if __name__ == "__main__":
    main()
