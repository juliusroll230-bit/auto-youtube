"""Zugang zur YouTube API.

Der Refresh-Token kommt entweder aus YT_REFRESH_TOKEN oder aus content/channel.enc.
Diese Datei schreibt der Workflow "Kanal verbinden"; sie ist mit YT_CLIENT_SECRET verschlüsselt.
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(HERE, "content", "channel.enc")


def encrypt_token(token):
    out = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-a", "-pass", "env:YT_CLIENT_SECRET"],
        input=token.encode(), capture_output=True, check=True,
    )
    with open(TOKEN_FILE, "wb") as f:
        f.write(out.stdout)


def refresh_token():
    if os.environ.get("YT_REFRESH_TOKEN"):
        return os.environ["YT_REFRESH_TOKEN"]
    if not os.path.exists(TOKEN_FILE):
        raise SystemExit("Kein Kanal verbunden. Starte den Workflow 'Kanal verbinden'.")
    out = subprocess.run(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-a", "-pass", "env:YT_CLIENT_SECRET", "-in", TOKEN_FILE],
        capture_output=True, check=True,
    )
    return out.stdout.decode().strip()


def youtube_client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=refresh_token(),
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)
