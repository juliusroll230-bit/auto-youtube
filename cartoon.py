"""Cartoon-Shorts: Strichmännchen-Szenen aus dem Baukasten in cartoon/web, gerendert im Browser.

Ein Skript mit "stil": "cartoon" hat pro Segment ein Feld "szene" (siehe cartoon/README.md).
Stimme und Musik kommen wie bei allen Shorts aus make_short.synthesize (Piper Thorsten).
Jedes Bild zeichnet Chromium (Playwright) auf eine Canvas, ffmpeg baut daraus das Video.

Aufruf zum Testen: python cartoon.py skript.json ausgabe-ordner
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import make_short
import numerals

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "cartoon", "web")
FPS = 30
CHROME = os.environ.get("CHROME_PATH", "")


TYPES = {"figur", "zwei", "gruppe", "objekt", "zahl", "jahr", "liste", "vergleich", "horror"}
PLACES = {"strand", "meer", "stadt", "wald", "feld", "nacht", "haus", "kinderzimmer", "keller", "schule", "buero",
          "labor", "weltall", "wueste", "burg", "dorf", "farbe"}
MOODS = {"freude", "angst", "staunen", "wut", "traurig", "denken", "cool", "neutral", "k_o"}
ACTIONS = {"steht", "zeigt", "winkt", "jubelt", "rennt", "zittert", "denkt", "faellt", "schockiert", "haende"}
COLORS = {"rot", "blau", "gelb", "gruen", "lila", "navy"}
HATS = {"keiner", "bandana", "matrose", "kapitaen", "krone", "zylinder", "helm", "muetze", "hexe", "ritter"}


def validate(spec):
    """Liste der Fehler in einem Cartoon-Skript (leer = in Ordnung)."""
    errs = []
    segs = spec.get("segments") or []
    if not 6 <= len(segs) <= 12:
        errs.append(f"{len(segs)} Segmente, erlaubt sind 6 bis 12")

    def fig(f, where):
        if not isinstance(f, dict):
            return
        if f.get("farbe") and f["farbe"] not in COLORS:
            errs.append(f"{where}: Farbe {f['farbe']}")
        if f.get("hut") and f["hut"] not in HATS:
            errs.append(f"{where}: Hut {f['hut']}")

    fig(spec.get("figur"), "figur")
    for i, seg in enumerate(segs, 1):
        sc = seg.get("szene")
        if not isinstance(sc, dict):
            errs.append(f"Segment {i}: Feld szene fehlt")
            continue
        typ = sc.get("typ")
        if typ not in TYPES:
            errs.append(f"Segment {i}: Typ {typ}")
        if sc.get("ort") and sc["ort"] not in PLACES:
            errs.append(f"Segment {i}: Ort {sc['ort']}")
        if sc.get("gefuehl") and sc["gefuehl"] not in MOODS:
            errs.append(f"Segment {i}: Gefühl {sc['gefuehl']}")
        if sc.get("aktion") and sc["aktion"] not in ACTIONS:
            errs.append(f"Segment {i}: Aktion {sc['aktion']}")
        fig(sc.get("figur"), f"Segment {i}")
        fig(sc.get("zweite"), f"Segment {i} zweite")
        if typ == "zahl" and not isinstance(sc.get("zahl"), (int, float)):
            errs.append(f"Segment {i}: zahl muss eine Zahl sein")
        if typ == "jahr" and not sc.get("jahr"):
            errs.append(f"Segment {i}: jahr fehlt")
        if typ == "liste" and not 2 <= len(sc.get("punkte") or []) <= 4:
            errs.append(f"Segment {i}: liste braucht 2 bis 4 punkte")
        if typ == "vergleich" and not (sc.get("links") and sc.get("rechts")):
            errs.append(f"Segment {i}: vergleich braucht links und rechts")
        if typ == "objekt" and not sc.get("objekt"):
            errs.append(f"Segment {i}: objekt (Emoji) fehlt")
        for k in ("text", "tafel"):
            if len(str(sc.get(k) or "")) > 22:
                errs.append(f"Segment {i}: {k} länger als 22 Zeichen")
    return errs


def word_times(segments, timings):
    """Wort-Zeiten für die Untertitel: jeder Satz bekommt seine Zeit, die Wörter teilen sie nach Länge."""
    words = []
    for li, (seg, (s0, s1)) in enumerate(zip(segments, timings)):
        toks = seg["text"].replace("*", "").split()
        weights = [len(re.sub(r"\W", "", w)) + 2 + (4 if re.search(r"[,.:;?!]$", w) else 0) for w in toks]
        total, acc = sum(weights) or 1, 0
        for w, x in zip(toks, weights):
            st = s0 + (s1 - s0) * acc / total
            acc += x
            words.append({"w": numerals.display_word(w), "s": round(st, 3), "line": li})
    for i, w in enumerate(words):
        nxt = words[i + 1]["s"] if i + 1 < len(words) else timings[-1][1]
        w["e"] = round(min(nxt, w["s"] + 1.2), 3)
    return words


def plan(spec, timings, total):
    segs = spec["segments"]
    scenes = []
    for i, seg in enumerate(segs):
        sc = dict(seg.get("szene") or {"typ": "objekt", "objekt": seg.get("emoji") or "❓"})
        sc.setdefault("ort", spec.get("ort") or "feld")
        sc["start"] = 0.0 if i == 0 else round(timings[i][0], 3)
        sc["end"] = round(timings[i + 1][0], 3) if i + 1 < len(segs) else round(total, 3)
        scenes.append(sc)
    for sc in scenes:  # gleiche Figur im ganzen Video, wenn die Szene nichts anderes sagt
        sc.setdefault("figur", spec.get("figur") or {"farbe": "rot"})
    return {"scenes": scenes, "words": word_times(segs, timings), "dur": round(total, 3)}


def stage(p, folder):
    """Legt die Seite mit dem Plan in einen eigenen Ordner."""
    shutil.copytree(WEB, folder, dirs_exist_ok=True)
    emoji_font = os.path.join(HERE, "fonts", "NotoColorEmoji.ttf")
    shutil.copy(emoji_font, os.path.join(folder, "fonts", "NotoColorEmoji.ttf"))
    with open(os.path.join(folder, "plan.js"), "w", encoding="utf-8") as f:
        f.write("const PLAN=" + json.dumps(p, ensure_ascii=False) + ";")


def open_page(folder):
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(**({"executable_path": CHROME} if CHROME else {}),
                                 args=["--allow-file-access-from-files", "--no-sandbox"])
    page = browser.new_page(viewport={"width": 1080, "height": 1920})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("file://" + os.path.join(folder, "index.html"))
    page.wait_for_function("window.READY === true", timeout=20000)
    page.evaluate("async () => { await document.fonts.load('700 40px Poppins'); await document.fonts.load('40px CEmoji', '🦈'); }")
    if errors:
        browser.close()
        pw.stop()
        raise RuntimeError("Cartoon-Seite hat einen Fehler: " + errors[0])
    return pw, browser, page


def frames(page, times=None):
    """Gibt JPEG-Bilder zurück: alle Bilder des Videos oder nur die zu den Zeiten (Sekunden)."""
    total = page.evaluate("window.TOTAL_FRAMES")
    todo = [round(t * FPS) for t in times] if times else range(total)
    for f in todo:
        data = page.evaluate("f => { renderFrame(f); return grab(.9); }", min(f, total - 1))
        yield base64.b64decode(data.split(",", 1)[1])


def build_video(spec, out_dir, tts, stock_key=None, info=None):
    """Wie make_short.build_video, nur mit Cartoon-Bild. Gibt (mp4, dauer, satz-zeiten) zurück."""
    os.makedirs(out_dir, exist_ok=True)
    wav = os.path.join(out_dir, f"{spec['slug']}.wav")
    mp4 = os.path.join(out_dir, f"{spec['slug']}.mp4")
    timings, total = make_short.synthesize(tts, spec["segments"], wav, seed=sum(map(ord, spec["slug"])),
                                           speed=spec.get("voice_speed") or make_short.SPEED)
    total += make_short.TAIL
    if info is not None:
        info["stock"] = []
    with tempfile.TemporaryDirectory(prefix="cartoon-") as tmp:
        stage(plan(spec, timings, total), tmp)
        pw, browser, page = open_page(tmp)
        try:
            ff = subprocess.Popen([
                "ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg",
                "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high",
                "-g", str(FPS * 2), "-pix_fmt", "yuv420p", "-af", make_short.AUDIO_FILTER, "-ar", "48000",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4,
            ], stdin=subprocess.PIPE)
            for jpg in frames(page):
                ff.stdin.write(jpg)
            ff.stdin.close()
            if ff.wait() != 0:
                raise RuntimeError("ffmpeg konnte das Cartoon-Video nicht erstellen")
        finally:
            browser.close()
            pw.stop()
    os.remove(wav)
    return mp4, total, timings


def render_thumbnail(spec, path, width=360):
    """Vorschaubild: erste Szene nach 0,9 s, mit geschätzten Zeiten (ohne Stimme)."""
    from PIL import Image
    import io

    timings, total = make_short.estimated_timings(spec)
    with tempfile.TemporaryDirectory(prefix="cartoon-") as tmp:
        stage(plan(spec, timings, total), tmp)
        pw, browser, page = open_page(tmp)
        try:
            jpg = next(frames(page, [0.9]))
        finally:
            browser.close()
            pw.stop()
    img = Image.open(io.BytesIO(jpg)).convert("RGB")
    img.resize((width, int(width * img.height / img.width)), Image.LANCZOS).save(path, "JPEG", quality=84)


def stills(spec, times, out_dir):
    """Einzelbilder zum Prüfen (ohne Stimme, mit geschätzten Zeiten)."""
    os.makedirs(out_dir, exist_ok=True)
    timings, total = make_short.estimated_timings(spec)
    with tempfile.TemporaryDirectory(prefix="cartoon-") as tmp:
        stage(plan(spec, timings, total), tmp)
        pw, browser, page = open_page(tmp)
        try:
            paths = []
            for t, jpg in zip(times, frames(page, times)):
                p = os.path.join(out_dir, f"still_{t:05.2f}.jpg")
                open(p, "wb").write(jpg)
                paths.append(p)
            return paths
        finally:
            browser.close()
            pw.stop()


if __name__ == "__main__":
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    if len(sys.argv) > 2 and sys.argv[2] == "--check":
        bad = {s["slug"]: validate(s) for s in (data if isinstance(data, list) else [data])}
        bad = {k: v for k, v in bad.items() if v}
        print(json.dumps(bad, ensure_ascii=False) if bad else "ok")
        sys.exit(1 if any(bad.values()) else 0)
    tts = make_short.load_tts()
    for s in data if isinstance(data, list) else [data]:
        path, dur, _ = build_video(s, sys.argv[2], tts)
        print(f"{path}  {dur:.1f}s")
