"""Instagram/TikTok automatisch: Auswahl des besten Shorts, Zeitfenster, Tageslimit, Ablauf der Uploads (ohne Netz)."""
import datetime as dt
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import social  # noqa: E402
import store  # noqa: E402

now = dt.datetime(2026, 11, 20, 15, 0, tzinfo=store.TZ)


def item(vid, views, hours_ago, **kw):
    return {"video_id": vid, "title": "T " + vid, "views": views, "share": "Text " + vid,
            "posted_at": (now - dt.timedelta(hours=hours_ago)).isoformat(timespec="seconds"), **kw}


yes = lambda p: True  # noqa: E731
posted = [
    item("a", 900, 10),
    item("b", 2600, 20),                                   # bester
    item("c", 5000, 60),                                   # zu alt
    item("d", 9000, 1),                                    # zu frisch
    item("e", 8000, 10, kind="clip"),                      # Clipi
    item("f", 7000, 10, lang=True),                        # langes Video
    item("g", 6000, 10, shared={"instagram": "x"}),        # schon von Hand geteilt
]
assert social.pick(posted, "instagram", now, yes)["video_id"] == "b"
assert social.pick(posted, "tiktok", now, yes)["video_id"] == "g"  # TikTok-Haken fehlt dort noch
assert social.pick(posted, "instagram", now, lambda p: not p.endswith("b.mp4"))["video_id"] == "a"
posted[1]["auto"] = {"instagram": "123", "instagram_at": now.isoformat()}
assert social.pick(posted, "instagram", now, yes)["video_id"] == "a"
assert social.sent_today(posted, "instagram", now) == 1
assert social.sent_today(posted, "tiktok", now) == 0
del posted[1]["auto"]

# due(): an, verbunden, Uhrzeit, Abstand, Tageslimit
d = social.load()
assert social.due("instagram", d, posted, now) is None  # aus
d["instagram"].update(on=True, token="tok", ig_id="17841")
social.pick, real_pick = (lambda p, pl, n, exists=None: real_pick(p, pl, n, yes)), social.pick
assert social.due("instagram", d, posted, now)["video_id"] == "b"
assert social.due("instagram", d, posted, now.replace(hour=9)) is None          # vor 12 Uhr
assert social.due("instagram", d, posted, now.replace(hour=22)) is None         # ab 22 Uhr
d["instagram"]["last"] = {"at": (now - dt.timedelta(hours=1)).isoformat()}
assert social.due("instagram", d, posted, now) is None                           # Abstand 3 h
d["instagram"]["last"] = {"at": (now - dt.timedelta(hours=4)).isoformat()}
assert social.due("instagram", d, posted, now)["video_id"] == "b"
d["instagram"]["per_day"] = 1
posted[0]["auto"] = {"instagram": "1", "instagram_at": now.replace(hour=12).isoformat()}
assert social.due("instagram", d, posted, now) is None                           # Tageslimit
del posted[0]["auto"]
assert social.due("tiktok", d, posted, now) is None                              # nicht verbunden
d["tiktok"].update(on=True, refresh="r")
assert social.due("tiktok", d, posted, now)["video_id"] == "g"
social.pick = real_pick

# Instagram-Ablauf mit gefälschtem Netz
vid = tempfile.mktemp(suffix=".mp4")
with open(vid, "wb") as f:
    f.write(b"x" * 1234)
calls = []
status = iter(["IN_PROGRESS", "FINISHED"])


def fake(method, url, data=None, headers=None, body=None, timeout=60):
    calls.append((method, url, data, headers, body))
    if url.endswith("/media"):
        return {"id": "C1", "uri": "https://rupload.facebook.com/ig-api-upload/v21.0/C1"}
    if "rupload" in url:
        return {"success": True}
    if "/C1?" in url:
        return {"status_code": next(status)}
    if url.endswith("/media_publish"):
        return {"id": "M9"}
    if "/oauth/access_token" in url:
        return {"access_token": "LONG"}
    if "/me/accounts" in url:
        return {"data": [{"name": "Ohne IG", "access_token": "X"},
                         {"name": "60 Sekunden Wissen", "access_token": "PAGE",
                          "instagram_business_account": {"id": "17841", "username": "60sekundenwissen"}}]}
    if url.endswith("/oauth/token/"):
        return {"access_token": "TA", "refresh_token": "TR", "expires_in": 86400, "open_id": "o1"}
    if "/user/info/" in url:
        return {"data": {"user": {"display_name": "Julius"}}}
    if url.endswith("/inbox/video/init/"):
        return {"data": {"publish_id": "P7", "upload_url": "https://open-upload.tiktokapis.com/up/1"}}
    if url.startswith("https://open-upload"):
        return {}
    raise AssertionError(url)


social._req = fake
assert social.ig_post(vid, "Text #shorts", {"token": "PAGE", "ig_id": "17841"}, wait=lambda s: None) == "M9"
up = next(c for c in calls if "rupload" in c[1])
assert up[3]["file_size"] == "1234" and up[3]["Authorization"] == "OAuth PAGE" and len(up[4]) == 1234
assert calls[0][2]["media_type"] == "REELS" and calls[0][2]["upload_type"] == "resumable"

# Verbinden: Seite mit Instagram-Konto wird gefunden, Geheimnisse nicht im summary
s = social.ig_connect("111", "geheim", "KURZ")
assert s["connected"] and s["username"] == "60sekundenwissen" and s["page"] == "60 Sekunden Wissen"
assert "geheim" not in str(social.summary()) and "PAGE" not in str(social.summary())
assert social.load()["instagram"]["token"] == "PAGE"

# TikTok: Anmeldung, Entwurf
social.set_settings("tiktok", client_key="ck", client_secret="cs")
assert "client_key=ck" in social.tt_auth_url("https://x/oauth.html", "tt-abc")
t = social.tt_exchange("CODE", "https://x/oauth.html")
assert t["connected"] and t["username"] == "Julius"
assert social.tt_access() == "TA"
calls.clear()
assert social.tt_draft(vid, "TA") == "P7"
put = next(c for c in calls if c[0] == "PUT")
assert put[3]["Content-Range"] == "bytes 0-1233/1234"

# send(): merkt sich den Post beim Upload, Instagram setzt den Haken, TikTok nicht
st = store.state()
st["uploads"] = [{"video_id": "b", "title": "Schlaf"}]
store.write("state.json", st)
social.store.share_path = lambda v: vid
status = iter(["FINISHED"])
assert social.send("instagram", {"video_id": "b", "title": "Schlaf", "share": "Text"}, now)
u = store.state()["uploads"][0]
assert u["auto"]["instagram"] == "M9" and u["shared"]["instagram"]
assert social.send("tiktok", {"video_id": "b", "title": "Schlaf"}, now)
u = store.state()["uploads"][0]
assert u["auto"]["tiktok"] == "P7" and "tiktok" not in u["shared"]
assert social.load()["tiktok"]["last"]["failed"] is False


# Fehler: nicht abstürzen, Fehler merken
def broken(*a, **k):
    raise social.ApiError("400: Token ungültig")


social._req = broken
assert not social.send("instagram", {"video_id": "b", "title": "Schlaf"}, now)
assert "Token" in social.load()["instagram"]["error"]
assert social.load()["instagram"]["last"]["failed"] is True
print("social ok")
