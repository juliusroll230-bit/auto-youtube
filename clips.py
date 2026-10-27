"""Video-Clipper: macht aus langen Videos fertige Shorts (9:16, Untertitel Wort für Wort, Hook-Text).

Eine Kampagne ist ein Eingangsvideo und die Clips daraus:
  1. Eingang   Datei im Ordner DATA_DIR/inbox (auf ZimaOS: AppData/shorts-zentrale/inbox), Upload auf der
               Website oder Webhook (POST /webhook/video, siehe server.py)
  2. Rechte    Geschnitten wird erst nach der Bestätigung „Das Video ist von mir oder ich darf es verwenden“
               (Einstellung „Ordner-Videos sofort schneiden“ setzt sie für den Ordner automatisch)
  3. Abhören   faster-whisper schreibt auf dem Server mit, was gesagt wird, mit Zeit für jedes Wort
  4. Auswahl   Abschnitte zwischen min_len und max_len Sekunden, die an Satzgrenzen beginnen und enden.
               Punkte gibt es für einen starken ersten Satz (Frage, Zahl, „du“, starke Wörter), für die
               Stichwörter aus den Einstellungen, ein gutes Sprechtempo und laute Stellen.
  5. Schnitt   ffmpeg: 9:16 (Mitte oder ganzes Bild mit unscharfem Rahmen), Untertitel als ASS mit dem
               gerade gesprochenen Wort in Orange, Hook-Text in den ersten Sekunden, Lautheit -14 LUFS
  6. Freigabe  Clips warten in der Freigabe-Station. Freigegebene postet der Publisher verteilt auf die
               Sendeplätze (Einstellung „Clips pro Tag“).

Gespeichert wird in DATA_DIR/campaigns/<id>/: campaign.json, source.<endung>, transcript.json, clips/.
"""
import datetime as dt
import json
import os
import re
import secrets
import shutil
import subprocess
import time
import unicodedata

import numpy as np

import store

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi")
MAX_UPLOAD = 16 * 1024 ** 3  # 16 GB
ID_RE = re.compile(r"[a-z0-9-]{3,60}")
W, H = 1080, 1920

# Wörter, die einen ersten Satz stark machen (klein geschrieben, ohne Satzzeichen)
HOOK_WORDS = set("""warum wieso weshalb wie was wer geheim geheimnis niemand nie niemals immer fehler trick tricks wahrheit
verrückt krass unglaublich wichtig wichtigste eigentlich achtung problem lösung geld million millionen milliarden
schnell sofort heimlich verboten gefährlich besten beste schlimmste größte kleinste stell stellt einfach genial
why how what who secret nobody never always mistake truth crazy insane important problem money million fastest
best worst biggest stop imagine""".split())
YOU = {"du", "dich", "dir", "dein", "deine", "deinen", "deinem", "ihr", "euch", "euer", "eure", "you", "your"}
FILLER = {"also", "ähm", "äh", "ähh", "und", "ja", "so", "okay", "ok", "genau", "naja", "um", "uh", "so,", "and", "yeah"}
NUMBER_WORDS = set("""eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf zwanzig dreißig hundert tausend
million millionen one two three four five ten hundred thousand""".split())

TRANSCRIBE = None  # Tests setzen hier eine eigene Funktion ein (path, language, model, progress) -> words


# --- Speicher ---------------------------------------------------------------------

def inbox_dir():
    return store.path("inbox")


def camp_dir(cid, *parts):
    if not ID_RE.fullmatch(cid or ""):
        raise ValueError("Unbekannte Kampagne.")
    return store.path("campaigns", cid, *parts)


def load(cid):
    with open(camp_dir(cid, "campaign.json"), encoding="utf-8") as f:
        return json.load(f)


def save(c):
    path = camp_dir(c["id"], "campaign.json")
    with store.LOCK:
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False, indent=2)
        os.replace(path + ".tmp", path)


def update(cid, fn):
    """Liest, ändert und speichert eine Kampagne unter der Sperre."""
    with store.LOCK:
        c = load(cid)
        fn(c)
        save(c)
        return c


def all_campaigns():
    out = []
    root = store.path("campaigns")
    for cid in os.listdir(root) if os.path.isdir(root) else []:
        try:
            out.append(load(cid))
        except (OSError, ValueError):
            continue
    out.sort(key=lambda c: c.get("created_at") or "", reverse=True)
    return out


def source_path(c):
    return camp_dir(c["id"], c["file"])


def clip_path(c, clip, ext="mp4"):
    return camp_dir(c["id"], "clips", f"{clip['n']:02d}.{ext}")


def _slug(name):
    t = unicodedata.normalize("NFKD", name.lower().replace("ß", "ss").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue"))
    t = re.sub(r"[^a-z0-9]+", "-", t.encode("ascii", "ignore").decode()).strip("-")
    return (t[:40].strip("-") or "video")


def _new_id(name):
    while True:
        cid = f"{_slug(name)}-{secrets.token_hex(2)}"
        if not os.path.exists(store.path("campaigns", cid)):
            return cid


def _nice_name(filename):
    base = os.path.splitext(os.path.basename(filename))[0]
    return re.sub(r"[_\s]+", " ", base).strip()[:80] or "Video"


def _clean_text(value, limit):
    return " ".join(str(value or "").split())[:limit]


def create(name, origin, rights=False, credit="", ext=".mp4"):
    """Legt eine leere Kampagne an. Danach die Quelldatei nach camp_dir(id, file) schreiben und attach() aufrufen."""
    name = _clean_text(name, 80) or "Video"
    cid = _new_id(name)
    os.makedirs(store.path("campaigns", cid, "clips"), exist_ok=True)
    c = {"id": cid, "name": name, "origin": origin, "credit": _clean_text(credit, 80), "rights": bool(rights),
         "created_at": store.now().isoformat(timespec="seconds"), "file": "source" + ext.lower(),
         "status": "laedt", "progress": 0, "error": None, "duration": None, "clips": []}
    save(c)
    return c


def attach(cid):
    """Die Quelldatei ist vollständig da: Kampagne wartet jetzt auf Bestätigung oder aufs Schneiden."""
    c = update(cid, lambda c: c.update(status="wartet" if c["rights"] else "neu", progress=0))
    store.log("info", f"Neues Video im Eingang: {c['name']}" + ("" if c["rights"] else " (bitte Rechte bestätigen)"),
              agent="clipper", kind="input", source=c["origin"])
    return c


def add_file(path, origin, rights=False, credit="", name=None, move=True):
    ext = os.path.splitext(path)[1].lower()
    c = create(name or _nice_name(path), origin, rights, credit, ext if ext in VIDEO_EXT else ".mp4")
    (shutil.move if move else shutil.copyfile)(path, source_path(c))
    return attach(c["id"])


def add_stream(rfile, length, filename, origin, rights=False, credit="", name=None):
    """Speichert einen Upload direkt in eine neue Kampagne, Stück für Stück (auch mehrere GB)."""
    if not 0 < length <= MAX_UPLOAD:
        raise ValueError("Die Datei ist leer oder größer als 16 GB.")
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in VIDEO_EXT:
        raise ValueError("Bitte ein Video hochladen (mp4, mov, mkv, webm).")
    c = create(name or _nice_name(filename), origin, rights, credit, ext)
    target, left = source_path(c), length
    try:
        with open(target + ".part", "wb") as f:
            while left > 0:
                chunk = rfile.read(min(left, 1024 * 1024))
                if not chunk:
                    raise ValueError("Der Upload wurde abgebrochen.")
                f.write(chunk)
                left -= len(chunk)
        os.replace(target + ".part", target)
    except Exception:
        shutil.rmtree(store.path("campaigns", c["id"]), ignore_errors=True)
        raise
    return attach(c["id"])


def check_url(url):
    if not re.match(r"https?://", url or ""):
        raise ValueError("Bitte eine http(s)-Adresse einer Videodatei angeben.")
    if re.search(r"(youtube\.com|youtu\.be|tiktok\.com|instagram\.com)", url):
        raise ValueError("Links zu YouTube, TikTok oder Instagram werden nicht geladen. Bitte die Videodatei selbst schicken.")


def add_url(url, rights=False, credit="", name=None):
    """Lädt eine Videodatei von einer direkten Adresse (z. B. aus dem Heimnetz). Keine YouTube-Links."""
    import urllib.request

    check_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "shorts-zentrale"})
    with urllib.request.urlopen(req, timeout=60) as r:
        ctype = r.headers.get("Content-Type", "")
        if not (ctype.startswith("video/") or "octet-stream" in ctype):
            raise ValueError("Unter der Adresse liegt kein Video.")
        filename = os.path.basename(url.split("?")[0]) or "video.mp4"
        if os.path.splitext(filename)[1].lower() not in VIDEO_EXT:
            filename += ".mp4"
        length = int(r.headers.get("Content-Length") or 0)
        if length:
            return add_stream(r, length, filename, "webhook", rights, credit, name)
        c = create(name or _nice_name(filename), "webhook", rights, credit, os.path.splitext(filename)[1])
        size = 0
        with open(source_path(c), "wb") as f:
            while chunk := r.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    shutil.rmtree(store.path("campaigns", c["id"]), ignore_errors=True)
                    raise ValueError("Die Datei ist größer als 16 GB.")
                f.write(chunk)
        return attach(c["id"])


_sizes = {}


def scan_inbox(auto_start=False):
    """Übernimmt fertig kopierte Videos aus dem Eingangsordner (Größe zwei Durchläufe lang gleich)."""
    folder = inbox_dir()
    os.makedirs(folder, exist_ok=True)
    added = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if name.startswith(".") or not name.lower().endswith(VIDEO_EXT) or not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        if _sizes.get(name) != size or time.time() - os.path.getmtime(path) < 15:
            _sizes[name] = size
            continue
        _sizes.pop(name, None)
        try:
            added.append(add_file(path, "ordner", rights=auto_start))
        except OSError as e:
            store.log("error", f"Video aus dem Eingang konnte nicht übernommen werden ({name}): {e}", agent="clipper")
    return added


def inbox_count():
    folder = inbox_dir()
    try:
        return sum(1 for n in os.listdir(folder) if n.lower().endswith(VIDEO_EXT) and not n.startswith("."))
    except OSError:
        return 0


# --- Aktionen aus der Website -----------------------------------------------------------

def confirm(cid, credit=None):
    def go(c):
        c["rights"] = True
        if credit is not None:
            c["credit"] = _clean_text(credit, 80)
        if c["status"] == "neu":
            c["status"] = "wartet"
    return update(cid, go)


def retry(cid):
    def go(c):
        if c["status"] != "fehler":
            raise ValueError("Die Kampagne läuft schon oder ist fertig.")
        c.update(status="wartet" if c["rights"] else "neu", error=None, progress=0)
    return update(cid, go)


def delete(cid):
    path = camp_dir(cid)
    if not os.path.isdir(path):
        raise ValueError("Unbekannte Kampagne.")
    if _running.get("id") == cid:
        raise ValueError("Die Kampagne wird gerade geschnitten. Bitte warten, bis sie fertig ist.")
    shutil.rmtree(path)


def set_clip(cid, n, action, title=None):
    def go(c):
        clip = next((x for x in c["clips"] if x["n"] == n), None)
        if not clip:
            raise ValueError("Unbekannter Clip.")
        if clip["status"] == "gepostet":
            raise ValueError("Der Clip ist schon online.")
        if action == "approve":
            clip["status"] = "freigegeben"
        elif action == "reject":
            clip["status"] = "abgelehnt"
        elif action == "restore":
            clip["status"] = "neu"
        elif action == "title":
            t = _clean_text(title, 90)
            if len(t) < 3:
                raise ValueError("Der Titel ist zu kurz.")
            clip["title"] = t
        else:
            raise ValueError("Unbekannte Aktion.")
    return update(cid, go)


# --- Posten ------------------------------------------------------------------------------

def ready_clips():
    """Freigegebene, noch nicht gepostete Clips. Verteilt über die Kampagnen (nicht alle aus einer am Stück)."""
    out = []
    for c in all_campaigns():
        posted = sum(1 for x in c["clips"] if x["status"] == "gepostet")
        for clip in c["clips"]:
            if clip["status"] == "freigegeben" and os.path.exists(clip_path(c, clip)):
                out.append((posted, c.get("created_at") or "", clip["n"], c, clip))
    out.sort(key=lambda x: x[:3])
    return [(c, clip) for *_, c, clip in out]


def posted_today(uploads, day=None):
    day = day or store.now().date().isoformat()
    return sum(1 for u in uploads if u.get("kind") == "clip" and (u.get("posted_at") or "")[:10] == day)


def choose_for_slot(slot, hours, per_day, uploads, scripts_left=True):
    """Ob zu diesem Sendeplatz ein Clip statt eines KI-Shorts kommt (gleichmäßig über den Tag verteilt)."""
    if per_day <= 0 or posted_today(uploads) >= per_day:
        return None
    ready = ready_clips()
    if not ready:
        return None
    if not scripts_left:
        return ready[0]
    if not slot:
        return None
    hrs = sorted(int(h) for h in hours)
    hour = int(slot.rsplit("-", 1)[-1])
    idx = hrs.index(hour) if hour in hrs else 0
    per_day = min(per_day, len(hrs))
    positions = {min(len(hrs) - 1, int((i + 0.5) * len(hrs) / per_day)) for i in range(per_day)}
    return ready[0] if idx in positions else None


def upload_spec(c, clip):
    lang = (c.get("language") or "de")[:2]
    desc = clip.get("text", "")
    if len(desc) > 280:
        desc = desc[:277].rsplit(" ", 1)[0] + " …"
    if c.get("credit"):
        desc += f"\n\nOriginal: {c['credit']}"
    tags = ["shorts", "clip"] + [k for k in re.split(r"[,;]\s*|\s+", c.get("keywords") or "") if k][:8]
    return {"title": clip["title"], "description": desc + "\n\n#shorts", "tags": tags, "language": lang}


def mark_posted(cid, n, video_id):
    def go(c):
        for x in c["clips"]:
            if x["n"] == n:
                x.update(status="gepostet", video_id=video_id, posted_at=store.now().isoformat(timespec="seconds"))
    return update(cid, go)


def upload_record(c, clip, slot, video_id):
    """Eintrag für state.json → uploads (wie bei KI-Shorts, mit kind="clip")."""
    return {"slot": slot, "slug": f"clip-{c['id']}-{clip['n']}", "video_id": video_id, "title": clip["title"],
            "posted_at": store.now().isoformat(timespec="seconds"), "marks": clip.get("marks"),
            "duration": clip.get("duration"), "kind": "clip", "campaign": c["id"], "n": clip["n"],
            "niche": "Clip", "sentences": clip.get("sentences")}


# --- Übersicht für die Website -------------------------------------------------------------

def summary():
    camps = all_campaigns()
    today = store.now().date().isoformat()
    clips = [x for c in camps for x in c["clips"]]
    active = [c for c in camps if c["status"] in ("laedt", "neu", "wartet", "hoert", "schneidet")
              or any(x["status"] in ("neu", "freigegeben") for x in c["clips"])]
    out = []
    for c in camps[:30]:
        out.append({k: c.get(k) for k in ("id", "name", "origin", "credit", "rights", "created_at", "status",
                                          "progress", "error", "duration", "language", "finished_at")}
                   | {"clips": [{k: x.get(k) for k in ("n", "start", "end", "duration", "title", "hook", "score",
                                                         "status", "video_id", "posted_at", "text")}
                                for x in c["clips"]]})
    return {
        "campaigns": out,
        "totals": {"campaigns": len(camps), "active": len(active), "clips": len(clips),
                   "clips_today": sum(1 for c in camps if (c.get("finished_at") or "")[:10] == today
                                      for _ in c["clips"]),
                   "waiting": sum(1 for x in clips if x["status"] == "neu"),
                   "approved": sum(1 for x in clips if x["status"] == "freigegeben"),
                   "posted": sum(1 for x in clips if x["status"] == "gepostet"),
                   "unconfirmed": sum(1 for c in camps if c["status"] == "neu"),
                   "inbox": inbox_count()},
        "running": _running.get("id"),
    }


# --- Verarbeitung -----------------------------------------------------------------------------

_running = {}


def next_job():
    waiting = [c for c in all_campaigns() if c["status"] == "wartet" and c.get("rights")]
    return min(waiting, key=lambda c: c.get("created_at") or "") if waiting else None


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                         capture_output=True, text=True, timeout=120)
    if out.returncode:
        raise RuntimeError("Die Datei ist kein lesbares Video.")
    info = json.loads(out.stdout)
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v:
        raise RuntimeError("Die Datei enthält kein Bild.")
    dur = float(info.get("format", {}).get("duration") or v.get("duration") or 0)
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    rot = 0
    for sd in v.get("side_data_list") or []:
        rot = int(sd.get("rotation") or 0) or rot
    if abs(rot) in (90, 270):
        w, h = h, w
    return {"duration": dur, "width": w, "height": h,
            "audio": any(s.get("codec_type") == "audio" for s in info.get("streams", []))}


def loudness(path):
    """Lautstärke (RMS) je halbe Sekunde, 8 kHz Mono reicht dafür."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    vals = []
    while True:
        b = p.stdout.read(8000)
        if not b:
            break
        a = np.frombuffer(b[: len(b) // 2 * 2], dtype=np.int16).astype(np.float32)
        vals.append(float(np.sqrt(np.mean(a * a))) if len(a) else 0.0)
    p.wait()
    return vals


_models = {}


def _whisper(model_name):
    from faster_whisper import WhisperModel

    if model_name not in _models:
        _models.clear()  # immer nur ein Modell im Speicher
        baked = os.path.join(HERE, "models", "whisper", model_name)  # „base“ liegt im Docker-Image bereit
        threads = max(1, (os.cpu_count() or 2) // 2)  # die andere Hälfte bleibt für Uploads und Website
        _models[model_name] = WhisperModel(baked if os.path.isfile(os.path.join(baked, "model.bin")) else model_name, device="cpu",
                                           compute_type="int8", cpu_threads=threads,
                                           download_root=store.path("models"))
    return _models[model_name]


def whisper_words(path, language, model_name, progress):
    model = _whisper(model_name)
    segments, info = model.transcribe(path, language=None if language == "auto" else language, beam_size=1,
                                      word_timestamps=True, vad_filter=True)
    words, total = [], info.duration or 1
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append({"w": text, "s": round(w.start, 2), "e": round(w.end, 2)})
        progress(min(1.0, seg.end / total))
    return {"language": info.language, "words": words}


def sentences(words):
    """Wörter zu Sätzen: Ende bei . ! ? oder einer Pause über 1,2 s."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if re.search(r"[.!?…]$", w["w"]) or not nxt or nxt["s"] - w["e"] > 1.2 or len(cur) >= 40:
            out.append({"s": cur[0]["s"], "e": cur[-1]["e"], "words": cur, "text": " ".join(x["w"] for x in cur)})
            cur = []
    return out


def _plain(word):
    return re.sub(r"[^\wäöüß]", "", word.lower())


def hook_points(sentence):
    ws = [_plain(w["w"]) for w in sentence["words"]]
    pts = 0.0
    if sentence["text"].rstrip().endswith("?"):
        pts += 2
    if any(re.search(r"\d", w["w"]) for w in sentence["words"]) or any(w in NUMBER_WORDS for w in ws):
        pts += 1
    if any(w in YOU for w in ws):
        pts += 1
    pts += min(2, sum(1 for w in ws if w in HOOK_WORDS))
    if len(ws) <= 12:
        pts += 1
    if ws and ws[0] in FILLER:
        pts -= 1.5
    return pts


def candidates(sents, rms, keywords, min_len, max_len):
    target = (min_len + max_len) / 2
    mean = (sum(rms) / len(rms)) if rms else 0
    p90 = sorted(rms)[int(len(rms) * 0.9)] if rms else 0
    kws = [k.lower() for k in re.split(r"[,;]\s*|\s+", keywords or "") if len(k) > 2]
    out = []
    for i, first in enumerate(sents):
        for j in range(i, len(sents)):
            dur = sents[j]["e"] - first["s"]
            if dur > max_len:
                break
            if dur < min_len:
                continue
            part = sents[i:j + 1]
            text = " ".join(s["text"] for s in part).lower()
            n_words = sum(len(s["words"]) for s in part)
            score = hook_points(first)
            score += min(6, 1.5 * sum(text.count(k) for k in kws))
            wps = n_words / dur
            score += 1 if 2.2 <= wps <= 4.2 else -1 if wps < 1.2 else 0
            if rms and mean > 0:
                seg = rms[int(first["s"] * 2):int(sents[j]["e"] * 2) + 1] or [0]
                ratio = (sum(seg) / len(seg)) / mean
                score += max(-1, min(1.5, (ratio - 1) * 3))
                score += 0.5 if max(seg) >= p90 else 0
            if len(part[-1]["words"]) <= 10:
                score += 0.5  # kurzer letzter Satz: wirkt wie eine Pointe
            score -= 1.5 * abs(dur - target) / target
            out.append({"start": first["s"], "end": sents[j]["e"], "score": score, "i": i, "j": j})
    return out


def energy_windows(rms, duration, length, count):
    """Ohne Sprache: die lautesten Abschnitte."""
    step = max(1, int(length * 2))
    wins = []
    for k in range(0, max(1, len(rms) - step), max(1, step // 2)):
        wins.append({"start": k / 2, "end": min(duration, k / 2 + length), "score": sum(rms[k:k + step]) / step})
    return wins or [{"start": 0, "end": min(duration, length), "score": 0}]


def pick(cands, count, gap=1.0):
    chosen = []
    for c in sorted(cands, key=lambda c: -c["score"]):
        if all(c["end"] + gap <= x["start"] or c["start"] >= x["end"] + gap for x in chosen):
            chosen.append(c)
            if len(chosen) == count:
                break
    return sorted(chosen, key=lambda c: c["start"])


def _trim_filler(sentence_text):
    words = sentence_text.split()
    while words and _plain(words[0]) in FILLER and len(words) > 3:
        words = words[1:]
    if words:
        words[0] = words[0][:1].upper() + words[0][1:]
    return words


def hook_text(sentence_text, max_words=9):
    """Erster Satz als Text oben im Bild; zu lange Sätze enden mit „…“ (nicht nach „im“, „der“ usw.)."""
    words = _trim_filler(sentence_text)
    if len(words) > max_words:
        words = words[:max_words - 1]
        while len(words) > 3 and len(_plain(words[-1])) <= 3:
            words.pop()
        words[-1] = words[-1].rstrip(",;:") + " …"
    return " ".join(words).rstrip(",;:")


def title_text(sentence_text, limit=90):
    text = " ".join(_trim_filler(sentence_text))
    if len(text) > limit:
        text = text[:limit - 2].rsplit(" ", 1)[0].rstrip(",;:") + " …"
    return text


def score_label(raw):
    """Rohpunkte zu 1–99 für die Anzeige („Einschätzung“), keine echte Vorhersage."""
    return int(max(1, min(99, round(100 / (1 + np.exp(-(raw - 2.5) / 1.6))))))


# --- Untertitel (ASS) -----------------------------------------------------------------------

ACCENT = "&H000066FF&"  # #ff6600 in ASS-Reihenfolge (BBGGRR)


def _ass_time(t):
    t = max(0.0, t)
    h, rest = divmod(t, 3600)
    m, s = divmod(rest, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _ass_escape(text):
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def caption_groups(words, max_words=3, max_chars=20):
    groups, cur = [], []
    for i, w in enumerate(words):
        if cur and (len(cur) >= max_words or len(" ".join(x["w"] for x in cur + [w])) > max_chars
                    or w["s"] - cur[-1]["e"] > 0.6):
            groups.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?]$", w["w"]):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def ass(words, t0, dur, style="pop", hook=""):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display Black,88,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,0,0,0,0,100,100,0,0,1,7,4,2,90,90,560,1
Style: Box,Inter Display Black,82,&H00FFFFFF,&H00FFFFFF,&H28120A0E,&H28120A0E,0,0,0,0,100,100,0,0,3,20,0,2,90,90,560,1
Style: Hook,Inter Display Black,72,&H00FFFFFF,&H00FFFFFF,&H000066FF,&H000066FF,0,0,0,0,100,100,0,0,3,24,0,8,90,90,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    if hook:
        wrapped, line = [], ""
        for w in hook.split():
            if line and len(line) + 1 + len(w) > 18:
                wrapped.append(line)
                line = w
            else:
                line = f"{line} {w}".strip()
        wrapped.append(line)
        text = r"\N".join(_ass_escape(x) for x in wrapped)
        lines.append(f"Dialogue: 1,{_ass_time(0)},{_ass_time(min(3.2, dur))},Hook,,0,0,0,,"
                     r"{\fad(120,260)\fscx86\fscy86\t(0,160,\fscx100\fscy100)}" + text)
    cap = "Box" if style == "kasten" else "Cap"
    on = {"pop": r"{\c" + ACCENT + r"\fscx114\fscy114}", "unterstrich": r"{\c" + ACCENT + r"\u1}",
          "kasten": r"{\c" + ACCENT + "}"}.get(style, r"{\c" + ACCENT + "}")
    groups = caption_groups([w for w in words if t0 - 0.05 <= w["s"] < t0 + dur])
    for g_i, g in enumerate(groups):
        nxt_start = groups[g_i + 1][0]["s"] if g_i + 1 < len(groups) else t0 + dur
        for k, w in enumerate(g):
            start = w["s"] - t0
            end = (g[k + 1]["s"] if k + 1 < len(g) else min(nxt_start, g[-1]["e"] + 0.35)) - t0
            if end - start < 0.05:
                end = start + 0.05
            parts = [(on + _ass_escape(x["w"]) + r"{\r}") if x is w else _ass_escape(x["w"]) for x in g]
            lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(min(end, dur))},{cap},,0,0,0,,{' '.join(parts)}")
    return head + "\n".join(lines) + "\n"


# --- Schnitt ------------------------------------------------------------------------------

def _ffmpeg(args, cwd=None, timeout=3600):
    cmd = (["nice", "-n", "10"] if shutil.which("nice") else []) + ["ffmpeg", "-y", "-v", "error"] + args
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if out.returncode:
        raise RuntimeError("ffmpeg: " + (out.stderr.strip().splitlines() or ["unbekannter Fehler"])[-1][:200])


def render(c, clip, info, words, settings):
    folder = camp_dir(c["id"], "clips")
    start = max(0.0, clip["start"] - 0.15)
    end = min(info["duration"], clip["end"] + 0.4)
    dur = end - start
    name = f"{clip['n']:02d}"
    with open(os.path.join(folder, name + ".ass"), "w", encoding="utf-8") as f:
        f.write(ass(words, start, dur, settings["untertitel"], clip.get("hook") if settings["hook"] else ""))
    crop = settings["crop"]
    if crop == "auto":
        crop = "mitte" if info["width"] <= info["height"] * 1.05 else "rahmen"
    if crop == "mitte":
        base = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
    else:
        base = (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"gblur=sigma=28,eq=brightness=-0.12:saturation=1.15[bg];"
                f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1")
    graph = f"{base},fps=30,subtitles={name}.ass:fontsdir='{FONTS}'[v]"
    args = ["-ss", f"{start:.2f}", "-i", source_path(c), "-t", f"{dur:.2f}"]
    if info["audio"]:
        graph += ";[0:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
    args += ["-filter_complex", graph, "-map", "[v]"]
    args += ["-map", "[a]", "-c:a", "aac", "-b:a", "160k"] if info["audio"] else []
    args += ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-map_metadata", "-1", "-movflags", "+faststart", name + ".mp4"]
    _ffmpeg(args, cwd=folder)
    _ffmpeg(["-ss", "0.8", "-i", name + ".mp4", "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "3", name + ".jpg"],
            cwd=folder, timeout=120)
    return round(dur, 2)


def process(cid, settings, task=lambda text: None):
    """Schneidet eine Kampagne. task(text) meldet den Fortschritt für die Sprechblase."""
    _running["id"] = cid
    try:
        c = update(cid, lambda c: c.update(status="hoert", progress=1, error=None))
        info = probe(source_path(c))
        if info["duration"] < 8:
            raise RuntimeError("Das Video ist zu kurz (unter 8 Sekunden).")
        update(cid, lambda c: c.update(duration=round(info["duration"], 1)))
        tpath = camp_dir(cid, "transcript.json")
        if os.path.exists(tpath):
            with open(tpath, encoding="utf-8") as f:
                tr = json.load(f)
        elif info["audio"]:
            last = [0.0]

            def progress(x):
                pct = int(5 + 60 * x)
                task(f"Hört „{c['name'][:24]}“ ab ({int(x * 100)} %)")
                if time.time() - last[0] > 3:
                    last[0] = time.time()
                    update(cid, lambda c: c.update(progress=pct))
            task(f"Hört „{c['name'][:24]}“ ab")
            tr = (TRANSCRIBE or whisper_words)(source_path(c), settings["sprache"], settings["modell"], progress)
            with open(tpath, "w", encoding="utf-8") as f:
                json.dump(tr, f, ensure_ascii=False)
        else:
            tr = {"language": None, "words": []}
        task("Sucht die stärksten Stellen")
        c = update(cid, lambda c: c.update(status="schneidet", progress=66, language=tr.get("language"),
                                           keywords=settings["keywords"]))
        rms = loudness(source_path(c)) if info["audio"] else []
        lo, hi = sorted((settings["min_len"], settings["max_len"]))
        hi = min(hi, max(lo, info["duration"]))
        sents = sentences(tr["words"])
        chosen = pick(candidates(sents, rms, settings["keywords"], lo, hi), settings["clips"])
        if not chosen:
            chosen = pick(energy_windows(rms, info["duration"], min(hi, info["duration"]), settings["clips"]),
                          settings["clips"])
        clips = []
        for n, ch in enumerate(chosen, 1):
            task(f"Schneidet Clip {n}/{len(chosen)}")
            part = [s for s in sents if ch["start"] - 0.01 <= s["s"] and s["e"] <= ch["end"] + 0.01]
            hook = hook_text(part[0]["text"]) if part else ""
            text = " ".join(s["text"] for s in part)
            clip = {"n": n, "start": round(ch["start"], 2), "end": round(ch["end"], 2), "hook": hook,
                    "title": (title_text(part[0]["text"]) if part else "") or f"{c['name']} (Teil {n})",
                    "text": text, "score": score_label(ch["score"]) if part else None,
                    "status": "neu" if settings["freigabe"] else "freigegeben",
                    "sentences": [s["text"] for s in part]}
            clip["duration"] = render(c, clip, info, tr["words"], settings)
            t0 = max(0.0, clip["start"] - 0.15)
            clip["marks"] = [round(max(0.0, s["s"] - t0) / clip["duration"], 4) for s in part] or None
            clips.append(clip)
            update(cid, lambda c, k=n: c.update(progress=66 + int(34 * k / len(chosen))))
        c = update(cid, lambda c: c.update(status="fertig", progress=100, clips=clips,
                                           finished_at=store.now().isoformat(timespec="seconds")))
        return c
    except Exception as e:
        update(cid, lambda c: c.update(status="fehler", error=str(e)[:300]))
        raise
    finally:
        _running.pop("id", None)


def thumb_file(slug):
    """Vorschaubild eines geposteten Clips (slug clip-<kampagne>-<nummer>)."""
    cid, _, n = slug[5:].rpartition("-")
    try:
        return camp_dir(cid, "clips", f"{int(n):02d}.jpg")
    except ValueError:
        return None


def stale_cleanup():
    """Nach einem Neustart: Kampagnen, die mitten im Schneiden waren, starten neu; halbe Uploads fliegen raus."""
    for c in all_campaigns():
        if c["status"] in ("hoert", "schneidet"):
            update(c["id"], lambda c: c.update(status="wartet", progress=0))
        elif c["status"] == "laedt":
            age = store.now() - dt.datetime.fromisoformat(c["created_at"])
            if age.total_seconds() > 3600:
                shutil.rmtree(store.path("campaigns", c["id"]), ignore_errors=True)
