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

# Einstellung "Clipi pro Tag": Standard 10, höchstens 30
assert agents.settings({})["publisher"]["clipi_per_day"] == 10
assert agents.validate("publisher", {"clipi_per_day": 99})["clipi_per_day"] == 30

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
assert (q["min_len"], q["max_len"], q["clips"], q["freigabe"], q["hook"]) == (15, 25, 10, False, True), q
assert clips.quick_settings({}, 12)["clips"] == 1
parts = clips.choose_parts([], [0.5] * 600, 300, {**q, "keywords": ""})
assert len(parts) == 10 and all(14 <= p["end"] - p["start"] <= 25.5 for p in parts), parts
print("Clipi-Warteschlange ok")
