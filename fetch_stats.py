"""Holt Aufrufe, Likes und Kommentare der geposteten Videos und die Kanal-Daten.

Schreibt content/stats.json und content/channel.json, danach content/dashboard.json neu.
"""
import datetime as dt
import json
import os

from yt_auth import youtube_client

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "content")


def fetch_channel(yt=None):
    yt = yt or youtube_client()
    items = yt.channels().list(part="snippet,statistics", mine=True).execute().get("items", [])
    if not items:
        raise RuntimeError("Für dieses Google-Konto wurde kein YouTube-Kanal gefunden.")
    ch = items[0]
    thumbs = ch["snippet"].get("thumbnails", {})
    return {
        "id": ch["id"],
        "title": ch["snippet"]["title"],
        "handle": ch["snippet"].get("customUrl", ""),
        "thumbnail": (thumbs.get("medium") or thumbs.get("default") or {}).get("url", ""),
        "subscribers": int(ch["statistics"].get("subscriberCount", 0)),
        "views": int(ch["statistics"].get("viewCount", 0)),
        "videos": int(ch["statistics"].get("videoCount", 0)),
    }


def fetch_videos(yt, ids):
    out = {}
    for i in range(0, len(ids), 50):
        resp = yt.videos().list(part="statistics,status", id=",".join(ids[i:i + 50])).execute()
        for v in resp.get("items", []):
            s = v.get("statistics", {})
            out[v["id"]] = {
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
                "privacy": v.get("status", {}).get("privacyStatus", ""),
            }
    return out


def main():
    yt = youtube_client()
    state_path = os.path.join(CONTENT, "state.json")
    state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {"uploads": []}
    ids = [u["video_id"] for u in state["uploads"]]
    stats = {"updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
             "videos": fetch_videos(yt, ids) if ids else {}}
    json.dump(stats, open(os.path.join(CONTENT, "stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(fetch_channel(yt), open(os.path.join(CONTENT, "channel.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    import build_dashboard
    build_dashboard.main()


if __name__ == "__main__":
    main()
