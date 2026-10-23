"""Postet das nächste Video aus der Warteschlange, wenn ein Sendeplatz fällig ist.

  python3 post_next.py --check    gibt "due=true" oder "due=false" aus (für GitHub Actions)
  python3 post_next.py            rendert und lädt das nächste Video hoch
  python3 post_next.py --force    ignoriert den Zeitplan (für Tests)

Zugang: YT_CLIENT_ID und YT_CLIENT_SECRET, dazu YT_REFRESH_TOKEN oder content/channel.enc (siehe yt_auth.py).
"""
import datetime as dt
import glob
import json
import os
import shutil
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "content", "queue")
POSTED = os.path.join(HERE, "content", "posted")
STATE = os.path.join(HERE, "content", "state.json")
TZ = ZoneInfo("Europe/Berlin")

# Sendeplätze (Uhrzeit in Deutschland). Mittags, nach Schule/Arbeit und abends sind die Shorts-Spitzen.
SLOTS = [int(h) for h in os.environ.get("POST_HOURS", "12,17,20").split(",")]
EARLY_MIN = 20   # so viele Minuten vor dem Sendeplatz darf schon gepostet werden
LATE_MIN = 100   # bis so viele Minuten danach wird ein verpasster Platz nachgeholt


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {"done_slots": [], "uploads": []}


def due_slot(now, state):
    for h in SLOTS:
        slot = now.replace(hour=h, minute=0, second=0, microsecond=0)
        key = slot.strftime("%Y-%m-%d-%H")
        if key in state["done_slots"]:
            continue
        if slot - dt.timedelta(minutes=EARLY_MIN) <= now <= slot + dt.timedelta(minutes=LATE_MIN):
            return key
    return None


def next_script():
    files = sorted(glob.glob(os.path.join(QUEUE, "*.json")))
    return files[0] if files else None


def upload(path, meta):
    from googleapiclient.http import MediaFileUpload

    title = meta["title"]
    if "#shorts" not in title.lower() and len(title) <= 90:
        title += " #shorts"
    body = {
        "snippet": {
            "title": title[:100],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": "27",  # Bildung
            "defaultLanguage": "de",
            "defaultAudioLanguage": "de",
        },
        "status": {
            "privacyStatus": os.environ.get("PRIVACY", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(path, mimetype="video/mp4", chunksize=-1, resumable=True)
    from yt_auth import youtube_client

    request = youtube_client().videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]


def main():
    now = dt.datetime.now(TZ)
    state = load_state()
    force = "--force" in sys.argv
    slot = due_slot(now, state) or (now.strftime("%Y-%m-%d-%H") + "-manuell" if force else None)
    script = next_script()

    if "--check" in sys.argv:
        due = bool(slot and script)
        print(f"due={'true' if due else 'false'}")
        if slot and not script:
            print("Warteschlange ist leer.", file=sys.stderr)
        return

    if not slot:
        print("Kein Sendeplatz fällig.")
        return
    if not script:
        sys.exit("Warteschlange ist leer, es gibt nichts zu posten.")

    from make_short import build_video, load_tts

    spec = json.load(open(script, encoding="utf-8"))
    out_dir = os.path.join(HERE, "out")
    video, _ = build_video(spec, out_dir, load_tts())
    if os.environ.get("DRY_RUN"):
        print(f"Testlauf, nicht hochgeladen: {video}")
        return
    video_id = upload(video, spec)
    print(f"Hochgeladen: https://youtube.com/shorts/{video_id}")

    os.makedirs(POSTED, exist_ok=True)
    shutil.move(script, os.path.join(POSTED, os.path.basename(script)))
    state["done_slots"] = (state["done_slots"] + [slot])[-60:]
    state["uploads"].append({"slot": slot, "slug": spec["slug"], "video_id": video_id, "title": spec["title"]})
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    import build_dashboard
    build_dashboard.main()


if __name__ == "__main__":
    main()
