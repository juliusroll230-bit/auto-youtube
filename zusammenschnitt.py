"""Sonntags-Zusammenschnitt (Phase G, seit 26.11.2026, Julius' Wunsch).

Sonntags um 17 Uhr kommt statt des normalen langen Videos ein Zusammenschnitt der besten Shorts der Woche
auf den Hauptkanal. Gewählt wird fair mit learn.relative (jeder Short gegen die Shorts der Nachbartage), nur eigene
KI-Shorts des Hauptkanals: keine Kampagnen-Clips, keine Clipi-Uploads, keine Firmen-Folgen, keine langen Videos.

Länge: mindestens die 8 besten Shorts, aufgefüllt mit den nächstbesten bis ca. 8 Minuten (höchstens 10).
8 Shorts allein sind nur ca. 3 bis 4 Minuten lang; ab 8 Minuten darf YouTube später Werbung in der Mitte zeigen.

Bild: Querformat 1920x1080. Neu rendern im Querformat ginge nur über den langen Cartoon-Weg und würde den Server
viele Stunden blockieren (ein Short rendert ca. 1 Stunde). Darum läuft jeder Short im Hochformat in der Mitte,
dahinter dieselbe Szene groß, weich gezeichnet und abgedunkelt: der Hintergrund bewegt sich mit, keine schwarzen Balken.
Davor ein Intro mit der Stimme „klar“, vor jedem Short eine Karte „Platz N“ (gesprochen, Whoosh), am Ende ein
Frage-Satz. Platz 1 kommt zum Schluss. Kapitel in der Beschreibung, eigenes Thumbnail (thumbnail.py, 1280x720).

Die hochgeladenen Shorts werden dafür 8 Tage in data/woche/ aufbewahrt (nur die besten ca. 30, der Rest wird
gelöscht, sobald er einen Tag alt ist). Klappt etwas nicht, läuft um 19 Uhr das normale lange Video.
"""
import datetime as dt
import glob
import json
import os
import shutil
import subprocess
import tempfile
import threading
import wave

import numpy as np

import learn
import store

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_BLACK = os.path.join(HERE, "fonts", "InterDisplay-Black.otf")
FONT_SEMI = os.path.join(HERE, "fonts", "InterDisplay-SemiBold.otf")
DIR = "woche"
FILE = "zusammenschnitt.json"
KEEP_DAYS = 8
KEEP_TOP = 30          # so viele bewertete Shorts bleiben höchstens liegen
MIN_CLIPS = 8          # mindestens die 8 besten
TARGET_S = 8 * 60 + 10 # ab hier nicht mehr auffüllen (über 8 Minuten)
MAX_S = 10 * 60
WEEKDAY = 6            # Sonntag
BUILD_HOUR = 14        # ab 14 Uhr bauen, damit er um 17 Uhr fertig ist
POST_HOUR = 17
W, H, FPS = 1920, 1080, 30
BG = (11, 11, 12)
ACCENT = (10, 132, 255)
INTRO = "Das sind die {n} beliebtesten Shorts dieser Woche. Platz eins kommt ganz am Schluss."
OUTRO = "Welcher war dein Favorit? Schreib es in die Kommentare."
NUMBERS = ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf", "zwölf",
           "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn", "zwanzig",
           "einundzwanzig", "zweiundzwanzig", "dreiundzwanzig", "vierundzwanzig", "fünfundzwanzig", "sechsundzwanzig",
           "siebenundzwanzig", "achtundzwanzig", "neunundzwanzig", "dreißig"]
_run = threading.Lock()


# --- Shorts der Woche aufbewahren ----------------------------------------------------------

def clip_path(video_id):
    return store.path(DIR, video_id + ".mp4")


def keep(video, video_id, spec=None):
    """Nach dem Upload eines KI-Shorts: Kopie für den Zusammenschnitt ablegen. Fehler stoppen nie den Upload."""
    if not video_id or (spec or {}).get("format") == "firma" or (spec or {}).get("laenge") == "lang":
        return
    os.makedirs(store.path(DIR), exist_ok=True)
    shutil.copyfile(video, clip_path(video_id))
    prune()


def prune(now=None, posted=None):
    """Älter als 8 Tage: weg. Von den bewerteten (mind. 1 Tag alt) bleiben nur die besten KEEP_TOP."""
    now = now or store.now()
    files = {os.path.basename(f)[:-4]: f for f in glob.glob(store.path(DIR, "*.mp4"))}
    cutoff = (now - dt.timedelta(days=KEEP_DAYS)).timestamp()
    for vid, f in list(files.items()):
        if os.path.getmtime(f) < cutoff:
            _rm(f)
            files.pop(vid)
    if len(files) <= KEEP_TOP:
        return
    posted = posted if posted is not None else store.posted_items()
    rated = [(v["video_id"], lr) for v, _, lr, _ in learn.relative(posted, now)
             if v.get("video_id") in files and (now - dt.datetime.fromisoformat(v["posted_at"])).total_seconds() > 86400]
    rated.sort(key=lambda x: x[1], reverse=True)
    for vid, _ in rated[KEEP_TOP:]:
        _rm(files[vid])


def _rm(f):
    try:
        os.remove(f)
    except OSError:
        pass


# --- Auswahl ----------------------------------------------------------------------------------

def eligible(v, spec):
    """Nur eigene KI-Shorts des Hauptkanals."""
    return (spec is not None and v.get("kind") != "clip" and not v.get("lang") and v.get("channel") != "clips"
            and not v.get("abgabe") and spec.get("format") != "firma" and spec.get("laenge") != "lang")


def pick(posted, now, have=None, find=None):
    """Die besten Shorts der letzten 7 Tage, bester zuerst: (liste, grund). liste ist None, wenn es nicht reicht."""
    have = have or (lambda vid: os.path.exists(clip_path(vid)))
    if find is None:
        index = store.spec_index()
        find = lambda slug: store.find_spec(slug, index)   # noqa: E731
    since = now - dt.timedelta(days=7)
    cands = []
    for v, score, lr, _ in learn.relative(posted, now):
        at = dt.datetime.fromisoformat(v["posted_at"])
        if at < since or not v.get("video_id") or not have(v["video_id"]) or not eligible(v, find(v.get("slug"))):
            continue
        cands.append((lr, v.get("views") or 0, v))
    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out, total = [], 0.0
    for lr, views, v in cands:
        d = float(v.get("duration") or 25) + 2.5   # Short plus Karte davor
        if len(out) >= MIN_CLIPS and (total >= TARGET_S or total + d > MAX_S - 12):
            break
        out.append({"video_id": v["video_id"], "title": v.get("title") or "", "slug": v.get("slug"), "views": views,
                    "factor": round(2.718281828 ** lr, 2), "duration": v.get("duration")})
        total += d
    if len(out) < MIN_CLIPS:
        return None, f"nur {len(out)} passende Shorts aus dieser Woche (mindestens {MIN_CLIPS})"
    if total + 12 < 8 * 60:
        return None, f"zusammen nur {round((total + 12) / 60, 1)} Minuten (mindestens 8)".replace(".", ",")
    return out, None


def _mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def text_for(items, chapters, now):
    """Titel, Beschreibung mit Kapiteln und Tags. items: bester zuerst; chapters: [(sekunde, text)]."""
    kw = now.isocalendar()[1]
    first = (now - dt.timedelta(days=6)).strftime("%d.%m.")
    title = f"Die {len(items)} besten Shorts der Woche (KW {kw})"
    lines = [f"Die beliebtesten Shorts vom {first} bis {now:%d.%m.%Y} am Stück. Platz 1 kommt zum Schluss.", "",
             "Kapitel:"] + [f"{_mmss(t)} {txt}" for t, txt in chapters] + [
             "", "Alle Videos sind eigene Shorts dieses Kanals. Die Stimmen sind synthetisch (KI-Stimme)."]
    return {"title": title, "description": "\n".join(lines),
            "tags": ["Zusammenschnitt", "beste Shorts", "Wissen", "Erklärvideo", "Mystery", "Geschichten", "Shorts der Woche"]}


# --- Bauen (ffmpeg) -------------------------------------------------------------------------

def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def _font(path, size):
    from PIL import ImageFont
    return ImageFont.truetype(path, size)


def _wrap(draw, text, font, max_w, max_lines=2):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" ,.") + " …"
    return lines


def card_image(out, big, small, top="Die besten Shorts der Woche", frame=None):
    """Karte 2016x1134 (etwas größer, damit sie sich beim Abspielen langsam bewegen kann)."""
    from PIL import Image, ImageDraw, ImageFilter
    cw, ch = int(W * 1.05), int(H * 1.05)
    img = Image.new("RGB", (cw, ch), BG)
    glow = Image.new("RGB", (cw, ch), BG)
    ImageDraw.Draw(glow).ellipse((cw * 0.05, ch * 0.1, cw * 0.65, ch * 1.1), fill=(18, 52, 110))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(220)), 0.9)
    d = ImageDraw.Draw(img)
    x0 = int(cw * 0.1)
    text_w = int(cw * (0.5 if frame else 0.8))
    d.text((x0, int(ch * 0.24)), top.upper(), font=_font(FONT_SEMI, 34), fill=(150, 160, 175))
    d.text((x0, int(ch * 0.3)), big, font=_font(FONT_BLACK, 150), fill=(255, 255, 255))
    f = _font(FONT_SEMI, 58)
    y = int(ch * 0.52)
    for line in _wrap(d, small, f, text_w, 3):
        d.text((x0, y), line, font=f, fill=(225, 228, 235))
        y += 74
    d.rounded_rectangle((x0, int(ch * 0.47), x0 + 120, int(ch * 0.47) + 8), 4, fill=ACCENT)
    if frame and os.path.exists(frame):
        fr = Image.open(frame).convert("RGB")
        fh = int(ch * 0.74)
        fw = int(fh * 9 / 16)
        fr = fr.resize((fw, fh))
        mask = Image.new("L", (fw, fh), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, fw, fh), 36, fill=255)
        fx, fy = int(cw * 0.66), (ch - fh) // 2
        shadow = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(shadow).rounded_rectangle((fx + 10, fy + 24, fx + fw + 10, fy + fh + 24), 40, fill=160)
        img.paste((0, 0, 0), (0, 0), shadow.filter(ImageFilter.GaussianBlur(30)))
        img.paste(fr, (fx, fy), mask)
    img.save(out)
    return out


def write_wav(path, samples, rate, lead=0.0, tail=0.0, whoosh=False):
    """Mono-WAV (16 bit) mit Pause davor/danach, optional Whoosh am Anfang."""
    x = np.asarray(samples, dtype=np.float32)
    x = np.concatenate([np.zeros(int(lead * rate), np.float32), x, np.zeros(int(tail * rate), np.float32)])
    if whoosh:
        import audio
        w = np.asarray(audio.whoosh(rate), dtype=np.float32) * 0.5
        n = min(len(w), len(x))
        x[:n] += w[:n]
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak > 0.98:
        x = x / peak * 0.98
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((x * 32767).astype("<i2").tobytes())
    return len(x) / rate


ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


def _ff(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + args, check=True)


def card_video(out, png, wav, seconds):
    """Standbild, das sich langsam bewegt (kein Standbild-Gefühl), mit Ton."""
    dx, dy = int(W * 0.025), int(H * 0.025)
    _ff(["-loop", "1", "-framerate", str(FPS), "-i", png, "-i", wav, "-t", f"{seconds:.2f}",
         "-vf", f"crop={W}:{H}:x='{dx}+{dx}*sin(t*0.9)':y='{dy}+{dy}*cos(t*0.7)'", "-af", "apad"] + ENC + [out])


def clip_video(out, src):
    """Short im Hochformat in der Mitte, dahinter dieselbe Szene groß, weich und abgedunkelt."""
    fc = (f"[0:v]split=2[a][b];[a]scale={W}:-2,crop={W}:{H},boxblur=30:2,eq=brightness=-0.14:saturation=1.1[bg];"
          f"[b]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0,fps={FPS},format=yuv420p[v]")
    _ff(["-i", src, "-filter_complex", fc, "-map", "[v]", "-map", "0:a:0?", "-af", "aresample=48000"] + ENC + [out])


def frame_of(src, out, at=1.2):
    try:
        _ff(["-ss", str(at), "-i", src, "-frames:v", "1", out])
        return out
    except (subprocess.CalledProcessError, OSError):
        return None


def build(items, speak, out, workdir=None, now=None):
    """Baut das Video. items: bester zuerst. speak(text) -> (samples, rate) mit der Stimme „klar“.
    Gibt (pfad, kapitel, dauer) zurück. Abgespielt wird von hinten: Platz 1 zum Schluss."""
    now = now or store.now()
    work = workdir or tempfile.mkdtemp(prefix="zs-")
    parts, chapters, t = [], [], 0.0
    try:
        def seg(name, png, text, whoosh=False, lead=0.25, tail=0.6, min_s=2.2):
            x, rate = speak(text)
            wav = os.path.join(work, name + ".wav")
            secs = max(min_s, write_wav(wav, x, rate, lead=lead, tail=tail, whoosh=whoosh))
            mp4 = os.path.join(work, name + ".mp4")
            card_video(mp4, png, wav, secs)
            parts.append(mp4)
            return probe(mp4)

        n = len(items)
        intro_png = card_image(os.path.join(work, "intro.png"), f"Top {n}", f"Die beliebtesten Shorts vom "
                               f"{(now - dt.timedelta(days=6)):%d.%m.} bis {now:%d.%m.}", top="Shorts der Woche")
        chapters.append((0, "Intro"))
        t += seg("intro", intro_png, INTRO.format(n=_num(n)), lead=0.4, tail=0.8, min_s=5)
        for rank in range(n, 0, -1):
            it = items[rank - 1]
            src = clip_path(it["video_id"])
            frame = frame_of(src, os.path.join(work, f"f{rank}.jpg"))
            png = card_image(os.path.join(work, f"c{rank}.png"), f"Platz {rank}", it["title"], frame=frame)
            chapters.append((t, f"Platz {rank}: {it['title']}"))
            t += seg(f"c{rank}", png, f"Platz {_num(rank)}.", whoosh=True)
            mp4 = os.path.join(work, f"s{rank}.mp4")
            clip_video(mp4, src)
            parts.append(mp4)
            t += probe(mp4)
        outro_png = card_image(os.path.join(work, "outro.png"), "Dein Favorit?", "Schreib es in die Kommentare.",
                               top="Das waren die besten Shorts der Woche")
        t += seg("outro", outro_png, OUTRO, tail=1.2, min_s=4)
        lst = os.path.join(work, "list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            f.writelines(f"file '{p}'\n" for p in parts)
        _ff(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out])
        return out, chapters, probe(out)
    finally:
        if not workdir:
            shutil.rmtree(work, ignore_errors=True)


def _num(n):
    return NUMBERS[n] if 0 <= n < len(NUMBERS) else str(n)


# --- Ablauf am Sonntag ----------------------------------------------------------------------

def load():
    d = store.read(FILE, {}) or {}
    return {"on": True, "week": None, "status": None, "reason": None, "items": [], "file": None, "last": None, **d}


def save(**kw):
    with store.LOCK:
        d = load()
        d.update(kw)
        store.write(FILE, d)
        return d


def week_key(now):
    return now.strftime("%Y-%m-%d")


def due(now=None, cfg=None):
    """Ist heute (Sonntag ab 14 Uhr) noch etwas zu tun?"""
    now = now or store.now()
    d = load()
    if not d["on"] or now.weekday() != WEEKDAY or now.hour < BUILD_HOUR:
        return False
    if d["week"] == week_key(now) and d["status"] in ("hochgeladen", "übersprungen", "fehler"):
        return False
    if d["week"] == week_key(now) and d["status"] == "fertig" and now.hour < POST_HOUR:
        return False
    return True


def run(now=None, speak=None, upload=None, thumbs=None, posted=None):
    """Ein Schritt: auswählen und bauen (ab 14 Uhr), hochladen (ab 17 Uhr). Läuft nie doppelt.

    upload(path, spec) -> video_id; thumbs(spec, video_id) -> Thumbnail-Variante oder None (Fehler egal).
    """
    if not _run.acquire(blocking=False):
        return None
    try:
        now = now or store.now()
        if not due(now):
            return None
        key = week_key(now)
        d = load()
        if d["week"] != key:
            d = save(week=key, status=None, reason=None, items=[], file=None)
        if key in store.state().get("long_slots", []):
            return save(status="übersprungen", reason="Das lange Video lief heute schon.")
        if d["status"] != "fertig" or not d["file"] or not os.path.exists(d["file"]):
            posted = posted if posted is not None else store.posted_items()
            items, why = pick(posted, now)
            if not items:
                store.log("warn", f"Zusammenschnitt ausgelassen: {why}. Um 19 Uhr kommt das normale lange Video.",
                          agent="studio")
                return save(status="übersprungen", reason=why)
            out = store.path(DIR, f"zusammenschnitt-{key}.mp4")
            store.log("info", f"Baut den Zusammenschnitt der Woche aus {len(items)} Shorts.", agent="studio")
            try:
                path, chapters, secs = build(items, speak, out, now=now)
            except Exception as e:  # noqa: BLE001
                store.log("error", f"Zusammenschnitt nicht gebaut: {e}. Um 19 Uhr kommt das normale lange Video.",
                          agent="studio")
                return save(status="fehler", reason=str(e)[:200])
            d = save(status="fertig", items=items, file=path, chapters=chapters, seconds=round(secs, 1))
        if now.hour < POST_HOUR:
            return d
        # Thumbnail mit Figur und Ort des besten Shorts, Text und Titel vom Zusammenschnitt
        best = store.find_spec(d["items"][0].get("slug")) or {}
        spec = {**{k: best[k] for k in ("stil", "niche", "segments", "figur", "welt", "stimmung", "colors", "accent")
                   if k in best},
                "slug": f"zusammenschnitt-{key}", "laenge": "lang", **text_for(d["items"], d["chapters"], now),
                "thumb_text": [f"TOP {len(d['items'])} | der Woche", "Die besten Shorts"]}
        try:
            vid = upload(d["file"], spec)
        except Exception as e:  # noqa: BLE001
            store.log("error", f"Upload fehlgeschlagen: Zusammenschnitt ({e}). Um 19 Uhr kommt das normale lange Video.",
                      agent="publisher", kind="error")
            return save(status="fehler", reason=str(e)[:200])
        variant = None
        try:
            variant = thumbs(spec, vid) if thumbs else None
        except Exception:  # noqa: BLE001
            variant = None
        record(spec, vid, d, now, variant)
        _rm(d["file"])
        store.log("ok", f"Gepostet: {spec['title']}", agent="publisher", kind="posted", source="youtube")
        return save(status="hochgeladen", file=None, last={"video_id": vid, "title": spec["title"], "at": now.isoformat(
            timespec="seconds"), "n": len(d["items"])})
    finally:
        _run.release()


def record(spec, vid, d, now, variant):
    """Eintrag in uploads (lang, zusammenschnitt) und das lange Video für heute als erledigt markieren."""
    with store.LOCK:
        st = store.state()
        key = week_key(now)
        st["long_slots"] = (st.get("long_slots", []) + [key])[-90:]
        rec = {"slot": key, "slug": spec["slug"], "video_id": vid, "title": spec["title"],
               "posted_at": now.isoformat(timespec="seconds"), "duration": d.get("seconds"), "lang": True,
               "zusammenschnitt": True, "sources": [x["video_id"] for x in d["items"]],
               "look": {"stimme": "klar", "zusammenschnitt": True, **({"thumbnail": variant} if variant else {})}}
        st["uploads"].append(rec)
        store.write("state.json", st)


def overview(posted=None, now=None):
    """Für die Karte im Sendeplan."""
    now = now or store.now()
    d = load()
    days = (WEEKDAY - now.weekday()) % 7
    nxt = (now + dt.timedelta(days=days)).replace(hour=POST_HOUR, minute=0, second=0, microsecond=0)
    if nxt <= now or (d["week"] == week_key(now) and d["status"] in ("hochgeladen", "übersprungen", "fehler")):
        nxt += dt.timedelta(days=7)
    kept = len(glob.glob(store.path(DIR, "*.mp4")))
    preview = []
    if posted is not None:
        try:
            items, _ = pick(posted, now)
            preview = [x["title"] for x in (items or [])[:3]]
        except Exception:  # noqa: BLE001
            preview = []
    last = d.get("last")
    if last and posted is not None:
        v = next((p for p in posted if p.get("video_id") == last["video_id"]), None)
        last = {**last, "views": (v or {}).get("views")}
    return {"on": d["on"], "next": nxt.isoformat(timespec="minutes"), "status": d["status"], "week": d["week"],
            "reason": d["reason"], "kept": kept, "preview": preview, "last": last}
