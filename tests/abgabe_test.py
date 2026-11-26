"""Plätze ab Nr. X an Clipi (abgabe.py): Reihenfolge nach YouTube-Rate × Restbudget, Prüfungen, Upload auf Clipi,
Platz bleibt beim Hauptkanal ohne passenden Clip, Vergleich nach 14 Tagen. Läuft ohne Netz und ohne YouTube."""
import datetime as dt
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import abgabe  # noqa: E402
import clips  # noqa: E402
import store  # noqa: E402
import whop  # noqa: E402

store.init()
store.save_config(post_hours=list(range(8, 23)), post_hours_weekend=list(range(8, 23)), clip_token="clip-token", refresh_token="main-token")
cfg = store.config()


def camp(pid, rate=2.0, total=1000.0, used=200.0, status="läuft", rules=True, banned=()):
    x = {"id": pid, "url": "https://contentrewards.com/c/campaigns/" + pid, "title": "Kampagne " + pid[:2], "currency": "$",
         "rates": [{"platform": "YouTube", "rate": rate, "currency": "$"}] if rate else [{"platform": "TikTok", "rate": 1.0, "currency": "$"}],
         "budget_total": total, "budget_used": used, "status": status, "min_payout": None, "max_payout": None}
    if rules:
        x["rules"] = {"caption": "#werbung\n#partner", "screen_text": "", "min_len": 10, "language": "", "banned": list(banned)}
    return x


def pid(n):
    return f"{n:02d}000000-0000-0000-0000-000000000000"


camps = [camp(pid(1), rate=2.0, total=1000, used=200),          # Wert 2 × 800 = 1.600
         camp(pid(2), rate=3.0, total=1000, used=950),          # 5 % übrig: raus
         camp(pid(3), status="pausiert"),                       # läuft nicht: raus
         camp(pid(4), rate=None),                               # keine YouTube-Rate: raus
         camp(pid(5), rules=False),                             # Vorgaben fehlen: raus
         camp(pid(6), rate=1.0, total=10000, used=0, banned=["gratis"])]  # Wert 10.000, ein Clip mit verbotenem Wort
store.write(whop.FILE, camps)


def video(program, titles):
    c = clips.create("Video " + program[:2], "whop", rights=True)

    def setup(x):
        x["program"] = program
        x["clips"] = [{"n": i + 1, "title": t, "text": t, "status": "freigegeben", "duration": d} for i, (t, d) in enumerate(titles)]
    clips.update(c["id"], setup)
    c = clips.load(c["id"])
    for k in c["clips"]:
        os.makedirs(os.path.dirname(clips.clip_path(c, k)), exist_ok=True)
        open(clips.clip_path(c, k), "wb").write(b"mp4")
    return c


v1 = video(pid(1), [("Zwerg im Schnee", 20)])
for p in (2, 3, 4, 5):
    video(pid(p), [("Clip " + str(p), 20)])
v6 = video(pid(6), [("Jetzt gratis spielen", 20), ("Zu kurz", 6), ("Die Mine", 25)])

# 1. Platznummer: 8 Uhr ist Platz 1, 18 Uhr Platz 11
assert abgabe.slot_number(cfg, "2026-11-26-08") == 1
assert abgabe.slot_number(cfg, "2026-11-26-18") == 11
assert abgabe.slot_number(cfg, "2026-11-26-07") == 0

# 2. Reihenfolge und Prüfungen
found, skipped = abgabe.candidates()
titles = [k["title"] for _, k, _ in found]
assert titles == ["Die Mine", "Zwerg im Schnee"], titles
why = " | ".join(skipped.values())
for text in ("10 % Budget", "läuft nicht", "keine YouTube-Rate", "Vorgaben fehlen", "verbotenes Wort", "kürzer als 10 s"):
    assert text in why, (text, skipped)

# 3. Nur ab Platz 11, nur mit Clip-Kanal, 0 = aus
assert abgabe.choose("2026-11-26-17", cfg) is None
assert abgabe.choose("2026-11-26-18", cfg)[1]["title"] == "Die Mine"
assert abgabe.choose("2026-11-26-18", {**cfg, "clip_token": ""}) is None
store.save_config(agents={"publisher": {"abgabe_ab": 0}})
assert abgabe.choose("2026-11-26-22") is None
store.save_config(agents={"publisher": {"abgabe_ab": 11}})

# 4. Upload: Clipi lädt hoch, Platz ist erledigt, Eintrag mit abgabe und Platznummer, Clip in der Einreich-Station
import server  # noqa: E402

ups = []
server.yt.check = lambda c: None
server.yt.upload = lambda c, path, spec: (ups.append((c["refresh_token"], spec)), "vidABGABE")[1]
server.refresh_stats = lambda *a, **k: None
assert server.post_abgabe("2026-11-26-18") is True
assert ups[0][0] == "clip-token", "muss auf Clipi hochladen, nicht auf den Hauptkanal"
assert ups[0][1]["description"].startswith("#werbung"), "Pflicht-Text der Kampagne"
st = store.state()
rec = st["uploads"][-1]
assert rec["abgabe"] and rec["slot_nr"] == 11 and rec["channel"] == "clips" and rec["video_id"] == "vidABGABE", rec
assert "2026-11-26-18" in st["done_slots"]
import einreichen  # noqa: E402
assert einreichen.overview()["open"] == 1

# 5. Ohne passenden Clip bleibt der Platz beim Hauptkanal
for c in clips.all_campaigns():
    clips.update(c["id"], lambda x: [k.update(status="abgelehnt") for k in x["clips"] if k["status"] == "freigegeben"])
assert server.post_abgabe("2026-11-26-19") is False
assert "2026-11-26-19" not in store.state()["done_slots"]

# 6. Anzeige und Vergleich nach 14 Tagen
ov = abgabe.overview(store.config(), store.state())
assert ov["on"] and ov["from"] == 11 and ov["total"] == 1 and ov["ready"] == 0 and len(ov["slots"]) == 5, ov
start = dt.date(2026, 11, 1)
uploads = [{"abgabe": True, "kind": "clip", "channel": "clips", "posted_at": "2026-11-01T18:00:00", "video_id": "c1", "slot": "2026-11-01-18", "campaign": v1["id"]},
           {"kind": None, "posted_at": "2026-10-25T19:00:00", "video_id": "m1", "slot": "2026-10-25-19"},   # Platz 12: zählt
           {"kind": None, "posted_at": "2026-10-25T09:00:00", "video_id": "m2", "slot": "2026-10-25-09"}]   # Platz 2: zählt nicht
stats = {"c1": {"views": 5000}, "m1": {"views": 100}, "m2": {"views": 900}}
early = abgabe.compare(store.config(), uploads, stats, today=start + dt.timedelta(days=5))
assert early["ready"] is False and early["ready_on"] == "2026-11-15"
cmp_ = abgabe.compare(store.config(), uploads, stats, today=start + dt.timedelta(days=14))
assert cmp_["ready"] and cmp_["clips"]["avg"] == 5000 and cmp_["main"]["n"] == 1 and cmp_["main"]["avg"] == 100, cmp_
assert cmp_["clips"]["money"] == 10.0, cmp_   # 5.000 Aufrufe × 2 $ pro 1.000

print("abgabe ok")
