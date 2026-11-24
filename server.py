"""Shorts-Zentrale: Website, Zeitplan und Uploads in einem Prozess.

  python3 server.py        startet auf Port 8080 (änderbar mit PORT)

Umgebungsvariablen:
  DATA_DIR       Speicherort (Standard ./data, im Container /data)
  PASSWORD       optional: schützt die Website mit Benutzer "admin" und diesem Passwort
  SCRIPTS_REPO   optional: GitHub-Repo, aus dem neue Skripte geholt werden (z. B. name/auto-youtube)
  GITHUB_TOKEN   optional: nur nötig, wenn dieses Repo privat ist
  OAUTH_PAGE     optional: Weiterleitungsseite für die Zuschauer-Daten
                 (Standard: https://<besitzer>.github.io/<repo>/oauth.html aus SCRIPTS_REPO)

Video-Webhook (für Kampagnen): POST /webhook/video mit dem Schlüssel aus dem Bereich Kampagnen
  (Header X-Webhook-Token oder ?token=...). Entweder die Videodatei als Body (…?name=Titel&rights=1)
  oder JSON {"url": "http://…/video.mp4", "name": "…", "credit": "@kanal", "rights": true}
  bzw. {"file": "datei.mp4"} für ein Video, das schon im Eingangsordner liegt.
"""
import base64
import datetime as dt
import glob
import json
import os
import random
import re
import secrets
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import agents
import clips
import comments
import learn
import money
import social
import vorbilder
import store
import whop
import yt

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
PAGE_HEAD = ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
             '<link rel="icon" href="icon.png"><link rel="apple-touch-icon" href="icon.png">'
             '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);'
             'padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui}'
             'img{max-width:100%}[hidden]{display:none!important}</style></head><body>')
PORT = int(os.environ.get("PORT", "8080"))
PASSWORD = os.environ.get("PASSWORD", "")
SCRIPTS_REPO = os.environ.get("SCRIPTS_REPO", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
OAUTH_PAGE = os.environ.get("OAUTH_PAGE", "").strip() or (
    "https://{}.github.io/{}/oauth.html".format(*SCRIPTS_REPO.split("/", 1)) if "/" in SCRIPTS_REPO else "")
VERSION = {"sha": os.environ.get("APP_VERSION", "dev")[:7], "built": os.environ.get("APP_BUILT", "")}

work_lock = threading.Lock()   # es läuft immer nur ein Upload gleichzeitig
thumb_lock = threading.Lock()  # Thumbnails nacheinander bauen (Chromium)
relax_waiting = threading.Event()  # Quiet Corner wartet auf den Renderer: andere Aufgaben lassen ihn frei
relax_lock = threading.Lock()  # Entspannungskanal: baut und lädt ein langes Video, unabhängig vom Hauptkanal
clipi_lock = threading.Lock()  # Clipi lädt auf den eigenen Clip-Kanal hoch, unabhängig vom Hauptkanal
status = {"busy": "", "connect": {"status": "idle"}, "connect_clip": {"status": "idle"}, "connect_relax": {"status": "idle"}, "oauth_states": {}}
_tts = None
_tts_lock = threading.Lock()

# Live-Ansicht der Zentrale: wer gerade arbeitet (mit Aufgabe für die Sprechblase) und die letzten Ereignisse.
# Die Website fragt alle paar Sekunden /api/live?since=<seq> und animiert, was neu ist.
_live = {"seq": 0, "events": [], "working": {}}   # working: agent -> (wie oft gerade, Aufgabe)
_live_lock = threading.RLock()


class working:
    """Markiert Agenten als „arbeitet gerade“, solange der Block läuft (für die Website).
    task: kurzer Text für die Sprechblase über dem Agenten, z. B. „Rendert Video #12“."""

    def __init__(self, *ids, task=None):
        self.ids, self.task = ids, task

    def __enter__(self):
        start_work(*self.ids, task=self.task)
        return self

    def __exit__(self, *exc):
        stop_work(*self.ids)


def start_work(*ids, task=None):
    with _live_lock:
        for a in ids:
            n, old = _live["working"].get(a, (0, None))
            _live["working"][a] = (n + 1, task or old)


def stop_work(*ids):
    with _live_lock:
        for a in ids:
            n, task = _live["working"].get(a, (1, None))
            if n <= 1:
                _live["working"].pop(a, None)
            else:
                _live["working"][a] = (n - 1, task)


def set_task(agent, task):
    """Neuer Text für die Sprechblase eines Agenten, der schon arbeitet (z. B. Fortschritt)."""
    with _live_lock:
        if agent in _live["working"]:
            _live["working"][agent] = (_live["working"][agent][0], task)


def tasks_now():
    """{agent: Aufgabe} aller Agenten, die gerade arbeiten."""
    with _live_lock:
        return {a: task or "" for a, (n, task) in _live["working"].items()}


def live_push(entry):
    """Wird für jedes neue Ereignis aus store.log aufgerufen."""
    with _live_lock:
        _live["seq"] += 1
        _live["events"] = (_live["events"] + [{**entry, "seq": _live["seq"]}])[-60:]


def live_since(seq):
    with _live_lock:
        return {"seq": _live["seq"], "events": [e for e in _live["events"] if e["seq"] > seq],
                "working": tasks_now(), "busy": status["busy"]}


def tts():
    global _tts
    with _tts_lock:
        if _tts is None:
            from make_short import load_tts
            _tts = load_tts()
    return _tts


def video_voice():
    """Stimme für die Videos: Fish Audio, wenn eingerichtet, sonst die eingebaute Piper-Stimme."""
    cfg = store.config()
    if cfg.get("fish_key") and cfg.get("fish_voice"):
        import fishtts
        return fishtts.Voice(tts(), cfg["fish_key"], cfg["fish_voice"], cfg.get("fish_voice_dark", ""),
                             cfg.get("fish_voice_warm", ""))
    return tts()


# --- Arbeit ------------------------------------------------------------------

def post_next(slot, manual=False, long=False, firma=False):
    """Rendert das nächste Skript und lädt es hoch. long: ein langes Video (eigene Warteschlange, eigener Sendeplan).

    firma: die tägliche Folge des Firmen-Spiels, zusätzlich zu den normalen Sendeplätzen (eigener Sendeplan).
    Liegt schon ein fertig gerenderter Short im Vorrat, wird nur der hochgeladen (dauert wenige Minuten).
    """
    if not long and not firma and not manual:
        cap = int(store.config().get("max_shorts_day") or 0)   # Schutz: ab dem ca. 11. Upload am Tag sieht niemand das Video mehr
        if cap and store.shorts_today() >= cap:
            store.log("warn", f"Sendeplatz ausgelassen: heute sind schon {cap} Shorts online, weitere würden kaum Aufrufe bekommen.")
            if slot:
                store.mark_slot(slot, "done_slots")
            return
    if not long and not firma and store.ready_items():
        try:
            return post_ready(slot, manual)
        finally:
            if manual:
                status["busy"] = ""  # "Startet …" vom Knopf „Jetzt posten“ wieder freigeben
    done = "long_slots" if long else "firma_slots" if firma else "done_slots"
    if relax_waiting.is_set() or not work_lock.acquire(blocking=False):
        return
    try:
        with working("planer", task="Wählt das nächste Video"):
            if firma:
                extra = firma_episode()
                if not extra:
                    store.mark_slot(slot, done)
                    return
                planned = [extra]
            else:
                planned = store.planned_queue(ready_only=True, long=long, with_ready=False)  # nach Lernmodus
            cfg = store.config()
            # Mit eigenem Clip-Kanal laufen Clips getrennt (post_clip_slot), sonst ersetzen sie hier Sendeplätze
            clip = None if (cfg["clip_token"] or long or firma) else clips.choose_for_slot(
                slot, store.hours_for(cfg, store.now()), agents.settings(cfg)["publisher"]["clips_per_day"],
                store.state()["uploads"], scripts_left=bool(planned))
        if clip:
            return post_clip(clip, slot, manual)
        if not planned:
            store.log("warn", ("Langes Video verpasst: " if long else "Sendeplatz verpasst: ") + (
                "Kein freigegebenes Video in der Warteschlange." if store.config()["approval"]
                else "Die Warteschlange ist leer."))
            if slot:
                store.mark_slot(slot, done)
            return
        file, spec = planned[0]
        status["busy"] = "Prüft die Verbindung zu YouTube"
        with working("publisher", task="Prüft die YouTube-Verbindung"):
            yt.check(store.config())
        status["busy"] = f"Erstelle Video: {spec['title']}"
        r = render_short(spec)
        publish(file, r["spec"], r["video"], r["total"], r["timings"], r["look"], slot, manual, done, long, show=True)
    except Exception as e:
        upload_failed(e, slot, done)
    finally:
        status["busy"] = ""
        work_lock.release()


def render_short(spec):
    """Rendert ein Skript zum fertigen Video. Gibt Video, Länge, Satzzeiten, Look und (ergänztes) Skript zurück."""
    n = len(store.state()["uploads"]) + 1  # laufende Nummer für die Sprechblasen
    from make_short import build_video
    ag = agents.settings(store.config())
    # Untertitel-Stil, Übergang und Kopfzeile, die bisher am besten liefen (oder fest im Video-Studio)
    look = agents.apply_look(store.next_look(), ag)
    if spec.get("stil") == "cartoon":  # Stimme passend zur Stimmung, gelernt (oder fest im Skript)
        # lange Videos: immer die klare Stimme (Julius, 19.11.2026), Shorts lernen
        look["stimme"] = spec.get("stimme") or ("klar" if spec.get("laenge") == "lang" else store.next_voice(spec))
        if spec.get("laenge") != "lang":  # Test: starke Soundeffekte auf der Auflösung gegen dezente
            look["effekte"] = spec.get("effekte") or store.next_effects()
            if spec.get("format") != "firma":  # Test: Spannung (Herzschlag + Countdown) gegen normale Shorts
                lay = store.next_layout()
                look["aufbau"] = spec["aufbau"] if spec.get("aufbau") in learn.LAYOUTS else lay
                # Test Tempo: schnelle Schnitte wie in Julius' Vorbild-Reels (nicht zusammen mit Spannung)
                tem = store.next_tempo()
                look["tempo"] = spec["tempo"] if spec.get("tempo") in learn.TEMPOS else (
                    "normal" if look["aufbau"] == "spannung" else tem)
                if look["tempo"] == "schnell" and not spec.get("stimme"):
                    import cartoon
                    look["stimme"] = cartoon.FAST_VOICE   # schnell geschnitten, aber klar gesprochen (Julius, 21.11.2026)
            if learn.abo_ok(spec):  # Test Abo-Aufruf am Ende (gesprochen / nur eingeblendet / ohne)
                mode, line = store.next_abo(spec)
                if spec.get("abo") in learn.ABO_MODES:   # zum Ausprobieren fest im Skript
                    mode = spec["abo"]
                    line = line or learn.abo_lines(spec)[0]
                if mode == "gesprochen" and str(spec.get("ende", "")).lower() == "loop":
                    mode = "eingeblendet"   # ein gesprochener Satz nach dem offenen Schluss würde den Loop zerstören
                look["abo"] = mode
                look["abo_text"] = line if mode != "ohne" else None
    key = store.config().get("stock_key", "")
    if not key:
        look["hintergrund"] = "animation"
    info = {}
    voice = video_voice()
    with working("sprecher", task=f"Spricht Video #{n}"), working("studio", task=f"Rendert Video #{n}"):
        video, total, timings = build_video({**spec, **look, "voice_speed": agents.voice_speed(ag)},
                                            store.path("out"), voice, stock_key=key, info=info)
    if getattr(voice, "error", None):
        store.log("warn", f"{voice.error}. Dieses Video spricht die eingebaute Stimme.", agent="sprecher")
    if look.get("hintergrund") == "clips" and not info.get("stock"):
        look["hintergrund"] = "animation"  # kein Clip gefunden, das Video ist animiert
    if info.get("stock"):  # Pixabay und Pexels bitten um einen Hinweis auf die Quelle
        import stock
        src = stock.CREDIT.get(info["stock"][0].get("provider"), "Pixabay (pixabay.com)")
        spec = {**spec, "description": spec.get("description", "") + f"\n\nHintergrundvideos: {src}"}
    return {"video": video, "total": total, "timings": [list(t) for t in timings], "look": look, "spec": spec}


def publish(file, spec, video, total, timings, look, slot, manual, done, long, show=False):
    """Thumbnail, Upload, Eintrag in die Liste der Uploads. Die Videodatei wird danach gelöscht.

    show: den Schritt oben in der Zentrale anzeigen (nicht beim Hochladen aus dem Vorrat, während etwas anderes rendert).
    """
    n = len(store.state()["uploads"]) + 1
    if show:
        status["busy"] = f"Baut das Thumbnail: {spec['title']}"
    with working("studio", task=f"Baut das Thumbnail für Video #{n}"):
        thumb_files = make_thumbs(spec)
    if show:
        status["busy"] = f"Lade hoch: {spec['title']}"
    with working("publisher", task=f"Lädt Video #{n} hoch"):
        video_id = yt.upload(store.config(), video, spec)
    thumb = None
    if thumb_files:
        choice = _safe_variant(long)
        thumb = {"set": apply_thumb(video_id, thumb_files, choice[:1])}
        if thumb["set"]:
            look["thumbnail"] = choice  # Lern-Merkmal nur, wenn YouTube das Bild angenommen hat
    marks = [round(s / total, 4) for s, _ in timings]  # Satzanfänge, für die Abschalt-Kurve
    store.mark_posted(file, slot, spec, video_id, marks=marks, duration=round(total, 1), look=look, done=done,
                      thumb=thumb)
    if spec.get("format") == "firma" and spec.get("firma_state"):
        store.write("firma.json", spec["firma_state"])  # Spielstand erst nach dem Upload weiterzählen
    for a in ("planer", "sprecher", "studio", "publisher"):
        store.agent_done(a)
    if not long:
        try:
            store.keep_for_share(video, video_id)  # für TikTok und Instagram, bevor die Datei gelöscht wird
        except OSError as e:
            store.log("warn", f"Kopie für TikTok/Instagram nicht gespeichert: {e}")
    try:
        os.remove(video)
    except OSError:
        pass
    store.log("ok", f"Gepostet: {spec['title']}" + (" (manuell)" if manual else ""),
              agent="publisher", kind="posted", source="youtube")
    refresh_stats()


def upload_failed(e, slot, done):
    if yt.is_expired(e):
        connection_expired()
        return  # Sendeplatz bleibt offen und wird nach dem Neu-Verbinden nachgeholt
    traceback.print_exc()
    store.agent_done("publisher", error=e)
    store.log("error", f"Upload fehlgeschlagen: {e}", agent="publisher", kind="error")
    if slot:  # nicht endlos wiederholen, der nächste Platz versucht es erneut
        store.mark_slot(slot, done)


upload_lock = threading.Lock()  # fertige Shorts aus dem Vorrat hochladen, auch während gerade etwas rendert


def post_ready(slot, manual=False):
    """Lädt den ältesten fertig gerenderten Short aus dem Vorrat hoch."""
    if not upload_lock.acquire(blocking=False):
        return
    try:
        items = store.ready_items()
        if not items:
            return
        item = items[0]
        file = store.path("queue", item["file"])
        cfg = store.config()
        if cfg["approval"] and item["file"] not in set(store.state()["approved"]):
            # Freigabe zurückgenommen: Video wegwerfen, das Skript wartet wieder normal
            store.drop_ready(item)
            return post_ready_next(slot, manual)
        with working("publisher", task="Prüft die YouTube-Verbindung"):
            yt.check(cfg)
        try:
            publish(file, item["spec"], item["video"], item["total"], item["timings"], item["look"],
                    slot, manual, "done_slots", False)
        except Exception as e:
            if not yt.is_expired(e):
                store.ready_failed(item)  # nach 2 Fehlversuchen wird das Video verworfen und neu gerendert
            raise
        store.drop_ready(item)
    except Exception as e:
        upload_failed(e, slot, "done_slots")
    finally:
        upload_lock.release()


def post_ready_next(slot, manual):
    """Nach einem verworfenen Vorrats-Video: nächstes versuchen (ohne Sperre, die hält schon der Aufrufer)."""
    items = [i for i in store.ready_items()
             if not store.config()["approval"] or i["file"] in set(store.state()["approved"])]
    if not items:
        return
    item = items[0]
    yt.check(store.config())
    publish(store.path("queue", item["file"]), item["spec"], item["video"], item["total"], item["timings"],
            item["look"], slot, manual, "done_slots", False)
    store.drop_ready(item)


def prerender():
    """Rendert den nächsten Short in den Vorrat, wenn der Server gerade frei ist.

    Lange Videos und die Firmen-Folge haben Vorrang: Sind sie dran, wird nicht vorgerendert.
    """
    cfg = store.config()
    ag = agents.settings(cfg)
    if not cfg["refresh_token"] or not ag["publisher"]["on"] or status["busy"]:
        return
    if store.due_long(ag["publisher"].get("long_per_week", 0)) or store.due_firma(cfg.get("firma_hour")):
        return
    if len(store.ready_items()) >= store.READY_MAX:
        return
    if relax_waiting.is_set() or not work_lock.acquire(blocking=False):
        return
    try:
        planned = store.planned_queue(ready_only=True, with_ready=False)
        if not planned:
            return
        file, spec = planned[0]
        r = render_short(spec)
        store.add_ready(os.path.basename(file), r)
        store.log("info", f"Fertig gerendert, wartet auf den Sendeplatz: {spec['title']}", agent="studio")
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        store.log("warn", f"Vorrendern fehlgeschlagen: {e}", agent="studio")
        time.sleep(600)  # nicht im Kreis rendern, wenn etwas kaputt ist
    finally:
        work_lock.release()


def ready_worker():
    while True:
        try:
            prerender()
        except Exception:
            traceback.print_exc()
        time.sleep(30)


def make_thumbs(spec):
    """Baut beide Thumbnail-Varianten (thumbnail.py). Ein Fehler hier stoppt nie den Upload."""
    try:
        import thumbnail
        return thumbnail.build(spec, store.path("thumbs", "custom"))
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        store.log("warn", f"Thumbnail nicht erstellt, YouTube nimmt ein Bild aus dem Video: {e}", agent="studio")
        return None


def _safe_variant(long):
    try:
        return store.next_thumb(long)
    except Exception:  # noqa: BLE001
        return learn.THUMBS[0]


def apply_thumb(video_id, files, variant):
    """Setzt das Thumbnail auf YouTube. Gibt die Variante zurück, oder None, wenn YouTube es ablehnt."""
    try:
        yt.set_thumbnail(store.config(), video_id, files[variant])
    except Exception as e:  # noqa: BLE001
        print(f"Thumbnail für {video_id} abgelehnt: {e!r}", flush=True)
        if yt.is_limit(e):
            store.set_thumb_status(False, "limit", e)
            store.log("warn", "Thumbnail nicht gesetzt: YouTube-Tageslimit erreicht.", agent="publisher")
        elif yt.thumb_not_allowed(e):
            first = (store.state().get("thumb_status") or {}).get("reason") != "verify"
            store.set_thumb_status(False, "verify", e)
            if first:
                store.log("warn", "Eigene Thumbnails gehen erst, wenn dein Kanal bestätigt ist: youtube.com/verify "
                                  "öffnen und mit Handynummer bestätigen.", agent="publisher")
        else:
            store.set_thumb_status(False, str(e)[:200], e)
            store.log("warn", f"Thumbnail nicht gesetzt: {e}", agent="publisher")
        return None
    store.set_thumb_status(True)
    return variant


def retry_thumbs():
    """Setzt Thumbnails für die letzten Uploads, bei denen YouTube sie noch nicht angenommen hat (z. B. nach der
    Kanal-Bestätigung). Hört beim ersten „nicht erlaubt“ auf, damit nicht 30 Mal derselbe Fehler kommt."""
    import thumbnail
    ups = [u for u in store.state()["uploads"] if u.get("kind") != "clip" and u.get("video_id")]
    todo = [u for u in ups[-store.THUMB_RETRY_MAX:] if not (u.get("thumb") or {}).get("set")]
    done = 0
    for u in reversed(todo):   # neueste zuerst
        spec = store.find_spec(u["slug"])
        if not spec:
            continue
        variant = _safe_variant(bool(u.get("lang")))[:1]
        file = store.thumb_path(u["slug"], variant)
        try:
            if not os.path.exists(file):
                with thumb_lock:
                    thumbnail.build(spec, os.path.dirname(file))
        except Exception as e:  # noqa: BLE001
            store.log("warn", f"Thumbnail nicht erstellt ({u['title']}): {e}", agent="studio")
            continue
        if not apply_thumb(u["video_id"], {variant: file}, variant):
            break
        store.set_upload_thumb(u["video_id"], variant)
        done += 1
    st = store.state().get("thumb_status") or {}
    if done:
        store.log("ok", f"Thumbnails nachgeholt: {done} Videos.", agent="publisher", kind="input")
    elif not st.get("ok"):
        store.log("warn", "Thumbnails nachholen: YouTube lehnt noch ab. " + (st.get("detail") or ""), agent="publisher")


def firma_episode():
    """Firmen-Spiel: baut die Folge des Tages mit der echten Abozahl (Sendezeit: store.due_firma).

    Jeden Abend ist eine andere Firma dran (Autofirma, Burgerladen, Raketenfirma, Spielestudio, siehe firma.THEMES),
    jede mit eigenem Spielstand, damit man an den Aufrufen sieht, welche am besten ankommt.

    Gibt (datei, skript) für die Warteschlange zurück, sonst None. Namen kommen von Abonnenten mit öffentlichen
    Abos und aus Kommentaren mit Wunschjob (siehe firma.py).
    """
    import firma

    cfg = store.config()
    st = store.read("firma.json", {})
    today = store.now().date()
    if st.get("last_day") == today.isoformat():
        return None
    ch = store.read("channel.json", {})
    if not ch.get("id"):
        return None
    comments, subs = [], []
    try:
        comments = yt.recent_comments(cfg, ch["id"])
    except Exception as e:
        store.log("warn", f"Firmen-Spiel: Kommentare nicht geladen ({e})", agent="planer")
    try:
        subs = yt.public_subscribers(cfg)
    except Exception as e:
        store.log("warn", f"Firmen-Spiel: Abonnenten-Namen nicht geladen ({e})", agent="planer")
    for old in glob.glob(store.path("firma", "*.json")):  # alte, nicht gesendete Folge: Zahlen veraltet
        os.remove(old)
    spec, new_state = firma.episode(ch.get("subscribers", 0), st, comments, subs, today=today, own_channel=ch["id"])
    spec["firma_state"] = new_state
    file = store.path("firma", f"0000-{spec['slug']}.json")  # eigener Ordner, nicht in der normalen Warteschlange
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    th = spec["firma_thema"]
    store.log("info", f"Firmen-Spiel ({firma.THEMES[th]['firma']}): Tag {new_state['themen'][th]['tag']} "
              f"mit {new_state['themen'][th]['mitarbeiter']} Mitarbeitern",
              agent="planer")
    return file, spec


def clip_target():
    """Zugang für Clip-Uploads: der eigene Clip-Kanal, wenn verbunden, sonst der Hauptkanal."""
    cfg = store.config()
    return ({**cfg, "refresh_token": cfg["clip_token"]}, True) if cfg["clip_token"] else (cfg, False)


def post_clip(item, slot, manual=False, done="done_slots", busy=True):
    """Lädt einen freigegebenen Clip hoch (läuft innerhalb von post_next bzw. mit work_lock).
    busy=False: Clipi-Upload nebenher, die Anzeige „beschäftigt“ des Hauptkanals bleibt unberührt."""
    c, clip = item
    cfg, own = clip_target()
    if busy:
        status["busy"] = f"Lade Clip hoch: {clip['title']}"
    try:
        with working("publisher", task="Prüft die YouTube-Verbindung"):
            yt.check(cfg)
        with working("publisher", task=f"Lädt Clip „{clip['title'][:28]}“ hoch"):
            video_id = yt.upload(cfg, clips.clip_path(c, clip), clips.upload_spec(c, clip))
    except Exception as e:
        if own and yt.is_expired(e):  # nur der Clip-Kanal ist betroffen, der Hauptkanal läuft weiter
            clip_connection_expired()
            raise RuntimeError("Die Verbindung zum Clip-Kanal ist abgelaufen.") from e
        raise
    clips.mark_posted(c["id"], clip["n"], video_id)
    record = clips.upload_record(c, clip, slot, video_id)
    if own:
        record["channel"] = "clips"
    store.mark_clip_posted(slot, record, done=done)
    store.agent_done("publisher")
    store.log("ok", f"Clip gepostet{' auf dem Clip-Kanal' if own else ''}: {clip['title']}" + (" (manuell)" if manual else ""),
              agent="publisher", kind="posted", source="youtube")
    refresh_stats()


def post_clip_slot(slot, manual=False):
    """Sendeplatz des eigenen Clip-Kanals (Clipi): postet das nächste Video aus der Warteschlange.

    Läuft im eigenen Faden (clipi_worker) mit eigenem Lock, damit Clipi nicht wartet, während der
    Hauptkanal ein Video baut. Tageslimit: Einstellung „Clipi pro Tag“. Content-Rewards-Clips sind nie dabei.
    Ist die Warteschlange leer, bleibt der Platz offen und wird nachgeholt, sobald ein Video da ist."""
    if not clipi_lock.acquire(blocking=False):
        return False
    try:
        cfg = store.config()
        per = agents.settings(cfg)["publisher"]["clipi_per_day"]
        today = store.now().date().isoformat()
        done_today = sum(1 for u in store.state()["uploads"]
                         if u.get("channel") == "clips" and (u.get("posted_at") or "")[:10] == today)
        if done_today >= per and not manual:
            if slot:
                store.mark_slot(slot, "clipi_slots")
            return False
        if not manual and store.clipi_room(cfg, store.state()) <= 0:
            if slot:  # Tagestopf von YouTube (100 pro Projekt) gehört auch dem Hauptkanal, darum hier stoppen
                store.mark_slot(slot, "clipi_slots")
            return False
        ready = clips.ready_clips(auto=True)
        if not ready:
            return False
        store.clipi_posted()
        post_clip(ready[0], slot, done="clipi_slots", busy=False, manual=manual)
        if slot is None:
            store.agent_done("publisher")
        return True
    except Exception as e:
        if slot:
            store.mark_slot(slot, "clipi_slots")
        if yt.is_limit(e):  # YouTube nimmt heute nichts mehr an: morgen weiter, das Video bleibt in der Warteschlange
            until = (store.now() + dt.timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0)
            store.pause_clipi(until)
            store.agent_done("publisher")
            store.log("warn", "YouTube nimmt heute keine weiteren Clipi-Uploads an (Tageslimit des Kanals). "
                      "Es geht morgen um 9:30 Uhr weiter, nichts geht verloren.", agent="publisher", kind="error")
            return False
        traceback.print_exc()
        store.agent_done("publisher", error=e)
        store.log("error", f"Clipi-Upload fehlgeschlagen: {e}", agent="publisher", kind="error")
        return False
    finally:
        clipi_lock.release()


def clipi_worker():
    """Eigener Faden für Clipi: schaut jede Minute, ob ein Clipi-Platz dran ist."""
    while True:
        try:
            cfg = store.config()
            ag = agents.settings(cfg)
            if cfg["clip_token"] and ag["publisher"]["on"]:
                slot = store.due_clipi(ag["publisher"]["clipi_per_day"])
                if slot:
                    post_clip_slot(slot)
        except Exception:
            traceback.print_exc()
        time.sleep(60)


def post_clip_now(cid, n):
    """„Jetzt posten“ für einen einzelnen Clip aus der Freigabe-Station."""
    if not work_lock.acquire(blocking=False):
        return
    try:
        c = clips.load(cid)
        clip = next(x for x in c["clips"] if x["n"] == n)
        if clip["status"] == "neu":
            clips.set_clip(cid, n, "approve")
            clip["status"] = "freigegeben"
        post_clip((c, clip), None, manual=True)
    except Exception as e:
        if yt.is_expired(e):
            connection_expired()
            return
        traceback.print_exc()
        store.agent_done("publisher", error=e)
        store.log("error", f"Clip-Upload fehlgeschlagen: {e}", agent="publisher", kind="error")
    finally:
        status["busy"] = ""
        work_lock.release()


# --- Video-Clipper -----------------------------------------------------------------

_clip_wake = threading.Event()


def clip_worker():
    """Eigener Faden: holt Videos aus dem Eingangsordner und schneidet bestätigte Kampagnen, eine nach der anderen."""
    while True:
        try:
            ag = agents.settings(store.config())["clipper"]
            if ag["on"]:
                clips.scan_inbox(auto_start=ag["auto_start"])
            job = clips.next_job()
            if job:
                run_clip_job(job["id"], ag)
                continue
        except Exception:
            traceback.print_exc()
        _clip_wake.wait(20)
        _clip_wake.clear()


def run_clip_job(cid, settings):
    start_work("clipper", task="Startet")
    try:
        c = clips.process(cid, settings, task=lambda text: set_task("clipper", text))
        n = len(c["clips"])
        store.agent_done("clipper")
        wait = ", er wartet auf deine Freigabe." if n == 1 else ", sie warten auf deine Freigabe."
        store.log("ok", f"{n} Clip{'s' if n != 1 else ''} aus „{c['name']}“ fertig"
                  + (" und in der Clipi-Warteschlange." if clips.is_clipi(c) else wait if settings["freigabe"] else " und freigegeben."),
                  agent="clipper", kind="clips", source="clipper")
    except Exception as e:
        traceback.print_exc()
        store.agent_done("clipper", error=e)
        store.log("error", f"Clipping fehlgeschlagen: {e}", agent="clipper", kind="error")
    finally:
        stop_work("clipper")


def webhook_video(h):
    """POST /webhook/video: neues Video für eine Kampagne (geschützt mit dem Webhook-Schlüssel)."""
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(h.path).query)
    token = h.headers.get("X-Webhook-Token") or q.get("token", [""])[0]
    expected = store.config().get("webhook_token") or ""
    if not expected or not secrets.compare_digest(token.encode(), expected.encode()):
        return h.send(401, {"error": "Falscher oder fehlender Schlüssel (X-Webhook-Token)."})
    try:
        length = int(h.headers.get("Content-Length") or 0)
    except ValueError:
        length = 0
    one = lambda k, d="": q.get(k, [d])[0]
    try:
        if (h.headers.get("Content-Type") or "").startswith("application/json"):
            if length > 100_000:
                return h.send(413, {"error": "Zu groß."})
            data = json.loads(h.rfile.read(length) or b"{}")
            rights, credit, name = bool(data.get("rights")), str(data.get("credit") or ""), data.get("name")
            if data.get("file"):
                path = os.path.join(clips.inbox_dir(), os.path.basename(str(data["file"])))
                if not os.path.isfile(path):
                    return h.send(404, {"error": "Datei nicht im Eingangsordner gefunden."})
                c = clips.add_file(path, "webhook", rights, credit, name)
            elif data.get("url"):
                url = str(data["url"])
                clips.check_url(url)
                background(_download, url, rights, credit, name)
                return h.send(202, {"ok": True, "text": "Video wird geladen, die Kampagne erscheint gleich."})
            else:
                return h.send(400, {"error": "Bitte url, file oder die Videodatei selbst schicken."})
        else:
            filename = one("filename") or h.headers.get("X-Filename") or "video.mp4"
            c = clips.add_stream(h.rfile, length, filename, "webhook", one("rights") in ("1", "true", "ja"),
                                 one("credit"), one("name") or None)
    except ValueError as e:
        return h.send(400, {"error": str(e)})
    _clip_wake.set()
    h.send(200, {"ok": True, "campaign": c["id"], "status": c["status"],
                 "text": "Wird geschnitten." if c["status"] == "wartet" else "Bitte im Bereich Kampagnen die Rechte bestätigen."})


def _download(url, rights, credit, name, source="webhook", program=None):
    try:
        with working("clipper", task="Lädt das Video vom Link"):
            c = clips.add_url(url, rights, credit, name, source)
        if program:
            c = clips.update(c["id"], lambda k: k.__setitem__("program", program))
        store.log("info", f"Video vom Link geladen: {c['name']}", agent="clipper", kind="input")
        _clip_wake.set()
    except Exception as e:
        store.log("error", f"Video vom Link konnte nicht geladen werden: {e}", agent="clipper", kind="error")


_last_refresh = [0.0]


def refresh_stats():
    cfg = store.config()
    if not cfg["refresh_token"]:
        return
    _last_refresh[0] = time.time()
    try:
        with working("analyst", task="Holt Aufrufe und Likes"):
            ch = yt.channel(cfg)
            store.write("channel.json", ch)
            ups = store.state()["uploads"]
            ids = [u["video_id"] for u in ups]
            videos = yt.video_stats(cfg, ids) if ids else {}
        store.write("stats.json", {"updated_at": store.now().isoformat(timespec="seconds"), "videos": videos})
        own = {u["video_id"] for u in ups if u.get("channel") == "clips"}  # Clip-Kanal zählt nicht zum Hauptkanal
        cch = None
        if cfg["clip_token"]:
            try:
                cch = yt.channel({**cfg, "refresh_token": cfg["clip_token"]})
                store.write("clipchannel.json", cch)
            except Exception as e:
                if yt.is_expired(e):
                    clip_connection_expired()
        if cfg["relax_token"]:
            try:
                store.write("relaxchannel.json", yt.channel({**cfg, "refresh_token": cfg["relax_token"]}))
                relax_refresh_stats(cfg)
            except Exception as e:
                if yt.is_expired(e):
                    relax_connection_expired()
        store.record_history(sum(v["views"] for k, v in videos.items() if k not in own), ch.get("subscribers", 0), clip=cch)
        store.agent_done("analyst")
    except Exception as e:
        store.agent_done("analyst", error=e)
        if yt.is_expired(e):
            return connection_expired()
        store.log("error", f"Statistiken konnten nicht geladen werden: {e}", agent="analyst", kind="error")


def refresh_analytics():
    """Holt von YouTube Analytics, wie lange Zuschauer dranbleiben (Ø angesehen und Kurve je Video).

    YouTube liefert diese Daten mit 1 bis 3 Tagen Verzögerung. Kurven werden je Video höchstens
    alle 12 Stunden neu geholt, damit es schnell bleibt.
    """
    cfg = store.config()
    if not cfg["analytics_token"]:
        return
    data = store.read("analytics.json", {"videos": {}})
    videos = data.get("videos", {})
    uploads = store.state()["uploads"]
    today = store.now().date()
    start = min([u["posted_at"][:10] for u in uploads] or [str(today - dt.timedelta(days=28))])
    start_work("zuschauer", task="Holt Zuschauer-Daten")
    try:
        summary = yt.analytics_summary(cfg, start, str(today))
        fetched = 0
        for u in reversed(uploads):  # neueste zuerst
            vid, age_h = u["video_id"], (store.now() - dt.datetime.fromisoformat(u["posted_at"])).total_seconds() / 3600
            entry = {**videos.get(vid, {}), **summary.get(vid, {})}
            stale = time.time() - entry.get("curve_ts", 0) > 12 * 3600
            if age_h >= 24 and stale and fetched < 30:
                curve = yt.retention_curve(cfg, vid, u["posted_at"][:10], str(today))
                fetched += 1
                if curve:
                    entry["curve"] = [[r, w] for i, (r, w) in enumerate(curve) if i % 2 == 1 or len(curve) <= 50]
                entry["curve_ts"] = time.time()
            if entry:
                videos[vid] = entry
        store.write("analytics.json", {"updated_at": store.now().isoformat(timespec="seconds"),
                                       "videos": videos, "error": None})
        store.agent_done("zuschauer")
    except Exception as e:
        text = str(e)
        if yt.is_expired(e):
            store.save_config(analytics_token="", analytics_scopes="")
            error = "Der Zugang für die Zuschauer-Daten ist abgelaufen. Bitte im Reiter Kanal neu verbinden."
        elif "accessNotConfigured" in text or "has not been used" in text or "is disabled" in text:
            error = "Die YouTube Analytics API ist im Google-Projekt noch nicht aktiviert."
        else:
            error = f"Zuschauer-Daten konnten nicht geladen werden: {text[:200]}"
        store.write("analytics.json", {**data, "error": error})
        store.agent_done("zuschauer", error=error)
        store.log("error", error, agent="zuschauer", kind="error")
    finally:
        stop_work("zuschauer")


comments_lock = threading.Lock()


def comments_reset_access():
    """Nach neuem Verbinden: alte Zugangs-Fehler vergessen, damit die Kommentar-Antworten neu prüfen."""
    with store.LOCK:
        d = comments.load()
        d["status"] = {k: v for k, v in d["status"].items() if k not in ("reason", "error", "channel_ok")}
        comments.save(d)


def check_comments(force=False):
    """Liest neue Kommentare und antwortet auf die einfachen (siehe comments.py). Läuft im eigenen Faden."""
    if not comments_lock.acquire(blocking=False):
        return
    try:
        cfg = store.config()
        d = comments.load()
        if not force and not comments.due(d):
            return
        acc = comments.access(cfg)
        ch = store.read("channel.json", None) or {}
        with store.LOCK:
            d = comments.load()
            d["status"]["checked_at"] = store.now().isoformat(timespec="seconds")
            if acc != "ok" or not ch.get("id"):
                d["status"].update(reason=acc if acc != "ok" else "kanal_fehlt", error=None)
                return comments.save(d)
            comments.save(d)
        client = yt.reply_client(cfg)
        if d["status"].get("channel_ok") != ch["id"]:
            mine = yt.my_channel_id(client)
            if mine != ch["id"]:
                with store.LOCK:
                    d = comments.load()
                    d["status"].update(reason="kanal", error="Der Zugang gehört zu einem anderen Kanal. Bitte im "
                                       "Reiter Zuschauer neu verbinden und dabei den Kanal „" + ch.get("title", "") + "“ wählen.")
                    return comments.save(d)
        threads = yt.comment_threads(client, ch["id"], ch["id"])
        with store.LOCK:
            d = comments.load()
            d["status"].update(channel_ok=ch["id"], reason=None, error=None)
            send = comments.process(threads, d, ch["id"], comments.videos())
            comments.save(d)
        for i, (entry, text) in enumerate(send):
            if i:
                time.sleep(random.uniform(20, 60))  # nicht alles in derselben Sekunde
            try:
                yt.reply(client, entry["id"], text)
            except Exception as e:
                reason, msg = comments.error_text(e)
                with store.LOCK:
                    d = comments.load()
                    if reason in ("aus", "text"):
                        d["seen"][entry["id"]] = store.now().isoformat(timespec="seconds")
                        comments.save(d)
                        continue
                    d["status"].update(reason=reason, error=msg)
                    if reason == "quota":
                        tomorrow = (store.now() + dt.timedelta(days=1)).replace(hour=comments.HOURS[0], minute=5)
                        d["status"]["pause_until"] = tomorrow.isoformat(timespec="seconds")
                    d["seen"].pop(entry["id"], None)   # später noch einmal versuchen
                    comments.save(d)
                store.log("error", msg, kind="error")
                break
            with store.LOCK:
                d = comments.load()
                comments.record_sent(d, entry, text)
                comments.save(d)
        if send:
            store.log("ok", f"Auf {len(send)} Kommentar{'e' if len(send) != 1 else ''} geantwortet.", kind="comments")
    except Exception as e:
        if yt.is_expired(e):
            store.save_config(analytics_token="", analytics_scopes="")
        reason, msg = comments.error_text(e)
        with store.LOCK:
            d = comments.load()
            d["status"].update(reason=reason, error=msg)
            comments.save(d)
        traceback.print_exc()
    finally:
        comments_lock.release()


def clip_connection_expired():
    store.save_config(clip_token="", clip_expired=True)
    status["connect_clip"] = {"status": "idle"}
    store.log("warn", "Die Verbindung zum Clip-Kanal ist abgelaufen. Bitte im Reiter Kanäle neu verbinden.")


def connect_clip_channel():
    cfg = store.config()
    try:
        code = yt.device_start(cfg["client_id"])
        status["connect_clip"] = {"status": "code", "user_code": code["user_code"],
                                  "verification_url": code.get("verification_url", "https://www.google.com/device"),
                                  "expires_at": code["expires_at"]}
        token = yt.device_wait(cfg["client_id"], cfg["client_secret"], code)
        ch = yt.channel({**cfg, "refresh_token": token})
        main = store.read("channel.json", {}) or {}
        if main.get("id") and ch["id"] == main["id"]:
            raise RuntimeError("Das ist derselbe Kanal wie dein Hauptkanal. Wähle bei Google den anderen Kanal aus.")
        store.write("clipchannel.json", ch)
        store.save_config(clip_token=token, clip_expired=False)
        status["connect_clip"] = {"status": "verbunden"}
        store.log("ok", f"Clip-Kanal verbunden: {ch.get('title', 'YouTube')}. Clips gehen ab jetzt dorthin.")
    except Exception as e:
        status["connect_clip"] = {"status": "fehler", "message": str(e)}
        store.log("error", f"Clip-Kanal-Verbindung fehlgeschlagen: {e}")


def relax_connection_expired():
    store.save_config(relax_token="", relax_expired=True)
    status["connect_relax"] = {"status": "idle"}
    store.log("warn", "Die Verbindung zum Entspannungskanal ist abgelaufen. Bitte im Reiter Kanäle neu verbinden.")


def connect_relax_channel():
    cfg = store.config()
    try:
        code = yt.device_start(cfg["client_id"])
        status["connect_relax"] = {"status": "code", "user_code": code["user_code"],
                                   "verification_url": code.get("verification_url", "https://www.google.com/device"),
                                   "expires_at": code["expires_at"]}
        token = yt.device_wait(cfg["client_id"], cfg["client_secret"], code)
        ch = yt.channel({**cfg, "refresh_token": token})
        others = [(store.read("channel.json", {}) or {}).get("id"), (store.read("clipchannel.json", {}) or {}).get("id")]
        if ch["id"] in [o for o in others if o]:
            raise RuntimeError("Das ist ein Kanal, der schon verbunden ist. Wähle bei Google den neuen Entspannungskanal aus.")
        store.write("relaxchannel.json", ch)
        store.save_config(relax_token=token, relax_expired=False)
        status["connect_relax"] = {"status": "verbunden"}
        store.log("ok", f"Entspannungskanal verbunden: {ch.get('title', 'YouTube')}. Ab jetzt kommt dort täglich ein langes Video.")
        relax_apply_branding()
    except Exception as e:
        status["connect_relax"] = {"status": "fehler", "message": str(e)}
        store.log("error", f"Entspannungskanal-Verbindung fehlgeschlagen: {e}")


def relax_brand_files():
    """Banner und Profilbilder für Quiet Corner (einmal gebaut, dann aus dem Speicher). Gibt {name: pfad} zurück."""
    import entspannung
    folder = store.path("relax-brand")
    want = [f"quiet-corner-{k}-{v}.{'jpg' if k == 'banner' else 'png'}" for v in entspannung.BRAND_VARIANTS for k in ("banner", "profil")]
    if not all(os.path.exists(os.path.join(folder, f)) for f in want):
        entspannung.branding(folder)
    wm = os.path.join(folder, "quiet-corner-wasserzeichen.png")
    if not os.path.exists(wm):
        entspannung.watermark(wm)
    return {f: os.path.join(folder, f) for f in want + ["quiet-corner-kanaltext.txt", "quiet-corner-wasserzeichen.png"]}


def relax_apply_branding(variant=None):
    """Setzt Banner, Beschreibung und Stichwörter auf dem Entspannungskanal (Profilbild geht nur von Hand in YouTube Studio)."""
    import entspannung
    cfg = store.config()
    if not cfg["relax_token"]:
        return False
    variant = variant or cfg.get("relax_banner", "A")
    try:
        files = relax_brand_files()
        yt.set_branding({**cfg, "refresh_token": cfg["relax_token"]}, files[f"quiet-corner-banner-{variant}.jpg"],
                        entspannung.CHANNEL_DESCRIPTION, entspannung.CHANNEL_KEYWORDS, language="en", country="DE")
        try:
            yt.set_watermark({**cfg, "refresh_token": cfg["relax_token"]}, files["quiet-corner-wasserzeichen.png"])
            store.log("ok", "Quiet Corner: Wasserzeichen gesetzt.")
        except Exception as e:
            store.log("warn", f"Quiet Corner: Wasserzeichen nicht gesetzt: {e}")
        info = store.read("relax.json", {}) or {}
        info["branded"] = {"variant": variant, "at": store.now().isoformat(timespec="seconds")}
        store.write("relax.json", info)
        store.log("ok", f"Quiet Corner: Banner {variant} und Kanalbeschreibung gesetzt.")
        return True
    except Exception as e:
        traceback.print_exc()
        store.log("warn", f"Quiet Corner: Banner konnte nicht gesetzt werden: {e}")
        return False


def relax_phase(text):
    """Merkt sich, was Quiet Corner gerade macht, damit die Zentrale es anzeigen kann."""
    with store.LOCK:
        st = store.state()
        st["relax_phase"] = text
        store.write("state.json", st)


def post_relax(manual=False):
    """Quiet Corner: wählt die nächste Idee (Lernmodus), baut das lange Video plus Teaser-Short und lädt beides hoch.

    Rendert nur eine Minute Bild (plus 30 s Teaser), der Rest ist ffmpeg-Kopie. Braucht kurz den Renderer (work_lock),
    damit nicht gleichzeitig ein Short rendert. Dateien werden nach dem Upload gelöscht.
    """
    import shutil
    import entspannung
    if not relax_lock.acquire(blocking=False):
        return False
    folder = store.path("relax")
    try:
        cfg = store.config()
        if not cfg["relax_token"]:
            return False
        relax_phase("Wartet, bis der Server frei ist (ein laufender Short wird noch fertig)")
        relax_waiting.set()
        try:
            got = work_lock.acquire(timeout=4 * 3600 if not manual else 30 * 60)
        finally:
            relax_waiting.clear()
        if not got:
            raise RuntimeError("Der Server rendert gerade einen anderen Short, später noch einmal.")
        try:
            relax_phase("Baut das Video (ca. 10 bis 20 Minuten)")
            st = store.state()
            n = int(st.get("relax_n", 0))
            ups = (store.read("relax.json", {}) or {}).get("uploads") or []
            try:
                relax_check_uploads(cfg)   # erst nachsehen, ob YouTube die letzten Videos angenommen hat
                st = store.state()
                ups = (store.read("relax.json", {}) or {}).get("uploads") or []
            except Exception:
                traceback.print_exc()
            idea, minutes = entspannung.choose(ups, cfg.get("relax_length", "auto"), store.now().date(), n, st.get("relax_cap"))
            shutil.rmtree(folder, ignore_errors=True)
            status["busy"] = f"Baut Quiet-Corner-Video: {entspannung.IDEA[idea]['title']}, {entspannung.dauer_text(minutes)}"
            with working("studio", task="Baut ein langes Entspannungsvideo"):
                r = entspannung.build(idea, minutes, folder, seed=n + 1, teaser=bool(cfg.get("relax_shorts", True)))
        finally:
            status["busy"] = ""
            work_lock.release()
        meta = entspannung.meta(idea, minutes, n)
        rcfg = {**cfg, "refresh_token": cfg["relax_token"], "privacy": "public"}
        spec = {**meta, "laenge": "lang", "footer": "", "category": "22", "language": "en", "chunksize": 64 * 1024 * 1024}
        relax_phase("Lädt hoch (bei 8 bis 10 Std. dauert das ein paar Stunden)")
        with working("publisher", task="Lädt ein Entspannungsvideo hoch"):
            video_id = yt.upload(rcfg, r["video"], spec)
        thumb = False
        try:
            yt.set_thumbnail(rcfg, video_id, r["thumb"])
            thumb = True
        except Exception as e:  # Thumbnails brauchen einen bestätigten Kanal (youtube.com/verify)
            store.log("warn", f"Thumbnail für das Entspannungsvideo nicht gesetzt: {e}")
        teaser_id = None
        if r.get("teaser"):
            try:
                tm = entspannung.teaser_meta(idea, minutes, video_id)
                teaser_id = yt.upload(rcfg, r["teaser"], {**tm, "footer": "", "category": "22", "language": "en"})
            except Exception as e:
                store.log("warn", f"Quiet Corner: Teaser-Short nicht hochgeladen: {e}")
        day = store.now().date().isoformat()
        with store.LOCK:
            st = store.state()
            st["relax_today_n"] = (int(st.get("relax_today_n", 1)) + 1) if st.get("relax_last") == day else 1
            st["relax_last"], st["relax_n"] = day, int(st.get("relax_n", 0)) + 1
            store.write("state.json", st)
        info = store.read("relax.json", {}) or {}
        info["error"] = None
        info["uploads"] = (info.get("uploads") or [])[-200:] + [{
            "video_id": video_id, "title": meta["title"], "idea": idea, "scene": entspannung.IDEA[idea]["scene"],
            "minutes": minutes, "at": day, "thumb": thumb, "teaser_id": teaser_id, "views": 0}]
        store.write("relax.json", info)
        relax_phase("")
        store.log("ok", f"Quiet Corner: hochgeladen: {meta['title']}" + (" (plus Teaser-Short)" if teaser_id else ""))
        if not info.get("branded"):
            relax_apply_branding()
        return True
    except Exception as e:
        traceback.print_exc()
        relax_phase("")
        info = store.read("relax.json", {}) or {}
        info["error"] = str(e)[:300]
        store.write("relax.json", info)
        with store.LOCK:
            st = store.state()
            st["relax_tried"] = store.now().isoformat(timespec="seconds")
            store.write("state.json", st)
        if yt.is_expired(e):
            relax_connection_expired()
        store.log("error", f"Entspannungsvideo fehlgeschlagen: {e}", kind="error")
        return False
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        relax_lock.release()


def relax_check_uploads(cfg):
    """Prüft, ob YouTube die letzten Quiet-Corner-Videos wirklich angenommen hat. Zu lange werden abgelehnt:
    dann kürzer weitermachen und den Platz des Tages neu vergeben (Neu-Upload in kürzerer Form)."""
    import entspannung
    info = store.read("relax.json", {}) or {}
    today = store.now().date()
    recent = [u for u in info.get("uploads") or []
              if (today - dt.date.fromisoformat(u["at"])).days <= 3 and not u.get("ok")]
    if not recent:
        return
    states = yt.upload_states({**cfg, "refresh_token": cfg["relax_token"]}, [u["video_id"] for u in recent])
    bad = {i: x for i, x in states.items() if x["upload"] in ("rejected", "failed")}
    info = store.read("relax.json", {}) or {}
    keep, lost, cap = [], [], None
    for u in info.get("uploads") or []:
        x = bad.get(u["video_id"])
        if x:
            lost.append(u)
            if x["reason"] == "length" or x["upload"] == "rejected":
                cap = min(cap or 10 ** 6, entspannung.next_cap(u.get("minutes") or 600))
            continue
        if states.get(u["video_id"], {}).get("upload") == "processed":
            u["ok"] = True
        keep.append(u)
    if not lost:
        store.write("relax.json", info)
        return
    info["uploads"] = keep
    info["rejected"] = (info.get("rejected") or [])[-20:] + [{"video_id": u["video_id"], "title": u["title"], "minutes": u.get("minutes"), "at": u["at"]} for u in lost]
    if cap:
        info["notice"] = (f"YouTube hat ein Video wegen der Länge abgelehnt. Neue Videos sind jetzt höchstens {entspannung.dauer_text(cap)} lang. "
                          "Wenn du den Kanal auf youtube.com/verify bestätigt hast, in „Länge“ wieder eine längere wählen.")
    store.write("relax.json", info)
    with store.LOCK:
        st = store.state()
        if cap:
            st["relax_cap"] = cap
        for u in lost:   # der Platz zählt nicht als erledigt, dann baut die Zentrale sofort ein neues, kürzeres Video
            if u["at"] == st.get("relax_last") and int(st.get("relax_today_n", 1)) > 0:
                st["relax_today_n"] = int(st.get("relax_today_n", 1)) - 1
        st["relax_tried"] = None
        store.write("state.json", st)
    store.log("warn", f"Quiet Corner: {len(lost)} Video(s) von YouTube abgelehnt (zu lang). Es kommt ein kürzeres neu." if cap
              else f"Quiet Corner: {len(lost)} Video(s) von YouTube nicht angenommen.")


def relax_refresh_stats(cfg):
    """Aufrufe der Quiet-Corner-Videos (für den Lernmodus und die Übersicht)."""
    info = store.read("relax.json", {}) or {}
    ups = info.get("uploads") or []
    ids = [u["video_id"] for u in ups] + [u["teaser_id"] for u in ups if u.get("teaser_id")]
    if not ids:
        return
    try:
        relax_check_uploads(cfg)
    except Exception:
        traceback.print_exc()
    stats = yt.video_stats({**cfg, "refresh_token": cfg["relax_token"]}, ids)
    info = store.read("relax.json", {}) or {}
    for u in info.get("uploads") or []:
        if u["video_id"] in stats:
            u["views"], u["likes"] = stats[u["video_id"]]["views"], stats[u["video_id"]]["likes"]
        if u.get("teaser_id") in stats:
            u["teaser_views"] = stats[u["teaser_id"]]["views"]
    info["stats_at"] = store.now().isoformat(timespec="seconds")
    store.write("relax.json", info)


def relax_worker():
    """Eigener Faden: einmal pro Tag ab der eingestellten Uhrzeit ein langes Entspannungsvideo."""
    import entspannung
    try:
        relax_phase("")  # nach einem Neustart steht nichts mehr „in Arbeit“
    except Exception:
        pass
    while True:
        try:
            st = store.state()
            if entspannung.is_due(store.config(), st.get("relax_last"), store.now(), st.get("relax_tried"), st.get("relax_today_n")):
                post_relax()
        except Exception:
            traceback.print_exc()
        time.sleep(60)


def connection_expired():
    """Google nimmt den Zugang nicht mehr an: Kanal als getrennt markieren, damit die Website es anzeigt."""
    store.save_config(refresh_token="", expired=True)
    status["connect"] = {"status": "idle"}
    store.log("warn", "Die Verbindung zu YouTube ist abgelaufen. Bitte im Reiter Kanal neu verbinden.")


def sync_scripts():
    """Holt neue Skripte aus dem GitHub-Repo (Ordner seed/)."""
    if not SCRIPTS_REPO:
        return 0
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "shorts-zentrale"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    def get(url):
        # GitHub antwortet manchmal kurz mit 5xx: mehrmals mit Pause versuchen
        for wait in (3, 8, 20, None):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code < 500 or wait is None:
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if wait is None:
                    raise
            time.sleep(wait)

    start_work("autor", task="Holt neue Skripte")
    try:
        listing = get(f"https://api.github.com/repos/{SCRIPTS_REPO}/contents/seed")
        known = set(store.state()["known"])
        files = {}
        for item in listing:
            if item["name"].endswith(".json") and item["name"] not in known:
                blob = get(item["url"])
                files[item["name"]] = base64.b64decode(blob["content"]).decode("utf-8")
        added = store.add_scripts(files)
        store.agent_done("autor")
        if added:
            store.log("ok", f"{added} neue Skripte in die Warteschlange gelegt.", agent="autor", kind="scripts",
                      source="github")
            warm_thumbs()
        return added
    except Exception as e:
        store.agent_done("autor", error=e)
        store.log("error", f"Neue Skripte konnten nicht geladen werden: {e}", agent="autor", kind="error")
        return 0
    finally:
        stop_work("autor")


def connect_channel():
    cfg = store.config()
    try:
        code = yt.device_start(cfg["client_id"])
        status["connect"] = {"status": "code", "user_code": code["user_code"],
                             "verification_url": code.get("verification_url", "https://www.google.com/device"),
                             "expires_at": code["expires_at"]}
        token = yt.device_wait(cfg["client_id"], cfg["client_secret"], code)
        store.save_config(refresh_token=token, expired=False)
        refresh_stats()
        ch = store.read("channel.json", {}) or {}
        status["connect"] = {"status": "verbunden"}
        store.log("ok", f"Kanal verbunden: {ch.get('title', 'YouTube')}")
        apply_branding()
    except Exception as e:
        status["connect"] = {"status": "fehler", "message": str(e)}
        store.log("error", f"Kanal-Verbindung fehlgeschlagen: {e}")


def apply_branding(force=False):
    """Setzt Banner, Beschreibung und Stichwörter auf YouTube, einmal je Design-Version."""
    import branding

    cfg, st = store.config(), store.state()
    wk = cfg.get("post_hours_weekend") or cfg["post_hours"]
    version = f"{branding.VERSION}|{','.join(map(str, cfg['post_hours']))}|{','.join(map(str, wk))}"  # neue Sendezeiten = neues Banner
    if not cfg["refresh_token"] or (not force and st.get("branding_version") == version):
        return
    start_work("designer", task="Setzt Banner und Beschreibung")
    try:
        title = (store.read("channel.json", {}) or {}).get("title") or "60 Sekunden Wissen"
        banner, profile = branding.render_all(title, cfg["post_hours"], store.path("branding"))
        yt.set_branding(cfg, banner, branding.description(title, cfg["post_hours"], wk), branding.KEYWORDS)
        with store.LOCK:
            st = store.state()
            st["branding_version"] = version
            st["branding_at"] = store.now().isoformat(timespec="seconds")
            store.write("state.json", st)
        store.agent_done("designer")
        store.log("ok", "Kanal-Design gesetzt: Banner, Beschreibung und Stichwörter.", agent="designer",
                  kind="branding", source="youtube")
    except Exception as e:
        store.agent_done("designer", error=e)
        if yt.is_expired(e):
            return connection_expired()
        store.log("error", f"Kanal-Design konnte nicht gesetzt werden: {e}", agent="designer", kind="error")
    finally:
        stop_work("designer")


def warm_thumbs():
    """Erstellt fehlende Vorschaubilder im Hintergrund, damit die Website sofort Bilder zeigt."""
    from make_short import render_thumbnail
    for f in store.queue_files() + glob.glob(store.path("posted", "*.json")):
        try:
            spec = store.load_spec(f)
            target = store.path("thumbs", spec["slug"] + ".jpg")
            if not os.path.exists(target):
                render_thumbnail(spec, target)
        except Exception as e:
            print(f"Vorschaubild fehlgeschlagen ({f}): {e}", flush=True)


def background(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


social_lock = threading.Lock()


def post_social():
    """Je Plattform höchstens ein Short pro Durchgang (siehe social.py). Nie zwei Durchgänge gleichzeitig."""
    if not social_lock.acquire(blocking=False):
        return
    try:
        social.run_once()
    finally:
        social_lock.release()
    try:  # Zahlen für den Reiter „Insta & TikTok“ (höchstens alle 30 Minuten, siehe social.STATS_EVERY)
        if social.summary()["buffer"]["connected"] or social.load()["instagram"]["token"]:
            social.refresh_stats()
    except Exception as e:  # nie den Planer stören
        store.log("error", f"Insta/TikTok-Zahlen: {e}")


vorbilder_lock = threading.Lock()
_vb_try = [0.0]   # letzter Versuch (ohne Netz nicht alle 30 s neu probieren)


def refresh_vorbilder():
    if not vorbilder_lock.acquire(blocking=False):
        return
    _vb_try[0] = time.time()
    try:
        ours = [u.get("title", "") for u in reversed(store.state().get("uploads", []))
                if u.get("channel") != "clips" and not u.get("lang")]
        vorbilder.refresh(ours[:40])
    finally:
        vorbilder_lock.release()


def scheduler():
    last_stats = last_sync = last_analytics = last_whop = last_social = 0.0
    while True:
        try:
            if time.time() - last_whop > whop.REFRESH_HOURS * 3600:
                last_whop = time.time()
                if whop.load():
                    background(whop.refresh)
            cfg = store.config()
            ag = agents.settings(cfg)
            if cfg["refresh_token"]:
                slot = store.due_slot() if ag["publisher"]["on"] else None
                if slot and store.ready_items():
                    post_ready(slot)  # fertiger Short aus dem Vorrat: nur hochladen, auch wenn gerade etwas rendert
                elif slot and not status["busy"]:
                    post_next(slot)
                # Firmen-Folge und langes Video rendern im Hintergrund, damit Sendeplätze weiterlaufen
                fslot = store.due_firma(cfg.get("firma_hour")) if ag["publisher"]["on"] else None
                if fslot and not status["busy"] and not work_lock.locked():
                    background(post_next, fslot, False, False, True)  # Firmen-Spiel: zusätzlich zu den normalen
                lslot = store.due_long(ag["publisher"].get("long_per_week", 0)) if ag["publisher"]["on"] else None
                if lslot and not fslot and not status["busy"] and not work_lock.locked():
                    background(post_next, lslot, False, True)
                if time.time() - last_stats > ag["analyst"]["minutes"] * 60:  # kostet kaum API-Quote
                    refresh_stats()
                    if ag["designer"]["on"]:
                        apply_branding()
                    last_stats = time.time()
            if comments.load()["settings"]["on"]:
                background(check_comments)
            if vorbilder.due() and time.time() - _vb_try[0] > 3600:  # Vorbilder: neueste Titel und Aufrufe (öffentlicher RSS-Feed, keine Quote)
                background(refresh_vorbilder)
            if time.time() - last_social > 5 * 60:  # die besten Shorts zu Instagram (Reel) und TikTok (Entwurf)
                last_social = time.time()
                background(post_social)
            if cfg["analytics_token"] and time.time() - last_analytics > ag["zuschauer"]["hours"] * 3600:
                last_analytics = time.time()
                refresh_analytics()
            if ag["autor"]["on"] and time.time() - last_sync > ag["autor"]["hours"] * 3600:
                sync_scripts()
                last_sync = time.time()
        except Exception:
            traceback.print_exc()
        time.sleep(30)


# --- Website -----------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "ShortsZentrale"

    def log_message(self, *args):
        pass

    def authorized(self):
        if not PASSWORD:
            return True
        expected = "Basic " + base64.b64encode(f"admin:{PASSWORD}".encode()).decode()
        if self.headers.get("Authorization") == expected:
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Shorts-Zentrale"')
        self.end_headers()
        return False

    def send(self, code, body, ctype="application/json; charset=utf-8", cache="no-store"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def send_file(self, path, ctype, download=None, ext="mp4"):
        """Datei mit Range-Unterstützung (damit man im Video-Player spulen kann)."""
        size = os.path.getsize(path)
        start, end, code = 0, size - 1, 200
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
            else:
                start = max(0, size - int(m.group(2)))
            if start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            code = 206
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-cache")
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if download:
            safe = re.sub(r"[^A-Za-z0-9._-]+", "-", download).strip("-") or "clip"
            self.send_header("Content-Disposition", f"attachment; filename=\"{safe}.{ext}\"; "
                             f"filename*=UTF-8''{urllib.parse.quote(download)}.{ext}")
        self.end_headers()
        try:
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(left, 256 * 1024))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path.startswith("/webhook/"):
            return self.send(200, {"ok": True, "info": "Shorts-Zentrale: Video-Webhook. Videos per POST schicken."})
        if not self.authorized():
            return
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            page = PAGE_HEAD + open(os.path.join(WEB, "index.html"), encoding="utf-8").read() + "</body></html>"
            return self.send(200, page, "text/html; charset=utf-8")
        if p.startswith("/static/"):
            return self.static_file(p[len("/static/"):])
        if p in ("/icon.png", "/favicon.ico"):
            return self.send(200, open(os.path.join(WEB, "icon.png"), "rb").read(), "image/png", cache="max-age=86400")
        if p.startswith("/relax-brand/"):
            name = p[len("/relax-brand/"):]
            if not re.fullmatch(r"quiet-corner-(banner-[ABC]\.jpg|profil-[ABC]\.png|kanaltext\.txt)", name):
                return self.send(404, {"error": "Nicht gefunden"})
            try:
                file = relax_brand_files()[name]
            except Exception as e:
                return self.send(500, {"error": f"Bilder konnten nicht gebaut werden: {e}"})
            typ = {"jpg": "image/jpeg", "png": "image/png", "txt": "text/plain; charset=utf-8"}[name.rsplit(".", 1)[1]]
            return self.send(200, open(file, "rb").read(), typ, cache="max-age=3600")
        if p == "/api/dashboard":
            if time.time() - _last_refresh[0] > 5 * 60:  # Website offen: Aufrufe frisch holen
                _last_refresh[0] = time.time()
                background(refresh_stats)
            return self.send(200, store.dashboard({"busy": status["busy"], "connect": status["connect"], "connect_clip": status["connect_clip"], "connect_relax": status["connect_relax"],
                                                   "version": VERSION, "oauth_page": OAUTH_PAGE,
                                                   "live_seq": live_since(10 ** 12)["seq"], "whop": whop.summary(),
                                                   "social": social.summary(), "social_view": social.overview(), "vorbilder": vorbilder.summary()},
                                                  working=tasks_now(), repo=bool(SCRIPTS_REPO)))
        if p == "/api/live":
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            try:
                since = int(q.get("since", ["0"])[0])
            except ValueError:
                since = 0
            return self.send(200, live_since(since))
        m = re.fullmatch(r"/api/clip/([a-z0-9-]+)/(\d+)\.(mp4|jpg)", p)
        if m:
            return self.clip_file(m.group(1), int(m.group(2)), m.group(3))
        if p == "/api/voice-sample.wav":
            return self.voice_sample()
        if p == "/api/preview.jpg":
            return self.preview()
        if p == "/api/analytics/callback":
            return self.analytics_callback()
        if p == "/api/tiktok/callback":
            return self.tiktok_callback()
        if p == "/api/social/paket.zip":  # beste Shorts + Texte, zum Planen ohne Entwickler-App
            dest = store.path("share", "paket.zip")
            try:
                social.build_package(dest)
            except ValueError as e:
                return self.send(404, {"error": str(e)})
            return self.send_file(dest, "application/zip", download="shorts-fuer-insta-und-tiktok", ext="zip")
        m = re.fullmatch(r"/api/share/([A-Za-z0-9_-]+)\.mp4", p)
        if m:
            u = next((x for x in store.state()["uploads"] if x.get("video_id") == m.group(1)), None)
            if not u or not os.path.exists(store.share_path(m.group(1))):
                return self.send(404, {"error": "Video nicht mehr gespeichert"})
            return self.send_file(store.share_path(m.group(1)), "video/mp4", download=u["title"])
        m = re.fullmatch(r"/api/thumbx/([a-z0-9-]+)-([AB])\.jpg", p)
        if m:
            return self.custom_thumb(m.group(1), m.group(2))
        m = re.fullmatch(r"/api/thumb/([a-z0-9-]+)\.jpg", p)
        if m:
            return self.thumb(m.group(1))
        self.send(404, {"error": "Nicht gefunden"})

    def analytics_callback(self):
        """Google hat über die Weiterleitungsseite einen Code geschickt: gegen einen Zugang tauschen."""
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        nonce = (q.get("state", [""])[0]).split(".")[0]
        ok = nonce and status["oauth_states"].pop(nonce, None)
        note = ""
        if q.get("error"):
            note = "abgebrochen"
        elif not ok:
            note = "ungueltig"
        else:
            cfg = store.config()
            try:
                token, scopes = yt.analytics_exchange(cfg["analytics_client_id"], cfg["analytics_client_secret"],
                                                      OAUTH_PAGE, q.get("code", [""])[0])
                store.save_config(analytics_token=token, analytics_scopes=scopes)
                comments_reset_access()
                store.write("analytics.json", {**store.read("analytics.json", {"videos": {}}), "error": None})
                store.log("ok", "Zuschauer-Daten verbunden. Die ersten Werte kommen in den nächsten Minuten.")
                background(refresh_analytics)
                note = "ok"
            except Exception as e:
                store.log("error", f"Zuschauer-Daten: Verbindung fehlgeschlagen: {e}")
                note = "fehler"
        self.send_response(303)
        self.send_header("Location", f"/?analytics={note}#zuschauer")
        self.end_headers()

    def voice_sample(self):
        """Ein Satz mit dem eingestellten Sprechtempo, zum Probehören im Panel des Sprechers."""
        import io
        import wave

        import numpy as np
        from piper import SynthesisConfig

        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        ag = agents.settings(store.config())
        try:
            tempo = agents.validate("sprecher", {"tempo": q.get("tempo", [ag["sprecher"]["tempo"]])[0]})["tempo"]
        except ValueError:
            tempo = ag["sprecher"]["tempo"]
        voice = tts()
        cfg = SynthesisConfig(length_scale=round(agents.BASE_SPEED * 100 / tempo, 3))
        text = "Hallo! So klingt die Stimme deiner Shorts mit diesem Sprechtempo."
        conf = store.config()
        which = q.get("fish", [""])[0]
        if which and conf.get("fish_key"):  # Hörprobe der Fish-Audio-Stimme (normal oder dunkel)
            import fishtts
            vid = {"dark": conf.get("fish_voice_dark"), "warm": conf.get("fish_voice_warm")}.get(which) or conf.get("fish_voice")
            if not vid:
                return self.send(400, {"error": "Bitte zuerst eine Stimme eintragen."})
            try:
                with working("sprecher", task="Spricht eine Hörprobe mit Fish Audio"):
                    audio = fishtts.speak("Hallo! So klingt die neue Stimme deiner Shorts.", conf["fish_key"], vid,
                                          voice.config.sample_rate)
            except Exception as e:
                return self.send(502, {"error": str(e)})
        elif q.get("stimme", [""])[0]:  # Hörprobe einer Cartoon-Stimme (z. B. die freundliche für Geschichten)
            import make_short
            name = q["stimme"][0]
            if name not in make_short.VOICES:
                return self.send(400, {"error": "Diese Stimme gibt es nicht."})
            pitch, slower, _ = make_short.VOICES[name]
            story = "Meine Oma hat mir einen alten Schlüssel geschenkt. Sie hat nur gelächelt und gesagt: Du wirst schon sehen."
            with working("sprecher", task="Spricht eine Hörprobe"):
                audio = make_short.speak_piper(voice, story, name, length_scale=cfg.length_scale * slower * pitch)
                audio = make_short.voice_color(audio, voice.config.sample_rate, name)
        else:
            with working("sprecher", task="Spricht eine Hörprobe"):
                audio = np.concatenate([c.audio_float_array for c in voice.synthesize(text, syn_config=cfg)])
        buf = io.BytesIO()
        with wave.open(buf, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(voice.config.sample_rate)
            f.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
        self.send(200, buf.getvalue(), "audio/wav")

    def preview(self):
        """Bild aus dem nächsten Video mit dem Look, den das Video-Studio gerade wählen würde."""
        import io

        from make_short import Scene, estimated_timings

        planned = store.planned_queue()
        if not planned:
            return self.send(404, {"error": "Die Warteschlange ist leer."})
        spec = planned[0][1]
        look = agents.apply_look(store.next_look(), agents.settings(store.config()))
        spec = {**spec, **look}
        timings, total = estimated_timings(spec)
        with working("studio", task="Rendert eine Vorschau"):
            img = Scene(spec, timings, total).frame(min(2.2, timings[0][1]))
        buf = io.BytesIO()
        img.resize((540, 960)).save(buf, "JPEG", quality=86)
        self.send(200, buf.getvalue(), "image/jpeg")

    def clip_file(self, cid, n, ext):
        try:
            c = clips.load(cid)
            clip = next(x for x in c["clips"] if x["n"] == n)
            path = clips.clip_path(c, clip, ext)
        except (OSError, ValueError, StopIteration):
            return self.send(404, {"error": "Clip nicht gefunden"})
        if not os.path.exists(path):
            return self.send(404, {"error": "Clip nicht gefunden"})
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        if ext == "jpg":
            return self.send(200, open(path, "rb").read(), "image/jpeg", cache="max-age=3600")
        self.send_file(path, "video/mp4", download=clip["title"] if q.get("download") else None)

    STATIC_TYPES = {".js": "text/javascript; charset=utf-8", ".html": "text/html; charset=utf-8",
                    ".css": "text/css; charset=utf-8", ".woff2": "font/woff2", ".jpg": "image/jpeg",
                    ".png": "image/png", ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8"}

    def static_file(self, rel):
        """Feste Dateien der Website (HyperFrames-Player, Film, Schriften) aus web/static."""
        ext = os.path.splitext(rel)[1].lower()
        root = os.path.realpath(os.path.join(WEB, "static"))
        path = os.path.realpath(os.path.join(root, rel))
        if (not re.fullmatch(r"[A-Za-z0-9._/-]+", rel) or ".." in rel.split("/")
                or not path.startswith(root + os.sep) or ext not in self.STATIC_TYPES or not os.path.isfile(path)):
            return self.send(404, {"error": "Nicht gefunden"})
        with open(path, "rb") as f:
            return self.send(200, f.read(), self.STATIC_TYPES[ext], cache="max-age=86400")

    def thumb(self, slug):
        if slug.startswith("clip-"):  # geposteter Clip: Vorschaubild aus der Kampagne
            file = clips.thumb_file(slug)
            if file and os.path.exists(file):
                return self.send(200, open(file, "rb").read(), "image/jpeg", cache="max-age=86400")
            return self.send(404, {"error": "Unbekanntes Video"})
        file = store.path("thumbs", slug + ".jpg")
        if not os.path.exists(file):
            spec = store.find_spec(slug)
            if not spec:
                return self.send(404, {"error": "Unbekanntes Video"})
            from make_short import render_thumbnail
            render_thumbnail(spec, file)
        self.send(200, open(file, "rb").read(), "image/jpeg", cache="max-age=86400")

    def custom_thumb(self, slug, variant):
        """Eigenes Thumbnail (Variante A oder B). Fehlt es, baut die App es jetzt (dauert ein paar Sekunden)."""
        file = store.thumb_path(slug, variant)
        if not os.path.exists(file):
            spec = store.find_spec(slug)
            if not spec:
                return self.send(404, {"error": "Unbekanntes Video"})
            with thumb_lock:
                if not os.path.exists(file):
                    import thumbnail
                    thumbnail.build(spec, os.path.dirname(file))
        self.send(200, open(file, "rb").read(), "image/jpeg", cache="max-age=600")

    def tiktok_callback(self):
        """TikTok hat über die Weiterleitungsseite einen Code geschickt (state beginnt mit "tt-")."""
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        nonce = (q.get("state", [""])[0]).split(".")[0]
        ok = nonce.startswith("tt-") and status["oauth_states"].pop(nonce, None)
        if q.get("error"):
            note = "abgebrochen"
        elif not ok:
            note = "ungueltig"
        else:
            try:
                social.tt_exchange(q.get("code", [""])[0], OAUTH_PAGE)
                store.log("ok", "TikTok verbunden. Die besten Shorts kommen ab jetzt als Entwurf in deine TikTok-App.")
                note = "ok"
            except Exception as e:
                store.log("error", f"TikTok: Verbindung fehlgeschlagen: {e}")
                note = "fehler"
        self.send_response(303)
        self.send_header("Location", f"/?tiktok={note}#kanal")
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/webhook/video":
            return webhook_video(self)
        if not self.authorized():
            return
        if path == "/api/campaign/upload":
            return self.campaign_upload()
        if path == "/api/whop/logo":
            return self.whop_logo()
        p, data = self.path, self.body()
        if p == "/api/settings":
            changes = {}
            if isinstance(data.get("stock_key"), str):
                changes["stock_key"] = data["stock_key"].strip()  # leer = Clips ausschalten
            if isinstance(data.get("fish_key"), str):
                changes["fish_key"] = data["fish_key"].strip()  # leer = eingebaute Stimme
            for k in ("fish_voice", "fish_voice_dark", "fish_voice_warm"):
                if isinstance(data.get(k), str):
                    import fishtts
                    vid = fishtts.voice_id(data[k])
                    if data[k].strip() and not vid:
                        return self.send(400, {"error": "Das ist keine Fish-Audio-Stimme. Bitte den Link der Stimme "
                                                        "(fish.audio/m/…) oder ihre ID einfügen."})
                    changes[k] = vid
            for key in ("client_id", "client_secret", "analytics_client_id", "analytics_client_secret"):
                if isinstance(data.get(key), str) and data[key].strip():
                    changes[key] = data[key].strip()
            if any(c in changes.get(k, "") for k in ("client_secret", "analytics_client_secret") for c in "*•"):
                return self.send(400, {"error": "Das ist nur die verdeckte Anzeige. Bitte in Google Cloud "
                                                "„Secret hinzufügen“ klicken und den neuen Schlüssel kopieren."})
            if any(changes.get(k) and not changes[k].endswith(".apps.googleusercontent.com")
                   for k in ("client_id", "analytics_client_id")):
                return self.send(400, {"error": "Die Client-ID endet auf .apps.googleusercontent.com. Bitte prüfen."})
            if changes.get("client_id") and changes["client_id"] != store.config()["client_id"]:
                changes["refresh_token"] = ""  # die alte Verbindung gehört zum alten Client
            for key, label in (("post_hours", ""), ("post_hours_weekend", " fürs Wochenende")):
                if key in data:
                    hours = sorted({int(h) for h in data[key] if 0 <= int(h) <= 23})
                    if not 1 <= len(hours) <= 10:
                        return self.send(400, {"error": f"Bitte 1 bis 10 Sendezeiten{label} wählen."})
                    changes[key] = hours
            if data.get("privacy") in ("public", "unlisted", "private"):
                changes["privacy"] = data["privacy"]
            store.save_config(**changes)
            return self.send(200, {"ok": True})
        if p == "/api/connect":
            cfg = store.config()
            if not (cfg["client_id"] and cfg["client_secret"]):
                return self.send(400, {"error": "Bitte zuerst Client-ID und Clientschlüssel speichern."})
            status["connect"] = {"status": "start"}
            background(connect_channel)
            return self.send(200, {"ok": True})
        if p == "/api/clipchannel/connect":
            cfg = store.config()
            if not (cfg["client_id"] and cfg["client_secret"] and cfg["refresh_token"]):
                return self.send(400, {"error": "Bitte zuerst deinen Hauptkanal verbinden."})
            status["connect_clip"] = {"status": "start"}
            background(connect_clip_channel)
            return self.send(200, {"ok": True})
        if p == "/api/clipchannel/disconnect":
            store.save_config(clip_token="", clip_expired=False)
            store.write("clipchannel.json", None)
            status["connect_clip"] = {"status": "idle"}
            store.log("warn", "Clip-Kanal getrennt. Clips laufen wieder auf dem Hauptkanal mit.")
            return self.send(200, {"ok": True})
        if p == "/api/relax/connect":
            cfg = store.config()
            if not (cfg["client_id"] and cfg["client_secret"] and cfg["refresh_token"]):
                return self.send(400, {"error": "Bitte zuerst deinen Hauptkanal verbinden."})
            status["connect_relax"] = {"status": "start"}
            background(connect_relax_channel)
            return self.send(200, {"ok": True})
        if p == "/api/relax/disconnect":
            store.save_config(relax_token="", relax_expired=False)
            store.write("relaxchannel.json", None)
            status["connect_relax"] = {"status": "idle"}
            store.log("warn", "Entspannungskanal getrennt.")
            return self.send(200, {"ok": True})
        if p == "/api/relax/settings":
            import entspannung
            ch = {}
            if "minutes" in data:   # alt: feste Länge in Minuten
                if int(data["minutes"]) not in entspannung.MINUTES:
                    return self.send(400, {"error": "Länge: 3, 5, 8 oder 10 Stunden."})
                ch["relax_minutes"] = int(data["minutes"])
                ch["relax_length"] = str(int(data["minutes"]))
            if "length" in data:
                with store.LOCK:   # eine neue Wahl hebt die Notbremse wieder auf (z. B. nach youtube.com/verify)
                    st0 = store.state()
                    st0["relax_cap"] = None
                    store.write("state.json", st0)
                v = str(data["length"])
                if v != "auto" and (not v.isdigit() or int(v) not in entspannung.MINUTES):
                    return self.send(400, {"error": "Länge: automatisch oder 3, 5, 8, 10 Stunden."})
                ch["relax_length"] = v
            if "hour" in data:
                if int(data["hour"]) not in entspannung.HOURS:
                    return self.send(400, {"error": "Uhrzeit von 0 bis 23."})
                ch["relax_hour"] = int(data["hour"])
            if "on" in data:
                ch["relax_on"] = bool(data["on"])
            if "per_day" in data:
                if int(data["per_day"]) not in (1, 2, 3):
                    return self.send(400, {"error": "1, 2 oder 3 Videos am Tag."})
                ch["relax_per_day"] = int(data["per_day"])
            if "shorts" in data:
                ch["relax_shorts"] = bool(data["shorts"])
            if "banner" in data:
                if data["banner"] not in entspannung.BRAND_VARIANTS:
                    return self.send(400, {"error": "Banner A, B oder C."})
                ch["relax_banner"] = data["banner"]
            store.save_config(**ch)
            return self.send(200, {"ok": True})
        if p == "/api/relax/branding":
            if not store.config()["relax_token"]:
                return self.send(400, {"error": "Der Entspannungskanal ist nicht verbunden."})
            v = data.get("banner") or store.config().get("relax_banner", "A")
            store.save_config(relax_banner=v)
            background(relax_apply_branding, v)
            return self.send(200, {"ok": True})
        if p == "/api/relax/now":
            if not store.config()["relax_token"]:
                return self.send(400, {"error": "Der Entspannungskanal ist nicht verbunden."})
            if relax_lock.locked():
                return self.send(400, {"error": "Es wird gerade schon ein Entspannungsvideo gebaut."})
            background(post_relax, True)
            return self.send(200, {"ok": True})
        if p == "/api/socials":
            socials = dict(store.config()["socials"])
            for k in clips.PLATFORMS:
                if k in data:
                    v = str(data[k] or "").strip().split("?")[0]
                    v = re.sub(r"^https?://(www\.)?(tiktok\.com|instagram\.com)/", "", v).strip("/").lstrip("@")
                    if v and not re.fullmatch(r"[A-Za-z0-9._]{1,30}", v):
                        return self.send(400, {"error": "Bitte nur den Namen eingeben, zum Beispiel @deinname."})
                    socials[k] = v
            store.save_config(socials=socials)
            return self.send(200, {"ok": True, "socials": socials})
        if p == "/api/social/settings":
            try:
                keys = {k: data[k] for k in ("app_id", "app_secret", "client_key", "client_secret") if k in data}
                return self.send(200, social.set_settings(str(data.get("platform", "")), on=data.get("on"),
                                                          per_day=data.get("per_day"), **keys))
            except (ValueError, TypeError) as e:
                return self.send(400, {"error": str(e)})
        if p == "/api/social/instagram/connect":
            try:
                r = social.ig_connect(str(data.get("app_id", "")), str(data.get("app_secret", "")), str(data.get("token", "")))
                store.log("ok", f"Instagram verbunden: @{r['username']}.")
                return self.send(200, r)
            except (ValueError, KeyError, social.ApiError, OSError) as e:
                return self.send(400, {"error": f"Instagram: {e}"})
        if p == "/api/social/tiktok/start":
            if not OAUTH_PAGE:
                return self.send(400, {"error": "Keine Weiterleitungsseite eingestellt (SCRIPTS_REPO oder OAUTH_PAGE)."})
            origin = str(data.get("origin", ""))
            if not re.fullmatch(r"https?://[\w.\-\[\]:]+", origin):
                return self.send(400, {"error": "Ungültige Adresse."})
            nonce = "tt-" + secrets.token_urlsafe(16)
            status["oauth_states"] = {**dict(list(status["oauth_states"].items())[-5:]), nonce: origin}
            state = nonce + "." + base64.urlsafe_b64encode(origin.encode()).decode().rstrip("=")
            try:
                return self.send(200, {"url": social.tt_auth_url(OAUTH_PAGE, state)})
            except ValueError as e:
                return self.send(400, {"error": str(e)})
        if p == "/api/social/test":
            try:
                return self.send(200, {"ok": True, "message": social.test(str(data.get("platform", "")))})
            except (ValueError, KeyError, social.ApiError, OSError) as e:
                return self.send(400, {"error": str(e)})
        if p == "/api/social/disconnect":
            d = social.load()
            plat = str(data.get("platform", ""))
            if plat == "instagram":
                d["instagram"].update(token="", ig_id="", username="", page="", on=False, error=None)
            elif plat == "tiktok":
                d["tiktok"].update(access="", refresh="", expires=0, open_id="", username="", on=False, error=None)
            else:
                return self.send(400, {"error": "Unbekannte Plattform."})
            social.save(d)
            b = social.buffer_load()
            if (b.get("channels") or {}).pop(plat, None):
                social.buffer_save(b if b["channels"] else {})
            return self.send(200, {"ok": True})
        if p == "/api/social/buffer/connect":
            try:
                r = social.buffer_connect(str(data.get("key", "")))
                store.log("ok", "Buffer verbunden: " + ", ".join({"instagram": "Instagram", "tiktok": "TikTok"}[k] for k in r["found"]) + ".")
                return self.send(200, r)
            except (ValueError, KeyError, social.ApiError, OSError) as e:
                return self.send(400, {"error": str(e)})
        if p == "/api/social/buffer/disconnect":
            social.buffer_disconnect()
            return self.send(200, {"ok": True})
        if p == "/api/social/refresh":  # Knopf „Zahlen neu holen“ im Reiter Insta & TikTok
            try:
                social.refresh_stats(force=True)
            except Exception as e:
                return self.send(400, {"error": str(e)[:200]})
            return self.send(200, {"ok": True})
        if p == "/api/social/profil":  # Checkliste „Profil fertig?“
            try:
                return self.send(200, {"done": social.set_done(str(data.get("key", "")), bool(data.get("done")))})
            except ValueError as e:
                return self.send(400, {"error": str(e)})
        if p == "/api/social/now":
            plat = str(data.get("platform", ""))
            if plat not in social.DEFAULTS:
                return self.send(400, {"error": "Unbekannte Plattform."})
            if not social.summary()[plat]["connected"]:
                return self.send(400, {"error": "Bitte zuerst verbinden."})
            u = social.pick(store.posted_items(), plat, store.now())
            if not u:
                return self.send(400, {"error": "Gerade kein passender Short (der beste der letzten 2 Tage ist schon dort)."})
            def once():
                with social_lock:
                    social.post_now(plat)
            background(once)
            return self.send(200, {"ok": True, "title": u.get("title", "")})
        if p == "/api/short/shared":
            try:
                store.set_short_shared(str(data.get("video_id", "")), str(data.get("platform", "")), bool(data.get("done")))
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            return self.send(200, {"ok": True})
        if p == "/api/clip/shared":
            try:
                clips.set_shared(str(data.get("id", "")), int(data.get("n", 0)), str(data.get("platform", "")),
                                 bool(data.get("done")))
            except (OSError, ValueError, TypeError) as e:
                return self.send(400, {"error": str(e) if isinstance(e, ValueError) else "Unbekannter Clip."})
            return self.send(200, {"ok": True})
        if p == "/api/analytics/start":
            cfg = store.config()
            if not (cfg["analytics_client_id"] and cfg["analytics_client_secret"]):
                return self.send(400, {"error": "Bitte zuerst Client-ID und Clientschlüssel der Webanwendung speichern."})
            if not OAUTH_PAGE:
                return self.send(400, {"error": "Keine Weiterleitungsseite eingestellt (SCRIPTS_REPO oder OAUTH_PAGE)."})
            origin = str(data.get("origin", ""))
            if not re.fullmatch(r"https?://[\w.\-\[\]:]+", origin):
                return self.send(400, {"error": "Ungültige Adresse."})
            nonce = secrets.token_urlsafe(16)
            status["oauth_states"] = {**dict(list(status["oauth_states"].items())[-5:]), nonce: origin}
            state = nonce + "." + base64.urlsafe_b64encode(origin.encode()).decode().rstrip("=")
            return self.send(200, {"url": yt.analytics_auth_url(cfg["analytics_client_id"], OAUTH_PAGE, state)})
        if p == "/api/comments/settings":
            try:
                s = comments.set_settings(on=data.get("on"), mode=data.get("mode"), per_day=data.get("per_day"))
            except (ValueError, TypeError) as e:
                return self.send(400, {"error": str(e)})
            if s["on"]:
                background(check_comments, True)
            return self.send(200, {"ok": True, "settings": s})
        if p == "/api/comments/check":
            background(check_comments, True)
            return self.send(200, {"ok": True})
        if p in ("/api/comments/reply", "/api/comments/dismiss"):
            cid, text = str(data.get("id", "")), str(data.get("text", "")).strip()
            with store.LOCK:
                d = comments.load()
                item = next((t for t in d["todo"] if t["id"] == cid), None)
                if not item:
                    return self.send(404, {"error": "Diesen Kommentar gibt es nicht mehr."})
                if p.endswith("dismiss"):
                    d["todo"] = [t for t in d["todo"] if t["id"] != cid]
                    comments.save(d)
                    return self.send(200, {"ok": True})
            if not 1 <= len(text) <= 500:
                return self.send(400, {"error": "Die Antwort muss 1 bis 500 Zeichen lang sein."})
            cfg = store.config()
            if comments.access(cfg) != "ok":
                return self.send(400, {"error": "Zum Antworten bitte zuerst im Reiter Zuschauer neu verbinden."})
            try:
                yt.reply(yt.reply_client(cfg), cid, text)
            except Exception as e:
                return self.send(400, {"error": comments.error_text(e)[1]})
            with store.LOCK:
                d = comments.load()
                entry = {k: v for k, v in item.items() if k not in ("draft", "why", "at")}
                comments.record_sent(d, entry, text, by="du" if text != item.get("draft") else "freigabe")
                comments.save(d)
            return self.send(200, {"ok": True})
        if p == "/api/analytics/disconnect":
            store.save_config(analytics_token="", analytics_scopes="")
            store.log("warn", "Zuschauer-Daten getrennt.")
            return self.send(200, {"ok": True})
        if p == "/api/disconnect":
            store.save_config(refresh_token="", expired=False)
            store.write("channel.json", None)
            status["connect"] = {"status": "idle"}
            store.log("warn", "Kanal getrennt.")
            return self.send(200, {"ok": True})
        if p == "/api/post-now":
            if not store.config()["refresh_token"]:
                return self.send(400, {"error": "Es ist noch kein Kanal verbunden."})
            if status["busy"]:
                return self.send(409, {"error": "Es läuft gerade schon ein Upload."})
            status["busy"] = "Startet …"
            background(post_next, None, True)
            return self.send(200, {"ok": True})
        if p == "/api/agent":
            try:
                agent = str(data.get("id", ""))
                changes = agents.validate(agent, data.get("settings") or {})
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            saved = store.config().get("agents") or {}
            saved[agent] = {**(saved.get(agent) or {}), **changes}
            store.save_config(agents=saved)
            if agent == "clipper" and changes.get("freigabe") is False:
                clips.approve_waiting()
            return self.send(200, {"ok": True, "settings": agents.settings(store.config())[agent]})
        if p == "/api/agent/run":
            return self.run_agent(str(data.get("id", "")))
        if p == "/api/approval":
            store.save_config(approval=bool(data.get("on")))
            store.log("info", "Freigabe-Pflicht eingeschaltet: Nur freigegebene Videos gehen online."
                      if data.get("on") else "Freigabe-Pflicht ausgeschaltet: Alle Videos gehen automatisch online.")
            return self.send(200, {"ok": True})
        if p in ("/api/approve", "/api/reject", "/api/restore"):
            name = str(data.get("file", ""))
            try:
                {"/api/approve": store.approve, "/api/reject": store.reject, "/api/restore": store.restore}[p](name)
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            if p == "/api/reject":
                store.log("warn", f"Skript abgelehnt: {name}")
            return self.send(200, {"ok": True})
        if p == "/api/campaign/link":
            url = str(data.get("url") or "").strip()
            if not data.get("rights"):
                return self.send(400, {"error": "Bitte bestätigen, dass du das Video verwenden darfst."})
            try:
                clips.check_url(url)
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            prog = str(data.get("program") or "")
            item = whop.find(prog) if prog else None
            if prog and not item:
                return self.send(400, {"error": "Unbekannte Kampagne."})
            store.log("info", "Link verknüpft, das Video wird geladen" + (f" (für „{item['title']}“)" if item else ""),
                      agent="clipper", kind="input")
            background(_download, url, True, str(data.get("credit") or (item or {}).get("brand") or "")[:80],
                       (str(data.get("name") or "").strip()[:80] or None), "whop" if item else "link", item and item["id"])
            return self.send(200, {"ok": True, "text": "Verknüpft. Das Video wird geladen und dann geschnitten."})
        if p == "/api/whop/add":
            try:
                item = whop.add(str(data.get("url") or ""))
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            except Exception:
                return self.send(502, {"error": "Die Kampagnen-Seite war gerade nicht erreichbar. Bitte gleich nochmal."})
            store.log("info", f"Whop-Kampagne verknüpft: {item['title']}", agent="clipper", kind="input")
            return self.send(200, {"ok": True, "item": item})
        if p == "/api/whop/rules":
            try:
                rules = whop.set_rules(str(data.get("id") or ""), data)
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            store.log("info", "Vorgaben der Whop-Kampagne gespeichert", agent="clipper", kind="input")
            return self.send(200, {"ok": True, "rules": rules})
        if p == "/api/thumb/retry":  # fehlende Thumbnails der letzten Uploads nachholen
            background(retry_thumbs)
            return self.send(200, {"ok": True})
        if p == "/api/thumb/set":  # andere Thumbnail-Variante für ein hochgeladenes Video setzen
            vid, variant = str(data.get("video_id") or ""), str(data.get("variant") or "")
            u = next((x for x in store.state()["uploads"] if x.get("video_id") == vid and x.get("kind") != "clip"), None)
            if not u or variant not in ("A", "B"):
                return self.send(400, {"error": "Unbekanntes Video oder Variante."})
            spec = store.find_spec(u["slug"])
            file = store.thumb_path(u["slug"], variant)
            try:
                if not os.path.exists(file):
                    if not spec:
                        return self.send(400, {"error": "Das Skript zu diesem Video gibt es nicht mehr."})
                    import thumbnail
                    with thumb_lock:
                        thumbnail.build(spec, os.path.dirname(file))
            except Exception as e:  # noqa: BLE001
                return self.send(500, {"error": f"Thumbnail nicht erstellt: {e}"})
            if not apply_thumb(vid, {variant: file}, variant):
                st = store.state().get("thumb_status") or {}
                msg = ("YouTube nimmt eigene Thumbnails erst, wenn dein Kanal bestätigt ist (youtube.com/verify)."
                       if st.get("reason") == "verify" else "YouTube hat das Thumbnail abgelehnt: " + st.get("reason", ""))
                return self.send(400, {"error": msg})
            store.set_upload_thumb(vid, variant)
            store.log("ok", f"Thumbnail {variant} gesetzt: {u['title']}", agent="publisher", kind="input")
            return self.send(200, {"ok": True})
        if p == "/api/clipi/now":
            if not store.config()["clip_token"]:
                return self.send(400, {"error": "Der Clip-Kanal ist nicht verbunden."})
            if not clips.ready_clips(auto=True):
                return self.send(400, {"error": "Es wartet gerade kein fertiger Clip."})
            if clipi_lock.locked():
                return self.send(400, {"error": "Clipi lädt gerade schon einen Clip hoch."})
            background(post_clip_slot, None, True)
            return self.send(200, {"ok": True})
        if p == "/api/money/add":
            try:
                item = money.add(data.get("amount"), data.get("currency") or "€", data.get("source") or "Content Rewards",
                                 data.get("date"), data.get("note"))
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            store.log("info", "Auszahlung eingetragen: %s %s (%s)" % (item["currency"], ("%.2f" % item["amount"]).replace(".", ","), item["source"]))
            return self.send(200, {"ok": True, "item": item})
        if p == "/api/money/delete":
            if not money.remove(str(data.get("id") or "")):
                return self.send(400, {"error": "Diese Auszahlung gibt es nicht."})
            return self.send(200, {"ok": True})
        if p in ("/api/whop/refresh", "/api/whop/delete"):
            pid = str(data.get("id") or "")
            if not whop.find(pid):
                return self.send(400, {"error": "Unbekannte Whop-Kampagne."})
            if p.endswith("delete"):
                whop.remove(pid)
                store.log("warn", "Whop-Kampagne entfernt (Clips bleiben)", agent="clipper")
            else:
                whop.refresh(pid)
            return self.send(200, {"ok": True})
        if p == "/api/whop/video":
            item = whop.find(str(data.get("id") or ""))
            url = str(data.get("url") or "").strip()
            if not item:
                return self.send(400, {"error": "Unbekannte Whop-Kampagne."})
            if not data.get("rights"):
                return self.send(400, {"error": "Bitte bestätigen, dass die Kampagne das Schneiden erlaubt."})
            try:
                clips.check_url(url)
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            store.log("info", f"Video für „{item['title']}“ wird geladen", agent="clipper", kind="input")
            background(_download, url, True, item.get("brand") or "", item["title"][:80], "whop", item["id"])
            return self.send(200, {"ok": True, "text": "Das Video wird geladen und für diese Kampagne geschnitten."})
        if p in ("/api/campaign/confirm", "/api/campaign/retry", "/api/campaign/delete"):
            cid = str(data.get("id", ""))
            try:
                if p.endswith("confirm"):
                    c = clips.confirm(cid, data.get("credit"))
                    store.log("info", f"Rechte bestätigt, wird geschnitten: {c['name']}", agent="clipper", kind="input")
                elif p.endswith("retry"):
                    clips.retry(cid)
                else:
                    name = clips.load(cid)["name"]
                    clips.delete(cid)
                    store.log("warn", f"Kampagne gelöscht: {name}", agent="clipper")
            except (OSError, ValueError) as e:
                return self.send(400, {"error": str(e) if isinstance(e, ValueError) else "Unbekannte Kampagne."})
            _clip_wake.set()
            return self.send(200, {"ok": True})
        if p == "/api/clip":
            try:
                c = clips.set_clip(str(data.get("id", "")), int(data.get("n", 0)), str(data.get("action", "")),
                                   data.get("title"))
            except (OSError, ValueError, TypeError) as e:
                return self.send(400, {"error": str(e) if isinstance(e, ValueError) else "Unbekannter Clip."})
            if data.get("action") == "reject":
                store.log("warn", f"Clip abgelehnt: {c['name']} #{data.get('n')}", agent="clipper")
            return self.send(200, {"ok": True})
        if p == "/api/clip/post":
            if not (store.config()["refresh_token"] or store.config()["clip_token"]):
                return self.send(400, {"error": "Es ist noch kein Kanal verbunden."})
            if status["busy"]:
                return self.send(409, {"error": "Es läuft gerade schon ein Upload."})
            try:
                cid, n = str(data.get("id", "")), int(data.get("n", 0))
                clip = next(x for x in clips.load(cid)["clips"] if x["n"] == n)
            except (OSError, ValueError, TypeError, StopIteration):
                return self.send(400, {"error": "Unbekannter Clip."})
            if clip["status"] in ("gepostet", "abgelehnt"):
                return self.send(400, {"error": "Dieser Clip kann nicht gepostet werden."})
            status["busy"] = "Startet …"
            background(post_clip_now, cid, n)
            return self.send(200, {"ok": True, "text": "Der Clip wird hochgeladen."})
        if p == "/api/sync":
            background(sync_scripts)
            background(refresh_stats)
            background(refresh_analytics)
            return self.send(200, {"ok": True})
        self.send(404, {"error": "Nicht gefunden"})


    def whop_logo(self):
        """Logo (PNG) einer Whop-Kampagne als Datei-Body: ?id=…  Ohne Datei (Länge 0) wird das Logo entfernt."""
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        pid = q.get("id", [""])[0]
        if not whop.find(pid):
            return self.send(400, {"error": "Unbekannte Whop-Kampagne."})
        n = int(self.headers.get("Content-Length") or 0)
        target = clips.logo_path(pid)
        if n == 0:
            if os.path.exists(target):
                os.remove(target)
            return self.send(200, {"ok": True})
        if n > 5_000_000:
            return self.send(400, {"error": "Das Logo ist zu groß (höchstens 5 MB)."})
        data = self.rfile.read(n)
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return self.send(400, {"error": "Bitte eine PNG-Datei nehmen."})
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)
        store.log("info", "Logo der Whop-Kampagne gespeichert", agent="clipper", kind="input")
        return self.send(200, {"ok": True})

    def campaign_upload(self):
        """Upload eines Videos von der Website, als Datei-Body (?name=…&credit=…&rights=1&filename=…)."""
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        one = lambda k: q.get(k, [""])[0]
        if one("rights") != "1":
            return self.send(400, {"error": "Bitte bestätigen, dass du das Video verwenden darfst."})
        item = whop.find(one("program")) if one("program") else None
        if one("program") and not item:
            return self.send(400, {"error": "Unbekannte Kampagne."})
        try:
            mode = "" if item else one("clipi")  # Clipi-Warteschlange: "ganz" (so posten) oder "kurz" (~20-s-Clips)
            c = clips.add_stream(self.rfile, int(self.headers.get("Content-Length") or 0), one("filename"),
                                 "clipi" if mode else "upload", True, one("credit") or (item or {}).get("brand", ""),
                                 one("name") or None, ready=mode == "ganz", quick=mode == "kurz")
        except ValueError as e:
            return self.send(400, {"error": str(e)})
        if item:
            c = clips.update(c["id"], lambda k: k.__setitem__("program", item["id"]))
        _clip_wake.set()
        return self.send(200, {"ok": True, "campaign": c["id"]})


RUNNERS = {"autor": sync_scripts, "analyst": refresh_stats, "zuschauer": refresh_analytics,
           "designer": lambda: apply_branding(force=True)}


def _run_agent(self, agent):
    cfg = store.config()
    if agent == "publisher":
        if not cfg["refresh_token"]:
            return self.send(400, {"error": "Es ist noch kein Kanal verbunden."})
        if status["busy"]:
            return self.send(409, {"error": "Es läuft gerade schon ein Upload."})
        status["busy"] = "Startet …"
        background(post_next, None, True)
        return self.send(200, {"ok": True, "text": "Das nächste Video wird erstellt und hochgeladen. Das dauert ein paar Minuten."})
    if agent == "clipper":
        background(clips.scan_inbox, agents.settings(cfg)["clipper"]["auto_start"])
        _clip_wake.set()
        return self.send(200, {"ok": True, "text": "Der Clipper prüft den Eingang. Neue Videos erscheinen gleich im Bereich Kampagnen."})
    if agent not in RUNNERS:
        return self.send(400, {"error": "Dieser Agent lässt sich nicht von Hand starten."})
    if agent in tasks_now():
        return self.send(409, {"error": "Der Agent arbeitet gerade schon."})
    if agent in ("analyst", "designer") and not cfg["refresh_token"]:
        return self.send(400, {"error": "Es ist noch kein Kanal verbunden."})
    if agent == "zuschauer" and not cfg["analytics_token"]:
        return self.send(400, {"error": "Die Zuschauer-Daten sind noch nicht verbunden."})
    if agent == "autor" and not SCRIPTS_REPO:
        return self.send(400, {"error": "Kein Skript-Repo eingestellt (SCRIPTS_REPO)."})
    start_work(agent)  # sofort sichtbar, auch bevor der Thread startet

    def job():
        try:
            RUNNERS[agent]()
        finally:
            stop_work(agent)
    background(job)
    return self.send(200, {"ok": True, "text": "Läuft."})


Handler.run_agent = _run_agent


def main():
    store.init()
    store.LISTENERS.append(live_push)
    clips.stale_cleanup()
    threading.Thread(target=scheduler, daemon=True).start()
    threading.Thread(target=clip_worker, daemon=True).start()
    threading.Thread(target=clipi_worker, daemon=True).start()
    threading.Thread(target=relax_worker, daemon=True).start()
    threading.Thread(target=ready_worker, daemon=True).start()
    background(warm_thumbs)
    print(f"Shorts-Zentrale läuft auf Port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
