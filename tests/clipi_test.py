"""Prüft die Clipi-Warteschlange: fertige Videos ohne Schneiden, Schnellschnitt-Einstellungen, Sendezeiten.
    python tests/clipi_test.py
"""
import datetime as dt
import io
import os
import subprocess
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="clipi-test-")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agents  # noqa: E402
import clips  # noqa: E402
import store  # noqa: E402

# Sendezeiten: gleichmäßig zwischen 7 und 23 Uhr
assert store.clipi_times(1) == [13 * 60]
t = store.clipi_times(10)
assert len(t) == 10 and t[0] == 7 * 60 and t[-1] == 23 * 60, t
assert len(store.clipi_times(30)) == 30
tz = store.now().tzinfo
at = dt.datetime(2026, 11, 12, 7, 2, tzinfo=tz)
key = store.due_clipi(10, at)
assert key == "2026-11-12-07-00", key
store.mark_slot(key, "clipi_slots")
assert store.due_clipi(10, at) is None
assert store.due_clipi(10, dt.datetime(2026, 11, 12, 6, 0, tzinfo=tz)) is None
store.pause_clipi(dt.datetime(2026, 11, 13, 9, 30, tzinfo=tz))
assert store.due_clipi(10, dt.datetime(2026, 11, 12, 15, 0, tzinfo=tz)) is None  # Tageslimit-Pause
assert store.next_clipi(10, dt.datetime(2026, 11, 12, 15, 0, tzinfo=tz)).startswith("2026-11-13T10:35"), store.clipi_times(10)

# Nachholen: verpasste Plätze von heute kommen dran, aber höchstens einer alle 10 Minuten
st = store.state(); st["clipi_pause"] = None; st["clipi_slots"] = []; store.write("state.json", st)
noon = dt.datetime(2026, 11, 14, 12, 0, tzinfo=tz)
assert store.due_clipi(10, noon) == "2026-11-14-07-00"
store.mark_slot("2026-11-14-07-00", "clipi_slots")
store.clipi_posted(noon)
assert store.due_clipi(10, noon + dt.timedelta(minutes=3)) is None  # Abstand
assert store.due_clipi(10, noon + dt.timedelta(minutes=11)) == "2026-11-14-08-45"
assert store.next_clipi(10, noon + dt.timedelta(minutes=3)).startswith("2026-11-14T12:10")
assert store.due_clipi(10, dt.datetime(2026, 11, 14, 6, 0, tzinfo=tz)) is None

# Einstellung "Clipi pro Tag": Standard 10, höchstens 100
assert agents.settings({})["publisher"]["clipi_per_day"] == 10
assert agents.validate("publisher", {"clipi_per_day": 999})["clipi_per_day"] == 100
assert len(store.clipi_times(100)) == 100 and store.clipi_gap(100) < 10

# Fertiges Video: wird nicht geschnitten, sondern nur umverpackt und gleich freigegeben
src = os.path.join(tempfile.mkdtemp(), "mein_video.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=360x640:d=4:r=30", "-f", "lavfi", "-i",
                "sine=d=4", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", src], check=True)
data = open(src, "rb").read()
c = clips.add_stream(io.BytesIO(data), len(data), "mein_video.mp4", "clipi", True, ready=True)
assert c["status"] == "wartet" and c["ready"]
assert clips.next_job()["id"] == c["id"]
c = clips.process(c["id"], agents.settings({})["clipper"])
assert c["status"] == "fertig" and len(c["clips"]) == 1, c
clip = c["clips"][0]
assert clip["status"] == "freigegeben" and clip["title"] == "mein video", clip
assert os.path.getsize(clips.clip_path(c, clip)) > 1000 and os.path.exists(clips.clip_path(c, clip, "jpg"))
assert not os.path.exists(clips.source_path(c))  # Original gelöscht, Platz gespart

# Läuft nur auf dem Clip-Kanal, nicht zwischen den KI-Shorts
assert clips.ready_clips(auto=True) and not clips.ready_clips(auto=True, main=True)
info = clips.queue_info(10)
assert info["waiting"] == 1 and info["days"] == 1 and info["items"][0]["title"] == "mein video", info
assert not clips.summary()["campaigns"]  # taucht nicht in der Kampagnen-Liste auf
assert store.dashboard()["clipi"]["waiting"] == 1

# Schnellschnitt: kurze Clips (15-25 s), sofort freigegeben, etwa einer pro halbe Minute
q = clips.quick_settings(agents.settings({})["clipper"], 300)
assert (q["min_len"], q["max_len"], q["clips"], q["freigabe"], q["hook"]) == (16, 25, 10, False, True), q
assert clips.quick_settings({}, 12)["clips"] == 1
parts = clips.choose_parts([], [0.5] * 600, 300, {**q, "keywords": ""})
assert len(parts) == 10 and all(14 <= p["end"] - p["start"] <= 25.5 for p in parts), parts

# Lernen: Hook-Arten, Längen, und dass die beste Variante bevorzugt wird
part = [{"text": "Also das hier ist ein ziemlich langer erster Satz über Autos", "s": 0, "e": 3},
        {"text": "Weißt du warum das so ist?", "s": 3, "e": 5}]
assert clips.quick_hook(part, "frage") == ("Weißt du warum das so ist?", "frage")
assert clips.quick_hook(part, "ohne") == ("", "ohne")
assert clips.quick_hook(part, "kurz")[0].endswith("…")
assert clips.quick_hook(part[:1], "frage")[1] == "satz"   # keine Frage da: normaler Satz
assert clips.quick_hook([], "satz") == ("", None)
assert clips.quick_settings({}, 120, "lang")["min_len"] == 25
now = store.now()
ups, stats = [], {}
for i, (hook, views) in enumerate([("satz", 100), ("satz", 120), ("kurz", 900), ("kurz", 1100),
                                   ("frage", 50), ("frage", 60), ("ohne", 10), ("ohne", 20)]):
    vid = f"vid{i}"
    ups.append({"kind": "clip", "video_id": vid, "posted_at": (now - dt.timedelta(days=3)).isoformat(timespec="seconds"),
                "features": {"hook": hook, "untertitel": "pop", "laenge": "mittel"}, "channel": "clips"})
    stats[vid] = {"views": views}
st = store.state()
st["uploads"] = ups
store.write("state.json", st)
store.write("stats.json", {"videos": stats})
sc = clips.learn_scores()
assert sc["hook"]["kurz"]["videos"] == 2
assert [clips.learn_choice("hook", k) for k in range(3)] == ["kurz"] * 3
row = next(r for r in clips.learn_summary() if r["key"] == "hook")
assert row["values"][0]["value"] == "Kurz mit „…“" and row["values"][0]["best"], row
print("Clipi-Warteschlange ok")

# Tagestopf: Clipi lässt dem Hauptkanal seine Plätze frei
import datetime as _dt
cfg_t = {"post_hours": [7, 9, 11, 13, 14, 15, 17, 18, 19, 21]}
now_t = store.now()
st_t = {"uploads": [{"channel": "clips", "posted_at": now_t.isoformat(timespec="seconds")} for _ in range(50)]}
assert store.clipi_room(cfg_t, st_t, now_t) == 100 - 12 - 50
st_t["uploads"] += [{"channel": "clips", "posted_at": now_t.isoformat(timespec="seconds")} for _ in range(38)]
assert store.clipi_room(cfg_t, st_t, now_t) == 0
st_t["uploads"] = [{"posted_at": now_t.isoformat(timespec="seconds")} for _ in range(12)]  # Hauptkanal hat alles gepostet
assert store.clipi_room(cfg_t, st_t, now_t) == 88
print("Tagestopf ok")

# Neue Standardzeiten (5 pro Tag): alte 10 Zeiten werden einmal umgestellt, eigene bleiben
import json as _json
_d = tempfile.mkdtemp()
store.DATA = _d
store.write("config.json", {"post_hours": [7, 9, 11, 13, 14, 15, 17, 18, 19, 21]})
store.init()
assert store.config()["post_hours"] == [8, 11, 13, 16, 18]
store.write("config.json", {"post_hours": [9, 12], "hours_v2": True, "hours_v4": True})
store.init()
assert store.config()["post_hours"] == [9, 12]
print("Zeiten ok")
