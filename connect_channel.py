"""Verbindet einen YouTube-Kanal über den Google-Geräte-Login und gibt den Refresh-Token aus.

  python3 connect_channel.py CLIENT_ID CLIENT_SECRET

Der OAuth-Client muss in der Google Cloud Console vom Typ "Fernseher und Geräte mit begrenzter Eingabe" sein.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

SCOPE = "https://www.googleapis.com/auth/youtube"


def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


def main():
    client_id, client_secret = sys.argv[1], sys.argv[2]
    code = post("https://oauth2.googleapis.com/device/code", {"client_id": client_id, "scope": SCOPE})
    if "device_code" not in code:
        sys.exit(f"Fehler: {code}")
    print(f"Öffne {code['verification_url']} und gib diesen Code ein: {code['user_code']}", flush=True)
    interval = code.get("interval", 5)
    deadline = time.time() + code.get("expires_in", 1800)
    while time.time() < deadline:
        time.sleep(interval)
        tok = post("https://oauth2.googleapis.com/token", {
            "client_id": client_id, "client_secret": client_secret, "device_code": code["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        if "refresh_token" in tok:
            print("Verbunden.")
            print(f"YT_REFRESH_TOKEN={tok['refresh_token']}")
            return
        if tok.get("error") == "slow_down":
            interval += 5
        elif tok.get("error") != "authorization_pending":
            sys.exit(f"Fehler: {tok}")
    sys.exit("Der Code ist abgelaufen, bitte neu starten.")


if __name__ == "__main__":
    main()
