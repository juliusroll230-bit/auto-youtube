"""Vorbilder: Feed lesen, Trend nach Aufrufen pro Tag, Titel-Muster und Tipps."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import vorbilder  # noqa: E402

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <entry><yt:videoId>aaaaaaaaaaa</yt:videoId><title>How Stitches Work \xf0\x9f\x98\xaf #shorts</title>
  <link rel="alternate" href="https://www.youtube.com/shorts/aaaaaaaaaaa"/><published>2026-11-19T12:00:00+00:00</published>
  <media:group><media:community><media:statistics views="200000"/></media:community></media:group></entry>
 <entry><yt:videoId>bbbbbbbbbbb</yt:videoId><title>Why Is The Sky Blue?</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=bbbbbbbbbbb"/><published>2026-11-10T12:00:00+00:00</published>
  <media:group><media:community><media:statistics views="500000"/></media:community></media:group></entry>
</feed>"""

NOW = dt.datetime(2026, 11, 20, 12, 0, tzinfo=dt.timezone.utc)


def test_parse():
    v = vorbilder.parse(XML)
    assert v[0]["title"] == "How Stitches Work \U0001F62F" and v[0]["short"] and v[0]["views"] == 200000
    assert not v[1]["short"]


def test_build_trend_and_tips():
    vids = vorbilder.parse(XML)
    feeds = {c["id"]: None for c in vorbilder.CHANNELS}
    feeds[vorbilder.CHANNELS[0]["id"]] = vids
    ours = ["Das Lied, das aus dem leeren Zimmer kommt und niemand weiß warum"] * 6
    d = vorbilder.build(feeds, ours, NOW)
    assert d["trend"][0]["id"] == "aaaaaaaaaaa"          # 200k an 1 Tag schlägt 500k in 10 Tagen
    assert d["trend"][0]["per_day"] == 200000
    assert d["channels"][0]["ok"] and not d["channels"][1]["ok"]
    assert d["muster"]["question"] == 50 and d["muster"]["emoji"] == 50
    assert any("Kürzere Titel" in t for t in d["tips"])
    assert "clippen" in d["regel"]


def test_fetch_all_survives_errors():
    def boom(cid):
        raise OSError("weg")
    feeds = vorbilder.fetch_all(boom)
    assert all(v is None for v in feeds.values()) and len(feeds) == len(vorbilder.CHANNELS)


def test_due():
    assert vorbilder.due({})
    fresh = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")}
    assert not vorbilder.due(fresh)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
