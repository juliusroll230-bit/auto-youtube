"""Entspannungskanal „Quiet Corner“ (seit 20.11.2026, komplett automatisch seit 21.11.2026, Julius' Wunsch).

Lange, ruhige Videos (1 bis 3 Stunden, nahtlos geloopt): Regen-Zimmer, Kamin-Ecke, Café bei Nacht, Fantasy-Bibliothek,
Lagerfeuer im Wald. Alles selbst gezeichnet (cartoon/web/quiet.js) und selbst vertont (audio.soundscape), keine fremden
Clips oder Musik. Titel, Beschreibung und Tags sind Englisch (Zielgruppe weltweit), ruhig, ohne Kitsch.

Gerendert wird nur eine nahtlose Schleife (LOOP_S Sekunden). ffmpeg hängt sie ohne neues Kodieren aneinander, darum
dauert eine Stunde kaum länger als eine Minute. Nach dem langen Video kommt ein kurzer Teaser als Short.

Ideen: IDEAS (Szene + Wetter + Sound-Rezept + Texte). choose() wählt die nächste Idee und Länge: erst jede Szene und
Länge einmal, danach 3 von 4 Mal die Szene/Länge mit den meisten Aufrufen pro Tag, sonst die am längsten nicht gezeigte.

Zum Testen: python entspannung.py regen-fenster 2 ordner   (Idee, Minuten, Ordner)
           python entspannung.py branding ordner          (Banner, Profilbilder, Kanaltext)
"""
import datetime as _dt
import json
import os
import random
import subprocess
import sys
import tempfile
import wave

import numpy as np

import audio
import cartoon

LOOP_S = 60      # Länge der Schleife (die Uhr im Kamin dreht sich genau einmal)
FPS = 30
RATE = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
CHANNEL = "Quiet Corner"
LADDER = (600, 180, 60, 15)   # Notbremse: lehnt YouTube ein Video wegen der Länge ab, geht es in diesen Stufen kürzer weiter
MINUTES = (180, 300, 480, 600)   # 3, 5, 8, 10 Stunden (Julius 21.11.: „länger“); "auto" = Lernmodus wählt
SLOTS = (6, 17)   # Standard: 2 lange Videos am Tag (Julius 21.11.: „mehr“), ab 6 und ab 17 Uhr
HOURS = list(range(0, 24))
TEASER_S = 30

SCENES = {"regenzimmer": "Regen-Zimmer", "kamin": "Kamin-Ecke", "cafe": "Café bei Nacht",
          "bibliothek": "Fantasy-Bibliothek", "lagerfeuer": "Lagerfeuer im Wald"}

# Eine Idee = ein Bild + ein Klang. thumb: höchstens 3 Wörter. sounds: was man hört (für Titel und Beschreibung).
IDEAS = [
    {"id": "regen-fenster", "scene": "regenzimmer", "weather": "regen", "emoji": "🌧️",
     "title": "Rainy Night by the Window", "sounds": "Rain Sounds", "thumb": "Rainy Night",
     "recipe": {"scheibe": 1, "regen": .45, "uhr": .06},
     "text": "Rain runs down the window of a small, warm room. A candle, a cup of tea and a few plants on the sill.",
     "layers": "rain on the glass, steady rainfall outside, a faint clock"},
    {"id": "gewitter-zimmer", "scene": "regenzimmer", "weather": "gewitter", "emoji": "⛈️",
     "title": "Soft Thunderstorm in a Cozy Room", "sounds": "Thunderstorm Sounds", "thumb": "Soft Storm",
     "recipe": {"scheibe": 1, "regen": .5, "donner": .55},
     "text": "A gentle storm outside the window, distant thunder and heavy rain, while the room stays warm and quiet.",
     "layers": "heavy rain, rain on the glass, distant rolling thunder"},
    {"id": "schnee-fenster", "scene": "regenzimmer", "weather": "schnee", "emoji": "❄️",
     "title": "Snowy Evening by the Window", "sounds": "Winter Ambience", "thumb": "Snowy Evening",
     "recipe": {"wind": .55, "uhr": .12},
     "text": "Snow falls on the pine trees outside. Inside: a lamp, a candle and a steaming cup.",
     "layers": "soft winter wind, a quiet clock"},
    {"id": "kamin-schnee", "scene": "kamin", "weather": "schnee", "emoji": "🔥",
     "title": "Crackling Fireplace on a Snowy Night", "sounds": "Fireplace Sounds", "thumb": "Fireside",
     "recipe": {"kamin": 1, "wind": .25, "uhr": .1},
     "text": "A crackling fire in a stone fireplace, plants on the mantel and snow falling outside the window.",
     "layers": "crackling fire, soft wind, a ticking mantel clock"},
    {"id": "kamin-regen", "scene": "kamin", "weather": "regen", "emoji": "🔥",
     "title": "Fireplace and Rain on the Window", "sounds": "Fireplace & Rain Sounds", "thumb": "Fire & Rain",
     "recipe": {"kamin": 1, "scheibe": .5},
     "text": "A warm fire on a rainy evening. The rain taps on the window while the logs crackle.",
     "layers": "crackling fire, rain on the glass"},
    {"id": "kamin-ecke", "scene": "kamin", "weather": "schnee", "emoji": "🪴",
     "title": "Warm Fireplace Corner with Plants", "sounds": "Fireplace Sounds", "thumb": "Warm Corner",
     "recipe": {"kamin": 1, "wind": .12},
     "text": "An armchair, a blanket, a big plant and a fire that never goes out.",
     "layers": "crackling fire, a little wind"},
    {"id": "cafe-regen", "scene": "cafe", "weather": "regen", "emoji": "☕",
     "title": "Rainy Night Café", "sounds": "Coffee Shop Ambience & Rain", "thumb": "Night Café",
     "recipe": {"cafe": .55, "scheibe": .8, "regen": .3},
     "text": "A seat by the window of a small café. Rain on the glass, city lights outside, a warm coffee in front of you.",
     "layers": "quiet café murmur without words, cups and spoons, rain on the window"},
    {"id": "cafe-schnee", "scene": "cafe", "weather": "schnee", "emoji": "☕",
     "title": "Quiet Café on a Snowy Night", "sounds": "Coffee Shop Ambience", "thumb": "Snowy Café",
     "recipe": {"cafe": .6, "wind": .2},
     "text": "Snow falls past the café window. Warm lamps, a cup of coffee and soft voices in the background.",
     "layers": "quiet café murmur without words, cups and spoons, soft wind"},
    {"id": "cafe-gewitter", "scene": "cafe", "weather": "gewitter", "emoji": "⛈️",
     "title": "Café Window During a Thunderstorm", "sounds": "Thunderstorm & Café Sounds", "thumb": "Stormy Café",
     "recipe": {"cafe": .45, "scheibe": .9, "donner": .55},
     "text": "A storm rolls over the city. You sit inside a warm café and watch the rain.",
     "layers": "rain on the glass, distant thunder, quiet café murmur"},
    {"id": "bibliothek-mond", "scene": "bibliothek", "weather": "klar", "emoji": "🕯️",
     "title": "Moonlit Library with Floating Candles", "sounds": "Library Ambience", "thumb": "Moonlit Library",
     "recipe": {"kamin": .3, "uhr": .18, "seiten": .45, "wind": .15},
     "text": "Old shelves full of books, candles floating in the air and moonlight falling through a tall window.",
     "layers": "soft fire, turning pages, an old clock, a little wind"},
    {"id": "bibliothek-regen", "scene": "bibliothek", "weather": "regen", "emoji": "📚",
     "title": "Fantasy Library on a Rainy Night", "sounds": "Rain Sounds & Library Ambience", "thumb": "Rainy Library",
     "recipe": {"scheibe": .8, "seiten": .35, "kamin": .3},
     "text": "Rain on the arched window of an old library. Candles float above the shelves while you read.",
     "layers": "rain on the glass, turning pages, a soft fire"},
    {"id": "bibliothek-schnee", "scene": "bibliothek", "weather": "schnee", "emoji": "📚",
     "title": "Snowfall Outside an Old Library", "sounds": "Winter Library Ambience", "thumb": "Winter Library",
     "recipe": {"wind": .4, "kamin": .4, "seiten": .3},
     "text": "Snowflakes drift past a tall window. Inside it is warm, quiet and full of books.",
     "layers": "winter wind, a soft fire, turning pages"},
    {"id": "bibliothek-gewitter", "scene": "bibliothek", "weather": "gewitter", "emoji": "⛈️",
     "title": "Old Library in a Gentle Thunderstorm", "sounds": "Thunderstorm Sounds", "thumb": "Library Storm",
     "recipe": {"scheibe": .8, "donner": .5, "seiten": .25},
     "text": "Thunder far away, rain on the glass and the calm of an old library at night.",
     "layers": "rain on the glass, distant thunder, turning pages"},
    {"id": "lagerfeuer-sterne", "scene": "lagerfeuer", "weather": "klar", "emoji": "🔥",
     "title": "Campfire Under the Stars", "sounds": "Campfire Sounds", "thumb": "Campfire",
     "recipe": {"feuer": 1, "grillen": .2, "wind": .12},
     "text": "A small campfire at the edge of a pine forest. Sparks rise into a sky full of stars.",
     "layers": "crackling campfire, crickets, a light breeze"},
    {"id": "lagerfeuer-wald", "scene": "lagerfeuer", "weather": "klar", "emoji": "🌲",
     "title": "Quiet Forest Campfire at Night", "sounds": "Campfire & Forest Sounds", "thumb": "Night Campfire",
     "recipe": {"feuer": 1, "wind": .35},
     "text": "The forest is dark and still. Only the fire moves.",
     "layers": "crackling campfire, wind in the trees"},
]
IDEA = {i["id"]: i for i in IDEAS}
USES = ["for Sleeping, Studying & Relaxing", "for Deep Sleep & Relaxation", "for Reading, Studying & Focus", "for Sleep & Stress Relief"]

CHANNEL_DESCRIPTION = (
    "Quiet Corner is a small place to slow down.\n\n"
    "Slow bedtime stories read in a soft voice, over cozy rooms on rainy nights, crackling fireplaces, a café after dark, "
    "old libraries with floating candles and campfires under the stars. When the story ends, the sounds keep playing "
    "for the rest of the hour, with no sudden noises.\n\n"
    "Use them to fall asleep, to wind down or just to breathe for a moment. Stories are invented and narrated with a synthetic voice.\n\n"
    "Every picture and every sound is drawn and made by Quiet Corner. New video every day.")
CHANNEL_KEYWORDS = "cozy ambience rain sounds fireplace sleep study relax café ambience library ambience"

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>@font-face{font-family:Poppins;font-weight:700;src:url(fonts/Poppins-Bold.ttf)}
@font-face{font-family:Serif;src:url(fonts/DMSerifDisplay-Regular.ttf)}body{margin:0;background:#000}</style></head><body>
<canvas id="c"></canvas>
<script>const PLAN={wide:%s}; const LOOP=%d; const OPT=%s; const OVER=%s;</script>
<script src="lib.js"></script><script src="ambient.js"></script><script src="quiet.js"></script>
<script>
const cv = document.getElementById('c'); cv.width = W; cv.height = H; const cx = cv.getContext('2d');
window.TOTAL_FRAMES = Math.round((OVER ? OVER.dur : LOOP) * FPS);
function wrap(t, x, y, maxW, lh) {   // Text umbrechen und mittig setzen
  const words = t.split(' '), lines = []; let cur = '';
  for (const w of words) { const n = cur ? cur + ' ' + w : w; if (cx.measureText(n).width > maxW && cur) { lines.push(cur); cur = w; } else cur = n; }
  lines.push(cur); lines.forEach((l, i) => cx.fillText(l, x, y + i * lh)); return lines.length;
}
window.renderFrame = f => {
  const t = f / FPS;
  cx.setTransform(1, 0, 0, 1, 0, 0); drawQuiet(cx, OPT, t, W, H);
  if (OVER) {   // Teaser-Short: ruhiger Titel unten, blendet weich ein und am Ende aus
    const a = Math.min(1, Math.max(0, (t - .8) / 1.2)) * Math.min(1, Math.max(0, (OVER.dur - t) / 1.2));
    const g = cx.createLinearGradient(0, H * .58, 0, H); g.addColorStop(0, 'rgba(10,8,8,0)'); g.addColorStop(1, 'rgba(10,8,8,.82)');
    cx.fillStyle = g; cx.fillRect(0, H * .58, W, H * .42);
    cx.globalAlpha = a; cx.textAlign = 'center'; cx.fillStyle = '#f6eee2'; cx.shadowColor = 'rgba(0,0,0,.6)'; cx.shadowBlur = 18;
    cx.font = '88px Serif'; const n = wrap(OVER.title, W / 2, H * .74, W * .82, 100);
    cx.font = '700 38px Poppins'; cx.fillStyle = '#e7c98f'; cx.fillText(OVER.sub, W / 2, H * .74 + n * 100 + 30);
    cx.font = '700 30px Poppins'; cx.fillStyle = 'rgba(246,238,226,.75)'; cx.fillText('QUIET CORNER', W / 2, H * .93);
    cx.shadowBlur = 0; cx.globalAlpha = 1;
  }
};
window.grab = (q = .92) => cv.toDataURL('image/jpeg', q);
window.READY = true;
</script></body></html>"""


# ---------- Planung ----------
def slots(cfg):
    """Uhrzeiten der langen Videos: so viele wie relax_per_day (1 bis 3), die erste ab relax_hour."""
    n = max(1, min(3, int(cfg.get("relax_per_day", len(SLOTS)))))
    first = int(cfg.get("relax_hour", 17))
    extra = {1: [], 2: [6], 3: [6, 11]}[n]
    return sorted(set(extra + [first]))


def is_due(cfg, last_date, now, tried_at=None, done_today=None):
    """True, wenn für heute noch ein Sendeplatz offen ist (Uhrzeit erreicht) und der letzte Versuch eine Stunde her ist.

    last_date: Tag des letzten Uploads, done_today: wie viele es an diesem Tag schon waren (None = 1, wie früher).
    """
    if not (cfg.get("relax_token") and cfg.get("relax_on", True)):
        return False
    done = (1 if done_today is None else int(done_today)) if last_date == now.date().isoformat() else 0
    open_slots = [h for h in slots(cfg) if now.hour >= h]
    if done >= len(open_slots):
        return False
    if tried_at and (now - _dt.datetime.fromisoformat(tried_at)).total_seconds() < 3600:
        return False
    return True


def dauer_text(minutes):
    return f"{minutes // 60} Stunde{'n' if minutes >= 120 else ''}" if minutes % 60 == 0 else f"{minutes} Minuten"


def hours_en(minutes):
    h = minutes / 60
    return f"{int(h)} Hour{'s' if h != 1 else ''}" if h == int(h) else f"{minutes} Minutes"


def _per_day(u, today):
    """Aufrufe pro Tag seit dem Upload (frühestens ab Tag 2 bewertet, sonst None)."""
    try:
        age = (today - _dt.date.fromisoformat(u["at"])).days
    except (KeyError, ValueError):
        return None
    if age < 2 or u.get("views") is None:
        return None
    return u["views"] / age


def _pick(options, uploads, key, today, rnd):
    """Lernmodus für eine Eigenschaft (Szene oder Länge): erst jede einmal, dann 3 von 4 Mal die beste, sonst die älteste."""
    used = [u.get(key) for u in uploads]
    fresh = [o for o in options if o not in used]
    if fresh:
        return fresh[0]
    score = {}
    for o in options:
        vals = [v for v in (_per_day(u, today) for u in uploads if u.get(key) == o) if v is not None]
        if len(vals) >= 2:
            score[o] = sum(vals) / len(vals)
    if len(score) >= 2 and rnd.random() < .75:
        return max(score, key=score.get)
    last = {o: max((i for i, x in enumerate(used) if x == o), default=-1) for o in options}
    return min(options, key=lambda o: last[o])


def next_cap(minutes):
    """Nächstkürzere Stufe unter `minutes` (für den Fall, dass YouTube die Länge ablehnt)."""
    return next((m for m in LADDER if m < minutes), LADDER[-1])


def choose(uploads, length="auto", today=None, n=0, cap=None):
    """Nächste Idee und Länge. uploads: frühere Uploads mit idea, scene, minutes, at, views. cap: längste erlaubte Länge in Minuten."""
    today = today or _dt.date.today()
    rnd = random.Random(1000 + n)
    long_ups = [u for u in uploads if u.get("idea")]
    scene = _pick(list(SCENES), long_ups, "scene", today, rnd)
    ideas = [i for i in IDEAS if i["scene"] == scene]
    count = {i["id"]: sum(1 for u in long_ups if u.get("idea") == i["id"]) for i in ideas}
    last = long_ups[-1]["idea"] if long_ups else None
    idea = min(ideas, key=lambda i: (count[i["id"]], i["id"] == last, ideas.index(i)))
    minutes = int(length) if str(length).isdigit() and int(length) in MINUTES else _pick([480, 600, 300, 180], long_ups, "minutes", today, rnd)
    if cap and minutes > cap:
        options = [m for m in (480, 600, 300, 180) if m <= cap]
        minutes = _pick(options, long_ups, "minutes", today, rnd) if options else cap
    return idea["id"], minutes


# ---------- Lernmodus für Stil (Titel, Thumbnail, Klang, Uhrzeit) ----------
TITLE_STYLES = {"klassisch": "Bild, Suchbegriff und Zweck, Dauer am Ende", "dauer": "Dauer zuerst („10 Hours of …“)",
                "suche": "Suchbegriff und Zweck zuerst"}
THUMB_STYLES = {"links": "Text links, Dauer als goldene Plakette", "mitte": "Text groß in der Mitte, Dauer darunter"}
SOUND_STYLES = {"klar": "Klang klar und natürlich", "weich": "Klang weich (hohe Töne gedämpft)"}
STYLE_DEFAULT = {"title_style": "klassisch", "thumb_style": "links", "sound": "klar"}
STYLE_KEYS = {"title_style": TITLE_STYLES, "thumb_style": THUMB_STYLES, "sound": SOUND_STYLES}
LEARN_HOURS = (15, 17, 19, 21)   # mögliche Uhrzeiten für das letzte Video des Tages


def choose_style(uploads, today=None, n=0):
    """Wählt Titel-, Thumbnail- und Klang-Stil: erst jeden Stil einmal, dann 3 von 4 Mal den mit den meisten Aufrufen pro Tag.
    Ältere Uploads ohne Angabe zählen als Standard-Stil."""
    today = today or _dt.date.today()
    rnd = random.Random(2000 + n)
    ups = [u for u in uploads if u.get("idea") and not u.get("story")]
    out = {}
    for key, options in STYLE_KEYS.items():
        norm = [{**u, key: u.get(key) or STYLE_DEFAULT[key]} for u in ups]
        out[key] = _pick(list(options), norm, key, today, rnd)
    return out


def learned_hour(uploads, today=None, n=0):
    """Uhrzeit für das letzte Video des Tages (15, 17, 19 oder 21 Uhr) nach den Aufrufen pro Tag der bisherigen Uploads."""
    today = today or _dt.date.today()
    rnd = random.Random(3000 + n)
    ups = [u for u in uploads if u.get("slot_hour") in LEARN_HOURS]
    return _pick(list(LEARN_HOURS), ups, "slot_hour", today, rnd)


def slot_hour_now(cfg, now):
    """Zu welchem Sendeplatz gehört `now` (größte Uhrzeit, die schon erreicht ist)?"""
    return max((h for h in slots(cfg) if now.hour >= h), default=None)


def soften(sound, rate=RATE, cutoff=3500):
    """Dämpft hohe Töne (Tiefpass über FFT, passt zur nahtlosen Schleife, weil die ganze Schleife auf einmal gefiltert wird)."""
    spec = np.fft.rfft(sound)
    freq = np.fft.rfftfreq(len(sound), 1 / rate)
    spec *= 1 / (1 + (freq / cutoff) ** 4)
    return np.fft.irfft(spec, len(sound))


def plan(uploads, length="auto", today=None, n=0, count=7, hours=(17,), cap=None):
    """Vorschau der nächsten Videos (ohne neue Aufrufe): Liste von {day, hour, idea, title, scene, minutes}."""
    today = today or _dt.date.today()
    ups, out, d = list(uploads), [], 0
    while len(out) < count:
        day = (today + _dt.timedelta(days=d)).isoformat()
        for hr in hours:
            if len(out) >= count:
                break
            idea, minutes = choose(ups, length, today, n + len(out), cap)
            out.append({"day": day, "hour": hr, "idea": idea, "scene": IDEA[idea]["scene"],
                        "scene_name": SCENES[IDEA[idea]["scene"]], "title": IDEA[idea]["title"], "minutes": minutes})
            ups.append({"idea": idea, "scene": IDEA[idea]["scene"], "minutes": minutes, "at": day})
        d += 1
    return out


KEYWORDS = {   # Suchbegriffe je Szene (das, was Leute bei YouTube eintippen)
    "regenzimmer": ["rain sounds", "rain sounds for sleeping", "rain on window", "rain on window sounds", "cozy rain",
                    "rainy night ambience", "cozy room ambience", "heavy rain sounds", "rain ambience"],
    "kamin": ["fireplace sounds", "crackling fireplace", "fireplace ambience", "cozy fireplace", "fireplace for sleeping",
              "crackling fire sounds", "fireplace 4k", "cozy winter ambience", "fire sounds for sleep"],
    "cafe": ["coffee shop ambience", "cafe ambience", "coffee shop sounds", "rainy cafe ambience", "cozy coffee shop",
             "cafe sounds for studying", "night cafe ambience", "coffee shop background noise", "cafe rain sounds"],
    "bibliothek": ["library ambience", "fantasy library ambience", "magic library", "cozy library", "library sounds for studying",
                   "old library ambience", "reading ambience", "candle library ambience", "study ambience"],
    "lagerfeuer": ["campfire sounds", "campfire ambience", "crackling campfire", "forest night sounds", "campfire for sleeping",
                   "night forest ambience", "campfire under the stars", "crickets and campfire", "nature sounds for sleep"],
}
HASHTAGS = {"regenzimmer": "#rainsounds", "kamin": "#fireplace", "cafe": "#coffeeshopambience",
            "bibliothek": "#libraryambience", "lagerfeuer": "#campfire"}
GENERAL = ["sleep sounds", "relaxing sounds", "study ambience", "cozy ambience", "ambience", "white noise",
           "sounds for sleeping", "deep sleep", "stress relief", "focus", "no music"]


def story_meta(story, idea_id, minutes, n=0):
    """Titel, Beschreibung und Tags für eine Einschlaf-Geschichte (Englisch). Die Szene gibt Klang und Suchbegriffe."""
    import sleepstory
    i = IDEA[idea_id]
    hrs = hours_en(minutes)
    title = f"{story['title']} 🌙 Sleep Story with {i['sounds']} | {hrs}"
    if len(title) > 100:
        title = f"{story['title']} 🌙 Sleep Story | {hrs}"
    kw = KEYWORDS[i["scene"]]
    desc = (f"{story['title']}: a calm, slow story to fall asleep to, read in a soft voice over {i['sounds'].lower()}.\n\n"
            f"{story.get('about', 'An invented story.')}\n\n"
            f"What you hear: a quiet narrator, then {i['layers']} that keep playing after the story ends ({hrs.lower()} in total).\n\n"
            "Good for:\n· falling asleep\n· winding down after a long day\n· quiet evenings\n\n"
            f"{sleepstory.DISCLOSURE} Every picture and every sound in this video was made by Quiet Corner. "
            "A new story every day. Subscribe if you want to come back.\n\n"
            f"{HASHTAGS[i['scene']]} #sleepstory #bedtimestory")
    tags, total = [], 0
    extra = ["sleep story", "bedtime story for adults", "story to fall asleep to", "calm narration", "sleep story for adults",
             "relaxing story", story["title"].lower()]
    for t in extra + kw + GENERAL:
        if t not in tags and total + len(t) + 3 <= 480:
            tags.append(t)
            total += len(t) + 3
    return {"title": title, "description": desc, "tags": tags, "thumb_text": story.get("thumb") or i["thumb"]}


def meta(idea_id, minutes, n=0, title_style="klassisch"):
    """Titel, Beschreibung und Tags (Englisch) für das lange Video, so aufgebaut wie bei den großen Ambience-Kanälen:
    Bild + Emoji, dann der Suchbegriff mit Zweck, am Ende die Dauer („Rainy Night Café ☕ Coffee Shop Ambience … | 8 Hours“)."""
    i = IDEA[idea_id]
    hrs = hours_en(minutes)
    title = ""
    for k in range(len(USES)):
        use = USES[(n + k) % len(USES)]
        if title_style == "dauer":
            title = f"{hrs} of {i['sounds']} {i['emoji']} {i['title']} | {use.replace('for ', '', 1)}"
        elif title_style == "suche":
            title = f"{i['sounds']} {use} | {i['title']} {i['emoji']} | {hrs}"
        else:
            title = f"{i['title']} {i['emoji']} {i['sounds']} {use} | {hrs}"
        if len(title) <= 100:
            break
    if len(title) > 100:
        title = f"{i['title']} {i['emoji']} {i['sounds']} | {hrs}"
    kw = KEYWORDS[i["scene"]]
    desc = (f"{i['sounds']} for sleeping, studying and relaxing: {hrs.lower()} in a cozy, quiet place. {i['text']}\n\n"
            f"What you hear: {i['layers']}. No talking, no music, no sudden loud sounds, so it is safe to fall asleep to.\n\n"
            "Good for:\n· falling asleep and deep sleep\n· studying, reading and focus\n· calming down after a long day\n\n"
            "Every picture and every sound in this video was drawn and made by Quiet Corner. "
            "New cozy ambience every day. Subscribe if you want to come back.\n\n"
            f"{HASHTAGS[i['scene']]} #sleepsounds #cozyambience")
    tags, total = [], 0
    for t in kw + [f"{kw[0]} {hrs.lower()}", f"{hrs.lower()} {kw[0]}", i["title"].lower()] + GENERAL:
        if t not in tags and total + len(t) + 3 <= 480:   # YouTube erlaubt ca. 500 Zeichen für alle Tags zusammen
            tags.append(t)
            total += len(t) + 3
    return {"title": title, "description": desc, "tags": tags, "thumb_text": i["thumb"]}


def teaser_meta(idea_id, minutes, video_id):
    """Titel und Beschreibung für den Teaser-Short, verweist auf das lange Video."""
    i = IDEA[idea_id]
    return {"title": f"{i['title']} {i['emoji']}",
            "description": f"{i['text']}\n\nFull {hours_en(minutes).lower()} version: https://youtu.be/{video_id}\n\n"
                           "Drawn and made by Quiet Corner.",
            "tags": meta(idea_id, minutes)["tags"][:8]}


# ---------- Bauen ----------
def _page(folder, opt, wide=True, over=None):
    cartoon.stage({"scenes": [], "words": [], "dur": LOOP_S, "wide": wide}, folder)
    font = os.path.join(HERE, "fonts", "DMSerifDisplay-Regular.ttf")
    with open(font, "rb") as src, open(os.path.join(folder, "fonts", "DMSerifDisplay-Regular.ttf"), "wb") as dst:
        dst.write(src.read())
    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as f:
        f.write(PAGE % ("true" if wide else "false", LOOP_S, json.dumps(opt), json.dumps(over)))


def _render(opt, mp4, wide=True, over=None, start=0.0):
    with tempfile.TemporaryDirectory(prefix="quiet-") as tmp:
        _page(tmp, opt, wide, over)
        pw, browser, page = cartoon.open_page(tmp, wide=wide)
        page.evaluate("document.fonts.load('88px Serif')")
        try:
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                                   "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-tune", "animation",
                                   "-profile:v", "high", "-g", str(FPS * 2), "-pix_fmt", "yuv420p", "-an", mp4],
                                  stdin=subprocess.PIPE)
            total = page.evaluate("window.TOTAL_FRAMES")
            for jpg in cartoon.frames(page, [start + k / FPS for k in range(total)] if start else None):
                ff.stdin.write(jpg)
            ff.stdin.close()
            if ff.wait() != 0:
                raise RuntimeError("ffmpeg konnte das Bild nicht erstellen")
        finally:
            browser.close()
            pw.stop()


def _wav(path, sound):
    pcm = (np.clip(sound, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(pcm.tobytes())


def _opt(i):
    return {"scene": i["scene"], "weather": i["weather"]}


def thumbnail(idea_id, minutes, loop_mp4, path, text=None, style="links"):
    """Thumbnail 1280x720: Bild aus der Schleife, links dunkler, 2 bis 3 Wörter in ruhiger Schrift, darunter die Dauer."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    i = IDEA[idea_id]
    still = path + ".still.jpg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "22.9" if i["weather"] == "gewitter" else "7",
                    "-i", loop_mp4, "-frames:v", "1", still], check=True)
    img = Image.open(still).convert("RGB").resize((1280, 720), Image.LANCZOS)
    os.remove(still)
    shade = Image.new("L", (1280, 720))
    sd = ImageDraw.Draw(shade)
    if style == "mitte":
        for x in range(1280):
            sd.line([(x, 0), (x, 720)], fill=int(150 * (1 - min(1, abs(x - 640) / 640) ** 0.6)))
    else:
        for x in range(1280):
            sd.line([(x, 0), (x, 720)], fill=int(170 * max(0, 1 - x / 760) ** 1.5))
    img = Image.composite(Image.new("RGB", img.size, (12, 9, 8)), img, shade)
    f1 = ImageFont.truetype(os.path.join(HERE, "fonts", "DMSerifDisplay-Regular.ttf"), 124)
    f2 = ImageFont.truetype(os.path.join(HERE, "fonts", "InterDisplay-SemiBold.otf"), 40)
    text = text or i["thumb"]
    words = text.split()
    lines = [" ".join(words[:2]), " ".join(words[2:])] if len(words) > 2 else ([words[0], " ".join(words[1:])] if len(words) == 2 and len(text) > 11 else [text])
    lines = [x for x in lines if x]
    y0 = 360 - len(lines) * 70
    centered = style == "mitte"
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    d0 = ImageDraw.Draw(img)

    def tx(ln, font):
        return (1280 - d0.textlength(ln, font=font)) / 2 if centered else 84

    for k, ln in enumerate(lines):
        gd.text((tx(ln, f1), y0 + k * 132 + 6), ln, font=f1, fill=(0, 0, 0, 210))
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    img.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(img)
    for k, ln in enumerate(lines):
        d.text((tx(ln, f1) - (4 if not centered else 0), y0 + k * 132), ln, font=f1, fill=(248, 240, 228))
    pill = f"{minutes // 60} HOURS" if minutes >= 120 else "1 HOUR"
    py = y0 + len(lines) * 132 + 28
    w = d.textlength(pill, font=f2)
    px = (1280 - (w + 44)) / 2 if centered else 80
    d.rounded_rectangle((px, py, px + w + 44, py + 64), radius=32, fill=(232, 199, 140))
    d.text((px + 22, py + 9), pill, font=f2, fill=(40, 28, 20))
    img.save(path, "JPEG", quality=90)


def build(idea_id, minutes, out_dir, seed=1, teaser=True, story=None, styles=None):
    """Fertiges Video (mp4), Thumbnail (jpg), Teaser-Short (mp4) und Text (json). Gibt die Pfade zurück.

    story (aus sleepstory.stories()): Erzählstimme liest die Geschichte, die Szene läuft leise darunter und danach weiter.
    Die Länge richtet sich dann nach der Geschichte (out["minutes"]), `minutes` ist nur der Mindestwert."""
    if idea_id not in IDEA:
        raise ValueError(f"Unbekannte Idee {idea_id}, erlaubt: {', '.join(IDEA)}")
    i = IDEA[idea_id]
    os.makedirs(out_dir, exist_ok=True)
    name = f"quiet-{idea_id}-{minutes}min"
    mp4 = os.path.join(out_dir, name + ".mp4")
    out = {"video": mp4, "minutes": minutes}
    styles = {**STYLE_DEFAULT, **(styles or {})}
    sound = audio.soundscape(i["recipe"], LOOP_S, RATE, seed, loop=True) * 0.5
    if styles["sound"] == "weich":
        sound = soften(sound)
    with tempfile.TemporaryDirectory(prefix="quiet-out-") as tmp:
        loop_mp4, loop_wav = os.path.join(tmp, "loop.mp4"), os.path.join(tmp, "loop.wav")
        _render(_opt(i), loop_mp4)
        _wav(loop_wav, sound)
        if story:
            import sleepstory
            narr = os.path.join(tmp, "story.wav")
            secs = sleepstory.narrate(story["text"], narr, RATE)
            minutes = sleepstory.total_minutes(secs, 60)
            out["minutes"], out["story"] = minutes, story["id"]
            name = f"quiet-{idea_id}-{story['id']}"
            mp4 = out["video"] = os.path.join(out_dir, name + ".mp4")
        out["thumb"] = os.path.join(out_dir, name + ".jpg")
        thumbnail(idea_id, minutes, loop_mp4, out["thumb"], text=(story or {}).get("thumb"), style=styles["thumb_style"])
        if story:
            sleepstory.mux(loop_mp4, loop_wav, narr, minutes, mp4, RATE)
        else:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", loop_mp4,
                            "-stream_loop", "-1", "-i", loop_wav, "-t", str(minutes * 60), "-map", "0:v", "-map", "1:a",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", str(RATE), "-movflags", "+faststart", mp4],
                           check=True)
        if teaser:
            t_mp4, t_wav = os.path.join(tmp, "teaser.mp4"), os.path.join(tmp, "teaser.wav")
            over = {"dur": TEASER_S, "title": story["title"] if story else i["title"],
                    "sub": "a sleep story on the channel" if story else f"{hours_en(minutes).lower()} on the channel"}
            _render(_opt(i), t_mp4, wide=False, over=over, start=5.0)
            n = TEASER_S * RATE
            s = np.concatenate([sound, sound])[5 * RATE:5 * RATE + n].copy()
            fade = RATE
            s[:fade] *= np.linspace(0, 1, fade)
            s[-fade:] *= np.linspace(1, 0, fade)
            _wav(t_wav, s)
            out["teaser"] = os.path.join(out_dir, name + "-short.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", t_mp4, "-i", t_wav, "-map", "0:v", "-map", "1:a",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
                            out["teaser"]], check=True)
    out["info"] = os.path.join(out_dir, name + ".json")
    with open(out["info"], "w", encoding="utf-8") as f:
        json.dump(story_meta(story, idea_id, minutes, seed) if story else meta(idea_id, minutes, seed, styles["title_style"]), f, ensure_ascii=False, indent=2)
    return out


# ---------- Branding (Banner, Profilbild) ----------
BRAND_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>@font-face{font-family:Serif;src:url(fonts/DMSerifDisplay-Regular.ttf)}@font-face{font-family:Poppins;font-weight:700;src:url(fonts/Poppins-Bold.ttf)}body{margin:0}</style></head><body>
<script>const PLAN={wide:true}; const LOOP=60;</script>
<script src="lib.js"></script><script src="ambient.js"></script><script src="quiet.js"></script>
<script src="brand.js"></script><script>window.READY = true;</script></body></html>"""

BRAND_VARIANTS = {"A": "Regen-Fenster mit Pflanzen (dunkel, gemütlich)",
                  "B": "Kamin-Ecke mit Pflanzen (warm)",
                  "C": "Grüne Pflanzen-Ranken (hell, salbeigrün)"}


def watermark(path, size=600):
    """Wasserzeichen für YouTube (transparentes PNG, quadratisch): ein cremefarbenes Blatt mit Stiel in einem dünnen Ring."""
    import math
    from PIL import Image, ImageDraw
    k = 4  # Supersampling gegen Zacken
    S = size * k
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cream = (255, 246, 228, 255)
    cx = cy = S / 2
    d.ellipse([S * .06, S * .06, S * .94, S * .94], outline=cream, width=int(S * .025))
    # Herzblatt (Monstera-Form), Spitze nach unten
    pts = []
    for i in range(361):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * S * .021, cy - S * .03 - y * S * .021))
    d.polygon(pts, fill=cream)
    # Blattadern als transparente Linien
    for a in (-.9, -.45, 0, .45, .9):
        x2, y2 = cx + a * S * .2, cy - S * .12 - abs(a) * S * .02
        d.line([(cx, cy + S * .22), (x2, y2)], fill=(0, 0, 0, 0), width=int(S * .014))
    d.line([(cx, cy + S * .3), (cx, cy + S * .38)], fill=cream, width=int(S * .03))
    img = img.resize((size, size), Image.LANCZOS)
    img.save(path, "PNG")
    return path


def branding(out_dir):
    """Banner (2560x1440) und Profilbild (800x800) in drei Varianten, dazu die Kanalbeschreibung. Gibt Pfade zurück."""
    import base64
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    with tempfile.TemporaryDirectory(prefix="quiet-brand-") as tmp:
        _page(tmp, {"scene": "regenzimmer"})
        with open(os.path.join(tmp, "index.html"), "w", encoding="utf-8") as f:
            f.write(BRAND_PAGE)
        pw, browser, page = cartoon.open_page(tmp, wide=True)
        try:
            page.evaluate("async () => { await document.fonts.load('80px Serif'); await document.fonts.load('700 30px Poppins'); }")
            for v in BRAND_VARIANTS:
                for kind, size in (("banner", (2560, 1440)), ("profil", (800, 800))):
                    data = page.evaluate("([v, k, w, h]) => brandImage(v, k, w, h)", [v, kind, *size])
                    p = os.path.join(out_dir, f"quiet-corner-{kind}-{v}.{'jpg' if kind == 'banner' else 'png'}")
                    with open(p, "wb") as f:
                        f.write(base64.b64decode(data.split(",", 1)[1]))
                    out[f"{kind}-{v}"] = p
        finally:
            browser.close()
            pw.stop()
    out["wasserzeichen"] = watermark(os.path.join(out_dir, "quiet-corner-wasserzeichen.png"))
    p = os.path.join(out_dir, "quiet-corner-kanaltext.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"Kanalname: {CHANNEL}\n\nBeschreibung:\n{CHANNEL_DESCRIPTION}\n\nStichwörter: {CHANNEL_KEYWORDS}\n")
    out["text"] = p
    return out


if __name__ == "__main__":
    if sys.argv[1] == "branding":
        print(branding(sys.argv[2]))
    else:
        print(build(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
