"""Lange Entspannungsvideos (seit 20.11.2026, Julius' Wunsch): Lagerfeuer, Regen oder Pendel-Welle, z. B. 1 Stunde.

Alles selbst gezeichnet (cartoon/web/ambient.js) und selbst vertont (audio.ambience), keine fremden Clips oder Musik.
Gerendert wird nur eine nahtlose Schleife (LOOP_S Sekunden, alle Bewegungen sind darauf gerundet). ffmpeg hängt sie
ohne neues Kodieren aneinander, darum dauert eine Stunde kaum länger als eine Minute.

Aufruf zum Testen: python entspannung.py feuer 60 ausgabe-ordner   (Art, Minuten, Ordner)
"""
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

import audio
import cartoon

LOOP_S = 60      # Länge der Schleife; Vielfaches von 30 (die Pendel-Welle wiederholt sich alle 30 s)
FPS = 30
RATE = 48000
KINDS = {
    "feuer": {"name": "Lagerfeuer", "emoji": "🔥", "title": "Lagerfeuer unter Sternen {emoji} {dauer} Knistern zum Einschlafen",
              "thumb": ["LAGERFEUER", "zum Einschlafen"],
              "text": "Ein ruhiges Lagerfeuer unter dem Sternenhimmel mit leisem Knistern. Zum Einschlafen, Lernen oder Abschalten."},
    "regen": {"name": "Regen", "emoji": "🌧️", "title": "Regen am Fenster {emoji} {dauer} zum Einschlafen und Lernen",
              "thumb": ["REGEN", "am Fenster"],
              "text": "Regen an der Fensterscheibe, dahinter verschwommene Stadtlichter. Gleichmäßiges Rauschen zum Einschlafen, Lernen oder Abschalten."},
    "pendel": {"name": "Pendel-Welle", "emoji": "🌈", "title": "Bunte Pendel-Welle {emoji} {dauer} zum Abschalten",
               "thumb": ["PENDEL", "einfach zuschauen"],
               "text": "Bunte Kugeln schwingen jede in ihrem eigenen Takt und bilden immer neue Muster. Mit leisem Ticken und ruhigen Klängen."},
}

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>@font-face{font-family:Poppins;font-weight:700;src:url(fonts/Poppins-Bold.ttf)}
@font-face{font-family:CEmoji;src:url(fonts/NotoColorEmoji.ttf)}body{margin:0;background:#000}</style></head><body>
<canvas id="c"></canvas>
<script>const PLAN={wide:true}; const LOOP=%d; const ART=%s;</script>
<script src="lib.js"></script><script src="ambient.js"></script>
<script>
const cv = document.getElementById('c'); cv.width = W; cv.height = H; const cx = cv.getContext('2d');
window.TOTAL_FRAMES = LOOP * FPS;
window.renderFrame = f => {
  const t = f / FPS;
  cx.setTransform(1, 0, 0, 1, 0, 0); drawAmbient(cx, ART, t, W, H);
  const g = cx.createRadialGradient(W / 2, H / 2, H * .45, W / 2, H / 2, W * .75);   // weicher Rand
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.45)'); cx.fillStyle = g; cx.fillRect(0, 0, W, H);
};
window.grab = (q = .92) => cv.toDataURL('image/jpeg', q);
window.READY = true;
</script></body></html>"""


MINUTES = (60, 120, 180, 300, 480)   # erlaubte Längen (1, 2, 3, 5, 8 Stunden)
HOURS = list(range(0, 24))


def next_kind(n):
    """Welche Art als nächstes dran ist: reihum Feuer, Regen, Pendel."""
    order = list(KINDS)
    return order[n % len(order)]


def is_due(cfg, last_date, now, tried_at=None):
    """True, wenn heute noch kein Entspannungsvideo kam, die Uhrzeit erreicht ist und der letzte Versuch eine Stunde her ist.

    last_date: Datum (YYYY-MM-DD) des letzten erfolgreichen Uploads, now: aktuelle Zeit (mit Zeitzone der Zentrale),
    tried_at: ISO-Zeit des letzten (fehlgeschlagenen) Versuchs.
    """
    if not (cfg.get("relax_token") and cfg.get("relax_on", True)):
        return False
    if last_date == now.date().isoformat() or now.hour < int(cfg.get("relax_hour", 17)):
        return False
    if tried_at and (now - __import__("datetime").datetime.fromisoformat(tried_at)).total_seconds() < 3600:
        return False
    return True


def dauer_text(minutes):
    return f"{minutes // 60} Stunde{'n' if minutes >= 120 else ''}" if minutes % 60 == 0 else f"{minutes} Minuten"


def meta(kind, minutes):
    """Titel, Beschreibung und Stichwörter für YouTube."""
    k = KINDS[kind]
    d = dauer_text(minutes)
    return {"title": k["title"].format(emoji=k["emoji"], dauer=d),
            "description": f"{k['text']}\n\n{d} ohne Unterbrechung, ohne Stimme und ohne Musik von anderen. "
                           "Bild und Ton sind selbst gemacht.",
            "tags": [k["name"], "Entspannung", "Einschlafen", "Schlafen", "Lernen", "Ambiente", "Ruhe", "Konzentration"],
            "thumb_text": k["thumb"]}


def _page(kind, folder):
    cartoon.stage({"scenes": [], "words": [], "dur": LOOP_S, "wide": True}, folder)
    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as f:
        f.write(PAGE % (LOOP_S, json.dumps(kind)))


def render_loop(kind, mp4, wav, seed=1):
    """Eine nahtlose Schleife: Bild (ohne Ton) und Ton getrennt."""
    with tempfile.TemporaryDirectory(prefix="relax-") as tmp:
        _page(kind, tmp)
        pw, browser, page = cartoon.open_page(tmp, wide=True)
        try:
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                                   "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                                   "-profile:v", "high", "-g", str(FPS * 2), "-pix_fmt", "yuv420p", "-an", mp4],
                                  stdin=subprocess.PIPE)
            for jpg in cartoon.frames(page):
                ff.stdin.write(jpg)
            ff.stdin.close()
            if ff.wait() != 0:
                raise RuntimeError("ffmpeg konnte die Schleife nicht erstellen")
        finally:
            browser.close()
            pw.stop()
    sound = audio.ambience(kind, LOOP_S, RATE, seed, loop=True) * 0.5
    pcm = (np.clip(sound, -1, 1) * 32767).astype(np.int16)
    with wave.open(wav, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(pcm.tobytes())


def thumbnail(kind, loop_mp4, path):
    """Thumbnail 1280x720: ein Bild aus der Schleife mit großem Wort und kleiner Zeile."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    here = os.path.dirname(os.path.abspath(__file__))
    still = path + ".still.jpg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "7", "-i", loop_mp4, "-frames:v", "1", still], check=True)
    img = Image.open(still).convert("RGB").resize((1280, 720), Image.LANCZOS)
    os.remove(still)
    big, small = KINDS[kind]["thumb"]
    d = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(os.path.join(here, "fonts", "InterDisplay-Black.otf"), 120)
    f2 = ImageFont.truetype(os.path.join(here, "fonts", "InterDisplay-SemiBold.otf"), 52)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for xy, txt, fnt in (((70, 60), big, f1), ((76, 200), small, f2)):
        sd.text((xy[0] + 4, xy[1] + 6), txt, font=fnt, fill=(0, 0, 0, 200))
    img.paste(shadow.filter(ImageFilter.GaussianBlur(8)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(8)))
    d.text((70, 60), big, font=f1, fill=(255, 255, 255))
    d.text((76, 200), small, font=f2, fill=(255, 214, 120))
    img.save(path, "JPEG", quality=90)


def build(kind, minutes, out_dir, seed=1):
    """Fertiges Video (mp4), Thumbnail (jpg) und Text (json) im Ordner. Gibt die Pfade zurück."""
    if kind not in KINDS:
        raise ValueError(f"Unbekannte Art {kind}, erlaubt: {', '.join(KINDS)}")
    os.makedirs(out_dir, exist_ok=True)
    name = f"entspannung-{kind}-{minutes}min"
    mp4 = os.path.join(out_dir, name + ".mp4")
    with tempfile.TemporaryDirectory(prefix="relax-out-") as tmp:
        loop_mp4, loop_wav = os.path.join(tmp, "loop.mp4"), os.path.join(tmp, "loop.wav")
        render_loop(kind, loop_mp4, loop_wav, seed)
        thumb = os.path.join(out_dir, name + ".jpg")
        thumbnail(kind, loop_mp4, thumb)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", loop_mp4,
                        "-stream_loop", "-1", "-i", loop_wav, "-t", str(minutes * 60), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", str(RATE), "-movflags", "+faststart", mp4],
                       check=True)
    info = os.path.join(out_dir, name + ".json")
    with open(info, "w", encoding="utf-8") as f:
        json.dump(meta(kind, minutes), f, ensure_ascii=False, indent=2)
    return {"video": mp4, "thumb": thumb, "info": info}


if __name__ == "__main__":
    print(build(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
