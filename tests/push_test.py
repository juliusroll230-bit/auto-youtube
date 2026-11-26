"""Push-Nachrichten über ntfy.sh (push.py) mit vorgetäuschtem HTTP: Thema beim Start, nichts ohne Thema oder
ausgeschaltet, Sofort-Meldungen höchstens 1 pro Stunde (gesammelt), Tagesbericht 19 Uhr, Wochenbericht Sonntag 18 Uhr,
Clip über 2 Std. offen, Budget über 80 %, Kampagne beendet, Gewinner, Upload-Fehler. Läuft ohne Netz."""
import datetime as dt
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

import clips  # noqa: E402
import push  # noqa: E402
import store  # noqa: E402
import whop  # noqa: E402

store.init()
calls = []


class FakeHTTP:
    """Statt urllib: prüft, dass genau JSON an https://ntfy.sh/ ginge."""
    def __call__(self, payload):
        json.dumps(payload)  # muss sich als JSON senden lassen (Umlaute, Emoji)
        calls.append(payload)
        return 200


push._send_impl = FakeHTTP()
TZ = store.now().tzinfo

# 1. Thema entsteht beim ersten Start, lang und zufällig
topic = store.config()["ntfy_topic"]
assert topic.startswith("zentrale-") and len(topic) >= 25, topic
assert push.new_topic() != topic

# 2. Ohne Thema oder ausgeschaltet: nichts
store.save_config(ntfy_topic="")
assert push.send("x", "y") is False and not calls
store.save_config(ntfy_topic=topic, ntfy_on=False)
assert push.send("x", "y") is False and not calls
push.tick(now=dt.datetime(2026, 11, 29, 20, 0, tzinfo=TZ))
assert not calls, "ausgeschaltet: auch kein Bericht"
assert push.send("Test", "y", force=True) is True and calls[-1]["topic"] == topic  # Test-Knopf geht immer
calls.clear()
store.save_config(ntfy_on=True, base_url="http://192.168.1.5:8090")

# 3. Sofort-Meldungen: jede Sache einmal, gesammelt, höchstens 1 pro Stunde
t0 = dt.datetime(2026, 11, 26, 12, 0, tzinfo=TZ)
assert push.alert("a", "Upload fehlgeschlagen: Netz weg") is True
assert push.alert("a", "doppelt") is False
assert push.flush(t0) is True and len(calls) == 1
assert calls[0]["title"] == "Upload fehlgeschlagen" and calls[0]["click"] == "http://192.168.1.5:8090/#kampagnen"
push.alert("b", "Eins: x")
push.alert("c", "Zwei: y")
assert push.flush(t0 + dt.timedelta(minutes=30)) is False, "erst nach einer Stunde"
assert push.flush(t0 + dt.timedelta(minutes=61)) is True and len(calls) == 2
assert calls[1]["title"] == "2 Dinge brauchen dich" and "Eins" in calls[1]["message"] and "Zwei" in calls[1]["message"]
assert push.flush(t0 + dt.timedelta(hours=3)) is False, "nichts mehr offen"
calls.clear()

# 4. Upload-Fehler aus dem Protokoll wird vorgemerkt
store.LISTENERS.append(push.on_log)
store.log("error", "Upload fehlgeschlagen: quotaExceeded", agent="publisher", kind="error")
store.log("error", "Etwas anderes", agent="analyst")
pend = store.state()["push"]["pending"]
assert len(pend) == 1 and "quotaExceeded" in pend[0]["text"], pend
store.LISTENERS.remove(push.on_log)

# 5. Kampagnen: Budget über 80 %, beendet; Clip über 2 Std. offen; Gewinner
P1, P2 = "11111111-0000-0000-0000-000000000000", "22222222-0000-0000-0000-000000000000"
store.write("einreichen.json", {"since": "2026-01-01T00:00:00+01:00", "clips": {}})
store.write(whop.FILE, [
    {"id": P1, "url": "u1", "title": "Spiel A", "status": "läuft", "budget_total": 1000, "budget_used": 850,
     "rates": [{"platform": "YouTube", "rate": 2.0, "currency": "$"}]},
    {"id": P2, "url": "u2", "title": "Spiel B", "status": "beendet", "budget_total": 1000, "budget_used": 100, "rates": []}])
c = clips.create("Video A", "whop", rights=True)
now = store.now()
clips.update(c["id"], lambda x: x.update(program=P1, clips=[
    {"n": 1, "title": "Alter Clip", "status": "gepostet", "video_id": "old1", "posted_at": (now - dt.timedelta(hours=3)).isoformat(timespec="seconds")},
    {"n": 2, "title": "Neuer Clip", "status": "gepostet", "video_id": "new1", "posted_at": (now - dt.timedelta(minutes=20)).isoformat(timespec="seconds")}]))
ups = [{"video_id": f"v{i}", "title": f"Short {i}", "posted_at": (now - dt.timedelta(days=2, hours=i)).isoformat(timespec="seconds")} for i in range(10)]
stats = {f"v{i}": {"views": 500} for i in range(10)}
stats["v3"] = {"views": 4000}
store.write("state.json", {**store.state(), "uploads": ups})
store.write("stats.json", {"videos": stats})
push.check_campaigns()
push.check_clips(now)
push.check_winners(now)
texts = " | ".join(x["text"] for x in store.state()["push"]["pending"])
assert "Budget fast aufgebraucht: Spiel A (85 %" in texts, texts
assert "Kampagne beendet: Spiel B" in texts, texts
assert "„Alter Clip“" in texts and "Neuer Clip" not in texts, texts
assert "Gewinner erkannt: „Short 3“ hat 4.000 Aufrufe, 8,0×" in texts, texts
n = len(store.state()["push"]["pending"])
push.check_campaigns(); push.check_clips(now); push.check_winners(now)
assert len(store.state()["push"]["pending"]) == n, "jede Meldung nur einmal"

# 6. Tagesbericht um 19 Uhr (einmal am Tag), Wochenbericht Sonntag 18 Uhr (einmal pro Woche)
store.write("channel.json", {"subscribers": 312})
state = store.state()
state["push"]["pending"] = []
store.write("state.json", state)
calls.clear()
sun = dt.datetime(2026, 11, 29, 17, 30, tzinfo=TZ)   # Sonntag
reports = lambda: [x for x in calls if "bericht" in x["title"]]
push.tick(now=sun)
assert not reports(), "vor 18 Uhr kein Bericht"
assert [x["title"] for x in calls] == ["Clip seit über 2 Stunden nicht eingereicht"], "der neue Clip ist inzwischen über 2 Std. offen"
push.tick(now=sun.replace(hour=18, minute=5))
assert [x["title"] for x in reports()] == ["Wochenbericht 29.11.: Weg zum Partnerprogramm"], [x["title"] for x in calls]
week = reports()[0]["message"]
assert "Abos: 312 von 1.000 (31 %)" in week and "Wiedergabezeit: unbekannt" in week and "4.000" in week, week
assert "Ab 01.02.2027" in week and "AdSense" in week, week
push.tick(now=sun.replace(hour=19, minute=1))
assert calls[-1]["title"] == "Tagesbericht 29.11." and calls[-1]["click"].endswith("#kampagnen"), calls[-1]
assert "Abonnenten: 312" in calls[-1]["message"] and "Offen zum Einreichen" in calls[-1]["message"], calls[-1]["message"]
n = len(calls)
push.tick(now=sun.replace(hour=21))
assert len(calls) == n, "Berichte nur einmal"
store.save_config(ntfy_hour=20)
push.tick(now=dt.datetime(2026, 11, 30, 19, 30, tzinfo=TZ))
assert len(calls) == n, "eingestellte Uhrzeit 20 Uhr"
push.tick(now=dt.datetime(2026, 11, 30, 20, 0, tzinfo=TZ))
assert calls[-1]["title"] == "Tagesbericht 30.11."

# 7. Ab Februar 2027 doppelte Schwellen
assert push.ypp_rule(dt.date(2027, 1, 31))[1]["hours"] == 4000
assert push.ypp_rule(dt.date(2027, 2, 1))[1]["hours"] == 8000 and push.ypp_rule(dt.date(2027, 2, 1))[1]["shorts"] == 20_000_000

# 8. QR-Code als SVG
svg = push.qr_svg(push.subscribe_url(topic))
assert svg.startswith(b"<?xml") or b"<svg" in svg[:200]

print("push ok")
