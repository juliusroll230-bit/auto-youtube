"""Sleep History für Quiet Corner (Phase I, Teil 1, seit 26.11.2026, Julius' Wunsch).

Neuer Typ neben den Einschlaf-Geschichten: „The Entire Story of <Thema> to Fall Asleep To“, 1 bis 3 Stunden, ruhig auf
Englisch erzählt (dieselbe Stimme wie sleepstory.py), langsames Tempo, keine Spannungsspitzen, keine brutalen Details.
Nur Stoffe ohne Urheberrecht (Mythologie, echte Geschichte, Märchen und Sagen, echte Rätsel), Sagen als Sagen erzählt.

Bild: die passende ruhige Szene aus entspannung.py, darüber langsam wechselnde, selbst gezeichnete Kapitel-Karten
(Glas-Karte unten links mit Kapitelname und einer einfachen Illustration). Jedes Kapitel beginnt auf einer vollen Minute,
damit das Bild aus fertigen 60-s-Stücken nur zusammenkopiert wird (kein stundenlanges Neu-Rendern). Kapitel mit Zeitmarken
in der Beschreibung.

Skripte: `sleep-history/NNNN-name.json` (Felder siehe CLAUDE.md), 2 pro Woche von der täglichen Skript-Aufgabe.
Häufigkeit: Standard alle 3 Tage (ca. 2 pro Woche). Lernmodus: Liegt Sleep History nach mindestens 4 bewerteten Videos je
Seite (gegen Einschlaf-Geschichte und reine Szene, Aufrufe pro Tag) zu 80 % sicher vorn, alle 2 Tage; liegt eine andere
Seite zu 80 % sicher vorn, nur noch einmal pro Woche.
"""
import datetime as dt
import glob
import json
import math
import os
import subprocess
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.environ.get("SLEEP_HISTORY_DIR", os.path.join(HERE, "sleep-history"))
PREFIX = "The Entire Story of"
VOICE_IN = 6.0           # Sekunden nach Kapitelanfang, bis die Stimme beginnt (erst blendet die Karte ein)
CHAPTER_GAP = 6.0        # mindestens so viel Ruhe am Kapitelende
TAIL_S = 600             # danach läuft die Szene mindestens so lange weiter
MIN_MIN, MAX_MIN = 60, 180
GAP_DAYS = 3             # Standard: alle 3 Tage ein Sleep-History-Video (ca. 2 pro Woche)
FAST_GAP, SLOW_GAP = 2, 7
MIN_EACH = 4
SURE = 0.8
NUM = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
       "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
DISCLOSURE = ("Narrated with a synthetic voice. Every picture and sound was made by Quiet Corner. "
              "Facts were checked with two sources; legends and myths are told as legends, not as history.")
FONT_SERIF = os.path.join(HERE, "fonts", "DMSerifDisplay-Regular.ttf")
FONT_SEMI = os.path.join(HERE, "fonts", "InterDisplay-SemiBold.otf")
FONT_EMOJI = os.path.join(HERE, "fonts", "NotoColorEmoji.ttf")


# --- Skripte ----------------------------------------------------------------------------------

def scripts():
    out = []
    for p in sorted(glob.glob(os.path.join(DIR, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and d.get("id") and d.get("title") and d.get("chapters"):
            out.append(d)
    return out


def pick(used_ids):
    used = set(used_ids or [])
    return next((h for h in scripts() if h["id"] not in used), None)


def words(h):
    return sum(len(c.get("text", "").split()) for c in h.get("chapters", []))


def validate(h, scenes=None):
    """Fehlerliste für ein Skript (leer = gut)."""
    errs = []
    if not str(h.get("title", "")).startswith(PREFIX):
        errs.append(f"Titel muss mit „{PREFIX}“ anfangen")
    if scenes is not None and h.get("scene") not in scenes:
        errs.append("scene unbekannt")
    if len(h.get("sources") or []) < 2:
        errs.append("mindestens zwei Quellen (sources)")
    if not h.get("thumb") or len(str(h["thumb"]).split()) > 3:
        errs.append("thumb: höchstens 3 Wörter")
    chs = h.get("chapters") or []
    if len(chs) < 3:
        errs.append("mindestens 3 Kapitel (YouTube-Kapitel brauchen 3)")
    for i, c in enumerate(chs):
        n = len(str(c.get("text", "")).split())
        if not c.get("title") or not c.get("icon"):
            errs.append(f"Kapitel {i + 1}: title und icon fehlen")
        if not 400 <= n <= 900:
            errs.append(f"Kapitel {i + 1}: {n} Wörter (400 bis 900)")
    return errs


# --- Häufigkeit und Lernmodus -----------------------------------------------------------------

def inhalt(u):
    return "History" if u.get("history") else "Geschichte" if u.get("story") else "Szene"


def gap_days(uploads, today=None):
    """Abstand zwischen zwei Sleep-History-Videos in Tagen (Lernmodus, siehe oben)."""
    import entspannung
    today = today or dt.date.today()
    ups = [{**u, "inhalt": inhalt(u)} for u in uploads if u.get("idea")]
    opts = ("History", "Geschichte", "Szene")
    counts = {o: entspannung.belief(ups, "inhalt", o, today)[0] for o in opts}
    if counts["History"] < MIN_EACH or max(counts["Geschichte"], counts["Szene"]) < MIN_EACH:
        return GAP_DAYS
    rivals = [o for o in opts if counts[o] >= MIN_EACH]
    ch = entspannung.chances(rivals, ups, "inhalt", today)
    if ch.get("History", 0) >= SURE:
        return FAST_GAP
    if any(ch.get(o, 0) >= SURE for o in rivals if o != "History"):
        return SLOW_GAP
    return GAP_DAYS


def due(uploads, today=None):
    """Ist heute ein Sleep-History-Video dran? (Ein neues Skript muss es außerdem geben, siehe pick.)"""
    today = today or dt.date.today()
    last = max((u.get("at") for u in uploads if u.get("history")), default=None)
    if not last:
        return True
    try:
        return (today - dt.date.fromisoformat(last)).days >= gap_days(uploads, today)
    except ValueError:
        return True


# --- Ton: Kapitel einzeln sprechen, jedes Kapitel beginnt auf einer vollen Minute --------------

def _spoken_title(i, c):
    n = NUM[i + 1] if i + 1 < len(NUM) else str(i + 1)
    return f"Chapter {n}. {c['title'].rstrip('.')}."


def _silence(path, seconds, rate):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\0\0" * int(seconds * rate))


def _len(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def narrate(h, out_wav, workdir, rate=24000, narrate_fn=None):
    """Sprechspur (wav) für alle Kapitel. Gibt [(start_minute, titel, minuten)] und die Länge in Minuten zurück.

    Kapitel k beginnt bei start_minute*60 s, die Stimme 6 s später, danach Stille bis zur nächsten vollen Minute."""
    import sleepstory
    narrate_fn = narrate_fn or sleepstory.narrate
    parts, chapters, minute = [], [], 0
    for i, c in enumerate(h["chapters"]):
        speech = os.path.join(workdir, f"ch{i:02d}.wav")
        narrate_fn(_spoken_title(i, c) + "\n\n" + c["text"], speech, rate)
        secs = _len(speech)
        mins = max(1, math.ceil((VOICE_IN + secs + CHAPTER_GAP) / 60))
        lead, tail = os.path.join(workdir, f"ch{i:02d}-a.wav"), os.path.join(workdir, f"ch{i:02d}-b.wav")
        _silence(lead, VOICE_IN, rate)
        _silence(tail, mins * 60 - VOICE_IN - secs, rate)
        parts += [lead, speech, tail]
        chapters.append((minute, c["title"], mins))
        minute += mins
    lst = os.path.join(workdir, "narration.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-ar", str(rate), "-ac", "1", out_wav], check=True)
    return chapters, minute


def total_minutes(story_minutes):
    """Video-Länge: Geschichte plus mindestens 10 Minuten Szene, auf volle Stunden, 1 bis 3 Stunden."""
    need = story_minutes * 60 + TAIL_S
    return max(MIN_MIN, min(MAX_MIN, int(-(-need // 3600)) * 60))


# --- Bild: Kapitel-Karten über der Szene ------------------------------------------------------

def card_png(out, size, index, count, title, icon):
    """Durchsichtige Karte in Videogröße: Glas-Fläche unten links, Illustration (Emoji-Zeichnung), Kapitel und Titel."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    w, h = size
    s = w / 1920
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ft = ImageFont.truetype(FONT_SERIF, int(62 * s))
    fs = ImageFont.truetype(FONT_SEMI, int(26 * s))
    d = ImageDraw.Draw(img)
    title_w = d.textlength(title, font=ft)
    bw, bh = int(max(560 * s, title_w + 300 * s)), int(200 * s)
    x0, y0 = int(80 * s), h - int(80 * s) - bh
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x0, y0 + 10 * s, x0 + bw, y0 + bh + 10 * s), int(36 * s), fill=(0, 0, 0, 90))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(int(24 * s))))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), int(36 * s), fill=(16, 13, 11, 165), outline=(255, 244, 228, 46),
                        width=max(1, int(2 * s)))
    cx, cy, r = x0 + int(110 * s), y0 + bh // 2, int(66 * s)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(232, 199, 140, 40), outline=(232, 199, 140, 120), width=max(1, int(2 * s)))
    try:
        fe = ImageFont.truetype(FONT_EMOJI, 109)
        em = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(em).text((80, 80), icon, font=fe, embedded_color=True, anchor="mm")
        em = em.crop(em.getbbox() or (0, 0, 160, 160))
        k = int(84 * s) / max(em.size)
        em = em.resize((max(1, int(em.size[0] * k)), max(1, int(em.size[1] * k))), Image.LANCZOS)
        img.alpha_composite(em, (cx - em.size[0] // 2, cy - em.size[1] // 2))
    except (OSError, ValueError):
        pass
    tx = x0 + int(206 * s)
    d.text((tx, y0 + int(46 * s)), f"CHAPTER {index + 1} OF {count}", font=fs, fill=(232, 199, 140, 235))
    d.text((tx, y0 + int(84 * s)), title, font=ft, fill=(250, 244, 234, 250))
    img.save(out)
    return out


ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-tune", "animation", "-profile:v", "high",
       "-pix_fmt", "yuv420p", "-an"]


def _probe_video(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    st = j["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    return (int(st["width"]), int(st["height"])), float(j["format"]["duration"]), int(num) / int(den)


def chapter_video(loop_mp4, h, chapters, minutes, out_mp4, workdir):
    """Ganzes Bild (ohne Ton): je Kapitel Szene + Karte (die erste Minute blendet die Karte langsam ein), danach nur die Szene.
    Gebaut aus fertigen Stücken in Schleifenlänge, die nur noch hintereinander kopiert werden."""
    size, loop_s, fps = _probe_video(loop_mp4)
    frames = round(loop_s * fps)
    pieces = []
    plain = os.path.join(workdir, "plain.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", loop_mp4, "-frames:v", str(frames)] + ENC + [plain], check=True)
    for i, (start, title, mins) in enumerate(chapters):
        png = card_png(os.path.join(workdir, f"card{i:02d}.png"), size, i, len(chapters), title, h["chapters"][i]["icon"])
        first, rest = os.path.join(workdir, f"c{i:02d}a.mp4"), os.path.join(workdir, f"c{i:02d}b.mp4")
        fade = min(4.0, loop_s / 3)
        # genau so viele Bilder wie die Schleife (overlay mit shortest/fps verliert sonst das letzte Bild, das summiert sich)
        img = ["-loop", "1", "-framerate", f"{fps:g}", "-i", png]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", loop_mp4] + img + ["-filter_complex",
                        f"[1:v]format=rgba,fade=in:st=0.5:d={fade:g}:alpha=1[c];[0:v][c]overlay=0:0[v]",
                        "-map", "[v]", "-frames:v", str(frames)] + ENC + [first], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", loop_mp4] + img + ["-filter_complex",
                        "[0:v][1:v]overlay=0:0[v]", "-map", "[v]", "-frames:v", str(frames)] + ENC + [rest], check=True)
        n = max(1, round(mins * 60 / loop_s))
        pieces += [first] + [rest] * (n - 1)
    used = sum(c[2] for c in chapters) * 60
    pieces += [plain] * max(1, math.ceil((minutes * 60 - used) / loop_s))
    lst = os.path.join(workdir, "video.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in pieces)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    "-t", str(minutes * 60), out_mp4], check=True)
    return out_mp4


# --- Text --------------------------------------------------------------------------------------

def stamp(seconds):
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def meta(h, idea, minutes, chapters):
    """Titel, Beschreibung (mit Kapiteln ab 0:00) und Tags, Englisch."""
    import entspannung
    i = entspannung.IDEA[idea]
    hrs = entspannung.hours_en(minutes)
    title = f"{h['title']} to Fall Asleep To 🌙 | {hrs}"
    if len(title) > 100:
        title = f"{h['title']} 🌙 | {hrs}"
    end = sum(c[2] for c in chapters) * 60
    lines = [f"{h['title']}, told slowly and calmly so you can drift off. {h.get('about', '')}".strip(), "",
             f"The story is read over {i['sounds'].lower()}, which keep playing after the last chapter ({hrs.lower()} in total).",
             "", "Chapters:"]
    lines += [f"{stamp(start * 60)} {t}" for start, t, _ in chapters]
    lines += [f"{stamp(end)} Quiet {i['sounds'].lower()}", ""]
    if h.get("sources"):
        lines += ["Sources: " + "; ".join(h["sources"]), ""]
    lines += [DISCLOSURE, "", f"{entspannung.HASHTAGS[i['scene']]} #sleephistory #history #sleepstory"]
    tags, total = [], 0
    topic = h.get("topic") or h["title"].replace(PREFIX, "").strip()
    for t in ["sleep history", "history for sleep", "boring history for sleep", "history to fall asleep to",
              f"{topic.lower()} history", topic.lower(), "sleep story", "calm narration"] + entspannung.KEYWORDS[i["scene"]]:
        if t not in tags and total + len(t) + 3 <= 480:
            tags.append(t)
            total += len(t) + 3
    return {"title": title, "description": "\n".join(lines), "tags": tags, "thumb_text": h.get("thumb")}


def build_into(h, idea, loop_mp4, loop_wav, tmp, out_mp4, rate, narrate_fn=None):
    """Für entspannung.build: Sprechspur + Kapitel-Bild + Mischung. Gibt (minuten, kapitel) zurück."""
    import sleepstory
    narr = os.path.join(tmp, "history.wav")
    chapters, story_min = narrate(h, narr, tmp, narrate_fn=narrate_fn)
    minutes = total_minutes(story_min)
    full = os.path.join(tmp, "history-video.mp4")
    chapter_video(loop_mp4, h, chapters, minutes, full, tmp)
    sleepstory.mux(full, loop_wav, narr, minutes, out_mp4, rate, lead=0)
    for f in glob.glob(os.path.join(tmp, "c[0-9][0-9]*.mp4")):
        os.remove(f)
    return minutes, chapters
