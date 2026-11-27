"""„Die GANZE Geschichte von … in X Minuten“ für den Hauptkanal (Phase I, Teil 2, seit 26.11.2026, Julius' Wunsch).

Einmal pro Woche, samstags, ersetzt ein langes Video mit Kapiteln das normale lange Video: eine große Geschichte komplett
erzählt (Mythologie, echte Geschichte, Märchen und Sagen, echte Rätsel; nur Stoffe ohne Urheberrecht), 15 bis 40 Minuten,
Strichmännchen oder Blockwelt, Stimme „klar“. Die Skripte liegen in `seed-long/` (Kapitel-Liste, die tägliche Skript-Aufgabe
schreibt 1 pro Woche, Regeln in CLAUDE.md) und kommen wie `seed-en/` mit dem nächtlichen Update auf den Server.

Ablauf am Samstag: ab 6 Uhr rendern (ein so langes Video braucht viele Stunden), ab 19 Uhr hochladen. Titel und Thumbnail
bekommen die echte Minutenzahl („Die GANZE Geschichte der griechischen Götter in 18 Minuten“, Thumbnail: Thema riesig +
Minuten). Kapitel mit Zeitmarken in der Beschreibung. Klappt etwas nicht, kommt das normale lange Video.

Danach schneidet die App aus dem fertigen Video 5 Shorts: je Kapitel der Ausschnitt mit der besten Hook-Prüfung (wie bei
normalen Shorts), 9:16 mit weichem Hintergrund, oben die Kapitel-Zeile, unten „Ganze Geschichte auf dem Kanal“.
Ein „verknüpftes Video“ kann man über die YouTube-API nicht setzen, darum steht der Link in der Beschreibung.
Ab dem nächsten Tag geht 1 Ausschnitt pro Tag auf einen normalen Sendeplatz ab 12 Uhr.

Lernmerkmal „Ganze Geschichte (lange Videos)“: ganze Geschichte gegen normale lange Videos (Aufrufe, Wiedergabezeit).
"""
import datetime as dt
import glob
import json
import os
import re
import threading

import hookcheck
import store

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.environ.get("LONG_SEED_DIR", os.path.join(HERE, "seed-long"))
FILE = "ganze.json"
WORK = "ganze"           # data/ganze/: fertiges Video und Ausschnitte
WEEKDAY = 5              # Samstag
RENDER_HOUR = 6
POST_HOUR = 19
CUTS = 5
CUT_HOUR = 12            # Ausschnitte gehen ab 12 Uhr auf einen normalen Sendeplatz, 1 pro Tag
CUT_MIN_S, CUT_MAX_S, CUT_GOAL_S = 18.0, 42.0, 28.0
HINT = "Ganze Geschichte auf dem Kanal"
DISCLOSURE = "Die Stimme ist synthetisch (KI-Stimme), alle Bilder sind selbst gezeichnet. Sagen sind als Sagen gekennzeichnet."
W, H = 1080, 1920
FONT_BLACK = os.path.join(HERE, "fonts", "InterDisplay-Black.otf")
FONT_SEMI = os.path.join(HERE, "fonts", "InterDisplay-SemiBold.otf")
_run = threading.Lock()


# --- Skripte ----------------------------------------------------------------------------------

def flatten(spec):
    """Kapitel-Skript -> normales langes Cartoon-Skript (segments) plus Kapitelanfänge [(index, titel)]."""
    segs, marks = [], []
    for k in spec.get("kapitel") or []:
        if not k.get("segments"):
            continue
        marks.append((len(segs), k.get("titel") or f"Kapitel {len(marks) + 1}"))
        segs += [dict(s) for s in k["segments"]]
    out = {k: v for k, v in spec.items() if k != "kapitel"}
    return {**out, "segments": segs, "laenge": "lang", "format": "ganze", "stil": spec.get("stil", "cartoon"),
            "stimme": "klar", "_chapters": marks}


def scripts():
    """Alle Skripte aus seed-long/ (nach Dateiname), schon flach. Kaputte Dateien werden übersprungen."""
    out = []
    for p in sorted(glob.glob(os.path.join(DIR, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                spec = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(spec, dict) and spec.get("slug") and spec.get("kapitel"):
            out.append((os.path.basename(p), flatten(spec)))
    return out


def words(spec):
    return sum(len(str(s.get("text", "")).split()) for s in spec.get("segments", []))


def load():
    d = store.read(FILE, {}) or {}
    return {"on": True, "week": None, "status": None, "reason": None, "rendered": None, "uploads": [], "cuts": [], **d}


def save(**kw):
    with store.LOCK:
        d = load()
        d.update(kw)
        store.write(FILE, d)
        return d


def next_script(d=None):
    d = d or load()
    used = {u.get("name") for u in d["uploads"]}
    return next(((n, s) for n, s in scripts() if n not in used), None)


def week_key(now):
    return now.strftime("%Y-%m-%d")


# --- Titel, Kapitel, Thumbnail ------------------------------------------------------------------

def _mmss(s):
    s = int(round(s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def chapter_times(spec, timings):
    """[(sekunde, titel)] aus den Satzzeiten. Das erste Kapitel beginnt immer bei 0:00 (Regel von YouTube)."""
    out = []
    for i, (idx, title) in enumerate(spec.get("_chapters") or []):
        t = 0.0 if i == 0 else float(timings[min(idx, len(timings) - 1)][0])
        out.append((t, title))
    return out


def minutes_of(total):
    return max(1, int(round(total / 60)))


def finish_spec(spec, total, timings):
    """Nach dem Rendern: echte Minutenzahl in Titel und Thumbnail, Kapitel in die Beschreibung."""
    m = minutes_of(total)
    thema = spec.get("thema") or spec.get("title", "")
    title = (spec.get("title") or "").replace("{min}", str(m)).replace("X Minuten", f"{m} Minuten")
    if "{min}" not in (spec.get("title") or "") and "Minuten" not in title:
        title = f"{title} in {m} Minuten"
    ch = chapter_times(spec, timings)
    desc = (spec.get("description") or "").rstrip()
    lines = [desc, "", "Kapitel:"] + [f"{_mmss(t)} {txt}" for t, txt in ch]
    if spec.get("quellen"):
        lines += ["", "Geprüft mit: " + ", ".join(spec["quellen"])]
    lines += ["", DISCLOSURE]
    return {**spec, "title": title[:100], "description": "\n".join(lines).strip(),
            "thumb_text": [f"{thema} | in {m} Minuten", f"Alles in {m} Minuten"], "_minutes": m, "_chapter_times": ch}


# --- Ausschnitte: die 5 stärksten Kapitel-Momente -----------------------------------------------

def moments(spec, timings, n=CUTS):
    """Je Kapitel das Fenster aus ganzen Sätzen (18 bis 42 s) mit der besten Hook-Prüfung, davon die n besten.
    Ein Satz mit "kurz": true im Skript wird bevorzugt. Gibt [{start, end, segs, chapter, score}] zurück."""
    segs = spec.get("segments") or []
    marks = [i for i, _ in spec.get("_chapters") or [(0, "")]] + [len(segs)]
    names = [t for _, t in spec.get("_chapters") or [(0, "")]]
    best = []
    for c in range(len(marks) - 1):
        lo, hi = marks[c], min(marks[c + 1], len(timings))
        cand = None
        for i in range(lo, hi):
            for j in range(i + 1, hi + 1):
                dur = timings[j - 1][1] - timings[i][0]
                if dur > CUT_MAX_S:
                    break
                if dur < CUT_MIN_S:
                    continue
                win = segs[i:j]
                chk = hookcheck.check({"segments": win, "niche": spec.get("niche", ""), "stil": "cartoon"})
                score = chk["score"] + (2 if win[0].get("kurz") else 0) - abs(dur - CUT_GOAL_S) / 30
                if not cand or score > cand["score"]:
                    cand = {"start": round(timings[i][0], 2), "end": round(timings[j - 1][1], 2), "first": i, "last": j,
                            "chapter": names[c], "score": round(score, 2), "hook": chk["score"]}
        if cand:
            best.append(cand)
    best.sort(key=lambda x: -x["score"])
    return sorted(best[:n], key=lambda x: x["start"])


def cut_spec(spec, m, long_id, k):
    """Titel und Text für einen Ausschnitt. Link zum langen Video in der Beschreibung (verknüpftes Video geht per API nicht)."""
    first = str(spec["segments"][m["first"]]["text"]).replace("*", "").strip()
    thema = spec.get("thema") or ""
    title = first if len(first) <= 58 and first.endswith("?") else f"{m['chapter']}: {thema}"
    title = re.sub(r"\s+", " ", title)[:60].rstrip(" ,:")
    return {"slug": f"{spec['slug']}-ausschnitt-{k + 1}", "title": title, "niche": spec.get("niche"), "stil": "cartoon",
            "segments": spec["segments"][m["first"]:m["last"]], "ausschnitt": True, "quelle_lang": long_id,
            "description": (f"Ausschnitt aus „{spec.get('_upload_title') or spec.get('title')}“, Kapitel „{m['chapter']}“.\n"
                            f"Die ganze Geschichte: https://youtu.be/{long_id}\n\n{DISCLOSURE}\n\n#shorts #geschichte"),
            "tags": (spec.get("tags") or [])[:8] + ["shorts"], "language": "de"}


def overlay_png(out, top, bottom):
    """Durchsichtiges 1080x1920-Bild: oben die Kapitel-Zeile, unten der Hinweis auf die ganze Geschichte."""
    from PIL import Image, ImageDraw, ImageFont
    import zusammenschnitt as zs
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(FONT_BLACK, 76)
    y = 250
    for line in zs._wrap(d, top, f1, W - 140, 3):
        x = (W - d.textlength(line, font=f1)) / 2
        d.text((x + 3, y + 4), line, font=f1, fill=(0, 0, 0, 170))
        d.text((x, y), line, font=f1, fill=(255, 255, 255, 255))
        y += 92
    f2 = ImageFont.truetype(FONT_SEMI, 46)
    tw = d.textlength(bottom, font=f2)
    bx, by = (W - tw) / 2 - 36, 1480
    d.rounded_rectangle((bx, by, bx + tw + 72, by + 92), 46, fill=(10, 132, 255, 235))
    d.text((bx + 36, by + 18), bottom, font=f2, fill=(255, 255, 255, 255))
    img.save(out)
    return out


def cut_video(src, start, end, out, top, bottom=HINT):
    """Ausschnitt 9:16: das Querformat in der Mitte, dahinter dieselbe Szene groß und weich, dazu Text oben und unten."""
    import zusammenschnitt as zs
    png = out + ".png"
    overlay_png(png, top, bottom)
    fc = (f"[0:v]split=2[a][b];[a]scale=-2:{H},crop={W}:{H},boxblur=28:2,eq=brightness=-0.16[bg];"
          f"[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2[m];[m][1:v]overlay=0:0,fps=30,format=yuv420p[v]")
    zs._ff(["-ss", f"{start:.2f}", "-t", f"{end - start + 0.4:.2f}", "-i", src, "-i", png, "-filter_complex", fc,
            "-map", "[v]", "-map", "0:a:0?", "-af", "afade=t=out:st=%.2f:d=0.4" % max(0, end - start), "-shortest"]
           + zs.ENC + [out])
    os.remove(png)
    return out


def make_cuts(spec, video, timings, long_id, folder=None):
    """5 Ausschnitte aus dem fertigen Video. Gibt [{file, spec, duration, chapter}] zurück (Fehler je Ausschnitt egal)."""
    folder = folder or store.path(WORK)
    os.makedirs(folder, exist_ok=True)
    out = []
    for k, m in enumerate(moments(spec, timings)):
        cs = cut_spec(spec, m, long_id, k)
        f = os.path.join(folder, f"{cs['slug']}.mp4")
        try:
            cut_video(video, m["start"], m["end"], f, m["chapter"])
        except Exception as e:  # noqa: BLE001
            store.log("warn", f"Ausschnitt {k + 1} nicht geschnitten: {e}", agent="studio")
            continue
        out.append({"file": f, "spec": cs, "duration": round(m["end"] - m["start"], 1), "chapter": m["chapter"],
                    "hook": m["hook"], "posted": None})
    return out


# --- Ablauf am Samstag --------------------------------------------------------------------------

def active(now=None):
    """Samstag, an und es gibt ein Skript: dann gehört das lange Video heute der ganzen Geschichte."""
    now = now or store.now()
    d = load()
    if not d["on"] or now.weekday() != WEEKDAY:
        return False
    if d["week"] == week_key(now):
        return d["status"] not in ("übersprungen", "fehler", "hochgeladen")
    return next_script(d) is not None


def due(now=None):
    now = now or store.now()
    return active(now) and now.hour >= RENDER_HOUR


def run(now=None, render=None, upload=None, thumbs=None, cut=True):
    """Ein Schritt: rendern (ab 6 Uhr), hochladen (ab 19 Uhr), dann 5 Ausschnitte schneiden.

    render(spec) -> {video, total, timings, look, spec}; upload(path, spec) -> video_id; thumbs(spec, vid) -> Variante."""
    if not _run.acquire(blocking=False):
        return None
    try:
        now = now or store.now()
        if not due(now):
            return None
        key = week_key(now)
        d = load()
        if d["week"] != key:
            old = (d.get("rendered") or {}).get("video")
            if old and os.path.exists(old):
                os.remove(old)   # von letzter Woche liegengeblieben (z. B. Neustart mitten im Upload)
            d = save(week=key, status=None, reason=None, rendered=None)
        if key in store.state().get("long_slots", []):
            return save(status="übersprungen", reason="Das lange Video lief heute schon.")
        r = d.get("rendered")
        if not r or not os.path.exists(r.get("video") or ""):
            nxt = next_script(d)
            if not nxt:
                return save(status="übersprungen", reason="Kein neues Skript in seed-long/.")
            name, spec = nxt
            save(status="rendert", name=name, title=spec["title"])
            store.log("info", f"Rendert „Die ganze Geschichte“: {spec.get('thema') or spec['title']} ({words(spec)} Wörter). "
                      "Das dauert einige Stunden.", agent="studio")
            try:
                res = render(spec)
            except Exception as e:  # noqa: BLE001
                store.log("error", f"Ganze Geschichte nicht gerendert: {e}. Um 19 Uhr kommt das normale lange Video.",
                          agent="studio")
                return save(status="fehler", reason=str(e)[:200])
            r = {"name": name, "video": res["video"], "total": res["total"], "timings": res["timings"],
                 "look": res.get("look") or {}, "spec": res.get("spec") or spec}
            d = save(status="fertig", rendered=r)
        if now.hour < POST_HOUR:
            return d
        spec = finish_spec(r["spec"], r["total"], r["timings"])
        try:
            vid = upload(r["video"], spec)
        except Exception as e:  # noqa: BLE001
            store.log("error", f"Upload fehlgeschlagen: Ganze Geschichte ({e}). Um 19 Uhr kommt das normale lange Video.",
                      agent="publisher", kind="error")
            return save(status="fehler", reason=str(e)[:200])
        variant = None
        try:
            variant = thumbs(spec, vid) if thumbs else None
        except Exception:  # noqa: BLE001
            variant = None
        record(r, spec, vid, now, variant)
        cuts = []
        if cut:
            try:
                cuts = make_cuts({**spec, "_upload_title": spec["title"]}, r["video"], r["timings"], vid)
            except Exception as e:  # noqa: BLE001
                store.log("warn", f"Ausschnitte nicht geschnitten: {e}", agent="studio")
        try:
            os.remove(r["video"])
        except OSError:
            pass
        store.log("ok", f"Gepostet: {spec['title']}" + (f" ({len(cuts)} Ausschnitte warten)" if cuts else ""),
                  agent="publisher", kind="posted", source="youtube")
        d = load()
        return save(status="hochgeladen", rendered=None, cuts=(d["cuts"] + cuts)[-20:],
                    uploads=d["uploads"] + [{"name": r["name"], "video_id": vid, "title": spec["title"],
                                             "minutes": spec["_minutes"], "at": now.isoformat(timespec="seconds")}])
    finally:
        _run.release()


def _keep_spec(spec):
    """Skript in posted/ ablegen, damit „Was am besten funktioniert“ Merkmale und Sätze findet."""
    keep = {k: v for k, v in spec.items() if not k.startswith("_")}
    store.write(os.path.join("posted", f"ganze-{spec['slug']}.json"), keep)


def record(r, spec, vid, now, variant):
    """Eintrag in uploads (lang, ganze) und das lange Video für heute als erledigt markieren."""
    _keep_spec(spec)
    with store.LOCK:
        st = store.state()
        key = week_key(now)
        st["long_slots"] = (st.get("long_slots", []) + [key])[-90:]
        total = float(r["total"])
        st["uploads"].append({"slot": key, "slug": spec["slug"], "video_id": vid, "title": spec["title"],
                              "posted_at": now.isoformat(timespec="seconds"), "duration": round(total, 1), "lang": True,
                              "ganze": True, "marks": [round(t[0] / total, 4) for t in r["timings"]] if total else None,
                              "look": {**(r.get("look") or {}), **({"thumbnail": variant} if variant else {})}})
        store.write("state.json", st)


# --- Ausschnitte posten (1 pro Tag auf einem normalen Sendeplatz) --------------------------------

def pending_cuts(d=None):
    d = d or load()
    return [c for c in d["cuts"] if not c.get("posted") and os.path.exists(c.get("file") or "")]


def cut_due(now=None):
    now = now or store.now()
    d = load()
    if not d["on"] or now.hour < CUT_HOUR or not pending_cuts(d):
        return None
    day = now.strftime("%Y-%m-%d")
    if any(str(c.get("posted") or "")[:10] == day for c in d["cuts"]):
        return None
    if any(str(u.get("at") or "")[:10] == day for u in d["uploads"]):
        return None   # nicht am selben Tag wie das lange Video
    return pending_cuts(d)[0]


def post_cut(slot, upload, now=None):
    """Lädt den nächsten Ausschnitt hoch. True: Platz erledigt."""
    now = now or store.now()
    c = cut_due(now)
    if not c:
        return False
    vid = upload(c["file"], c["spec"])
    store.write(os.path.join("posted", f"ganze-{c['spec']['slug']}.json"), c["spec"])
    with store.LOCK:
        st = store.state()
        if slot:
            st["done_slots"] = (st.get("done_slots", []) + [slot])[-90:]
        st["uploads"].append({"slot": slot, "slug": c["spec"]["slug"], "video_id": vid, "title": c["spec"]["title"],
                              "posted_at": now.isoformat(timespec="seconds"), "duration": c["duration"],
                              "ausschnitt": True, "quelle_lang": c["spec"].get("quelle_lang"),
                              "look": {"stimme": "klar", "ausschnitt": True}})
        store.write("state.json", st)
        d = load()
        for x in d["cuts"]:
            if x["file"] == c["file"]:
                x["posted"], x["video_id"] = now.isoformat(timespec="seconds"), vid
        store.write(FILE, d)
    try:
        os.remove(c["file"])
    except OSError:
        pass
    store.log("ok", f"Gepostet: {c['spec']['title']} (Ausschnitt aus der ganzen Geschichte)", agent="publisher",
              kind="posted", source="youtube")
    return True


# --- Vergleich und Karte ------------------------------------------------------------------------

def compare(posted):
    """Ganze Geschichte gegen normale lange Videos: Ø Aufrufe und Ø Wiedergabe (Minuten pro Aufruf)."""
    groups = {"ganze": [], "normal": []}
    for v in posted or []:
        if not v.get("lang") or v.get("zusammenschnitt"):
            continue
        groups["ganze" if v.get("ganze") else "normal"].append(v)
    out = {}
    for k, vs in groups.items():
        views = [int(v.get("views") or 0) for v in vs]
        durs = [float(v["avg_dur"]) / 60 for v in vs if v.get("avg_dur")]
        out[k] = {"n": len(vs), "views": round(sum(views) / len(views)) if views else None,
                  "watch_min": round(sum(durs) / len(durs), 1) if durs else None}
    return out


def next_saturday(now):
    days = (WEEKDAY - now.weekday()) % 7
    nxt = (now + dt.timedelta(days=days)).replace(hour=POST_HOUR, minute=0, second=0, microsecond=0)
    d = load()
    if nxt <= now or (d["week"] == week_key(now) and d["status"] in ("hochgeladen", "übersprungen", "fehler")):
        nxt += dt.timedelta(days=7)
    return nxt


def overview(posted=None, now=None):
    """Für die Karte im Sendeplan."""
    now = now or store.now()
    d = load()
    nxt = next_script(d)
    last = d["uploads"][-1] if d["uploads"] else None
    if last and posted is not None:
        v = next((p for p in posted if p.get("video_id") == last["video_id"]), None)
        last = {**last, "views": (v or {}).get("views")}
    return {"on": d["on"], "next": next_saturday(now).isoformat(timespec="minutes"), "status": d["status"],
            "week": d["week"], "reason": d["reason"],
            "script": {"title": nxt[1].get("thema") or nxt[1]["title"], "words": words(nxt[1]),
                       "minutes": round(words(nxt[1]) / 150)} if nxt else None,
            "waiting": sum(1 for n, _ in scripts() if n not in {u.get("name") for u in d["uploads"]}),
            "last": last, "cuts_waiting": len(pending_cuts(d)),
            "cuts_posted": sum(1 for c in d["cuts"] if c.get("posted")),
            "compare": compare(posted) if posted is not None else None}
