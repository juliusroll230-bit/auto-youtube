"""Eigene Thumbnails: großes Motiv, kurzer Text (höchstens 4 Wörter), starke Kontraste.

Bisher zeigte YouTube bei langen Videos irgendein Bild aus dem Video. Jetzt baut die App pro Video zwei Varianten
und setzt eine davon beim Upload per API (thumbnails.set):

- Variante A „Wort + Satz“: Figur rechts, links das Thema in Riesenschrift und darunter eine Neugier-Zeile, roter Pfeil.
- Variante B „Satz im Kasten“: Figur links, rechts eine Frage oder Behauptung im gelben Kasten.

Lange Videos: 1280x720 (16:9). Shorts: 1080x1920 (Hochformat, YouTube zeigt es im Kanal und in der Suche).
Der Text kommt aus dem Skript (Feld "thumb_text": ["GROSS | kleine Zeile", "Satz für B"], je höchstens 4 Wörter),
sonst baut die App ihn aus dem Titel. Keine fremden Logos, nur eigene Figuren, Emojis und Schrift.

  python3 thumbnail.py seed/0112-erklaert-kuehlschrank-lang.json ausgabe/   speichert -A.jpg und -B.jpg
"""
import io
import json
import os
import re
import sys
import tempfile

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_BLACK = os.path.join(HERE, "fonts", "InterDisplay-Black.otf")
FONT_EMOJI = os.path.join(HERE, "fonts", "NotoColorEmoji.ttf")

VARIANTS = ("A: Wort + Satz", "B: Satz im Kasten")   # Werte für das Lern-Merkmal „Thumbnail“
LONG_SIZE, SHORT_SIZE = (1280, 720), (1080, 1920)
YELLOW, RED, INK = (255, 214, 10), (235, 40, 40), (12, 12, 18)
MAX_BYTES = 2 * 1024 * 1024 - 50_000   # YouTube nimmt höchstens 2 MB

# Wörter, die im Titel groß geschrieben sind, aber kein Thema sind
STOP = {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "was", "wie", "warum", "wer", "wo", "wann",
        "wieso", "weshalb", "und", "oder", "aber", "teil", "wahrheit", "geheimnis", "rätsel", "frage", "antwort",
        "dinge", "ding", "menschen", "mensch", "leute", "welt", "jahr", "jahre", "tag", "tage", "minute", "minuten",
        "sekunden", "video", "fakten", "fakt", "niemand", "keiner", "alle", "alles", "nichts", "du", "dein", "deine",
        "ich", "wir", "sie", "er", "es", "ist", "sind", "hat", "kann", "wird", "wenn", "dann", "heute", "hier",
        "dieser", "diese", "dieses", "jeder", "jede", "überraschende", "unglaubliche", "wirklich", "wahre",
        "erklärt", "shorts"}

# Neugier-Zeilen je Video-Typ: (Zeile unter dem Thema bei A, Satz im Kasten bei B)
HOOKS = {
    "mystery": ("BIS HEUTE UNGELÖST", "NIEMAND KANN ES ERKLÄREN"),
    "horror": ("GEH NICHT REIN", "DAS WAR KEIN ZUFALL"),
    "was_passiert": ("UND DANN?", "DAS PASSIERT WIRKLICH"),
    "warum": ("DARUM!", "KEINER WEISS DAS"),
    "erklaeren": ("SO GEHT'S WIRKLICH", "DAS WUSSTEST DU NICHT"),
    "normal": ("KEINER WEISS DAS", "STIMMT DAS WIRKLICH?"),
}


# --- Text ---------------------------------------------------------------------

def _kind(spec):
    niche = str(spec.get("niche", "")).lower()
    title = str(spec.get("title", "")).lower()
    if niche == "horror":
        return "horror"
    if niche == "mystery" or title.startswith("das ") and "niemand" in title:
        return "mystery"
    if niche.startswith("erkl"):
        if title.startswith("was passiert"):
            return "was_passiert"
        if title.startswith(("warum", "wieso", "weshalb")):
            return "warum"
        return "erklaeren"
    return "normal"


def subject(spec):
    """Das Thema als ein Wort: das erste großgeschriebene Hauptwort im Titel, das kein Füllwort ist."""
    title = re.sub(r"[^\wÄÖÜäöüß\- ]", " ", str(spec.get("title", "")))
    words = title.split()
    for i, w in enumerate(words):
        if not w[:1].isupper() or w.lower() in STOP or len(w) < 4 or w.isdigit():
            continue
        if i == 0 and w.lower() in STOP:
            continue
        return w
    return ""


def _clean(text, max_words=4):
    words = re.sub(r"[–—]", " ", str(text)).split()
    return " ".join(words[:max_words]).upper()


def texts(spec):
    """Text für Variante A (Thema, Zeile) und Variante B (Satz). Höchstens 4 Wörter je Variante."""
    own = spec.get("thumb_text") or []
    if isinstance(own, str):
        own = [own]
    hook_a, hook_b = HOOKS[_kind(spec)]
    subj = subject(spec)
    if own:
        # eigener Text: "GROSS | kleine Zeile" oder alles groß
        big, _, line = str(own[0]).partition("|")
        a_big = _clean(big)
        a_line = _clean(line, max(0, 4 - len(a_big.split())))
        b = _clean(own[1]) if len(own) > 1 else _clean(own[0])
    else:
        a_big, a_line = (subj.upper(), hook_a) if subj else (hook_a, "")
        if len((a_big + " " + a_line).split()) > 4:
            a_line = " ".join(a_line.split()[:4 - len(a_big.split())])
        b = hook_b
    return {"A": (a_big, a_line), "B": b}


def emoji_for(spec):
    """Das Emoji am Ende des Titels, sonst das häufigste Szenen-Objekt im Video, sonst eins nach Typ."""
    last = str(spec.get("title", "")).strip().split()[-1:] or [""]
    if last[0] and not any(ch.isalnum() for ch in last[0]) and any(ord(ch) > 0x2100 for ch in last[0]):
        return last[0]
    count = {}
    for seg in spec.get("segments", []):
        sc = seg.get("szene") or {}
        for e in (sc.get("objekt"), seg.get("emoji"), (sc.get("links") or {}).get("objekt")):
            if e and len(e) <= 4:
                count[e] = count.get(e, 0) + 1
    if count:
        return max(count, key=count.get)
    return {"horror": "👻", "mystery": "❓", "was_passiert": "😱", "warum": "🤔"}.get(_kind(spec), "💡")


# --- Bild aus dem Video (die Figur in Pose, ohne Untertitel) --------------------

def pose_scene(spec):
    """Eine Szene mit großer Figur und deutlichem Gefühl, ohne Schild und schwebendes Emoji."""
    kind = _kind(spec)
    segs = spec.get("segments", [])
    good = [s.get("szene") or {} for s in segs[:max(3, len(segs) // 3)]]
    good = [s for s in good if s.get("typ") in ("figur", "zwei", "horror", "monster")] or \
           [s for s in (seg.get("szene") or {} for seg in segs) if s.get("typ") in ("figur", "zwei", "horror", "monster")]
    sc = dict(good[0]) if good else {"typ": "figur", "ort": (segs[0].get("szene") or {}).get("ort", "stadt") if segs else "stadt"}
    scary = kind in ("horror", "mystery")
    sc["gefuehl"] = "angst" if scary else "staunen"
    sc["aktion"] = "zittert" if sc.get("typ") == "monster" else "schockiert"
    for k in ("objekt", "text", "tafel", "punkte"):
        sc.pop(k, None)
    if isinstance(sc.get("figur"), dict):
        sc["figur"] = {k: v for k, v in sc["figur"].items() if k != "name"}
    return sc


def scene_image(spec, at=1.6):
    """Hochformat-Bild (1080x1920) der Pose-Szene. None, wenn Chromium fehlt oder das Skript kein Cartoon ist."""
    if spec.get("stil") != "cartoon":
        try:
            import make_short
            timings, total = make_short.estimated_timings(spec)
            return make_short.Scene(spec, timings, total).frame(0.9).convert("RGB")
        except Exception:  # noqa: BLE001
            return None
    try:
        import cartoon
        sc = pose_scene(spec)
        if "figur" not in sc:   # Hauptfigur ohne Namensschild
            sc["figur"] = {k: v for k, v in (spec.get("figur") or {"farbe": "rot"}).items() if k != "name"}
        sc.update(start=0.0, end=4.0)
        p = {"scenes": [sc], "words": [], "dur": 4.0, "stimmung": cartoon.mood(spec), "wide": False}
        with tempfile.TemporaryDirectory(prefix="thumb-") as tmp:
            cartoon.stage(p, tmp)
            pw, browser, page = cartoon.open_page(tmp, False)
            try:
                jpg = next(cartoon.frames(page, [at]))
            finally:
                browser.close()
                pw.stop()
        return Image.open(io.BytesIO(jpg)).convert("RGB")
    except Exception as e:  # noqa: BLE001  ohne Bild aus dem Video geht es mit Farbverlauf weiter
        print(f"Thumbnail: Szene nicht gerendert ({e})", flush=True)
        return None


# --- Zeichnen -----------------------------------------------------------------

def _hex(c, fallback):
    try:
        c = str(c).lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, TypeError):
        return fallback


def _font(size):
    return ImageFont.truetype(FONT_BLACK, size)


def _emoji(ch, size):
    tile = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((100, 100), ch, font=ImageFont.truetype(FONT_EMOJI, 109), embedded_color=True, anchor="mm")
    box = tile.getbbox()
    if not box:
        return None
    tile = tile.crop(box)
    return tile.resize((size, int(size * tile.height / tile.width)), Image.LANCZOS)


def _shadowed(img, layer, xy, blur=14, offset=(8, 10), alpha=170):
    """Legt eine Ebene mit weichem Schatten auf das Bild (hebt Figur, Emoji und Text vom Hintergrund ab)."""
    a = layer.split()[3].point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(a)
    pad = blur * 3
    canvas = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(sh, (pad, pad))
    canvas = canvas.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(canvas, (xy[0] - pad + offset[0], xy[1] - pad + offset[1]))
    img.alpha_composite(layer, xy)


def _glow(img, center, radius, color, alpha):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x, y = center
    ImageDraw.Draw(layer).ellipse((x - radius, y - radius, x + radius, y + radius), fill=color + (alpha,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius * 0.5)))


def _wrap(text, max_w, start, max_lines=2, min_size=60):
    """Bricht den Text in höchstens max_lines Zeilen und wählt die größte Schrift, die passt."""
    words = text.split()
    best = None
    for size in range(start, min_size - 1, -4):
        f = _font(size)
        lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if f.getlength(t) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) <= max_lines and all(f.getlength(ln) <= max_w for ln in lines):
            return f, lines
        best = (f, lines)
    return best


def _text_layer(lines, font, fill, stroke, highlight=None, spacing=0.98, align="left"):
    """Text mit dicker dunkler Kontur. highlight: Index der Zeile, die gelb wird."""
    lh = int(font.size * spacing)
    w = int(max(font.getlength(ln) for ln in lines)) + 2 * stroke + 8
    h = lh * len(lines) + 2 * stroke + int(font.size * 0.25)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, ln in enumerate(lines):
        x = stroke + 4 if align == "left" else (w - font.getlength(ln)) / 2
        d.text((x, stroke + i * lh), ln, font=font, fill=YELLOW if i == highlight else fill,
               stroke_width=stroke, stroke_fill=INK)
    return layer


def _background(size, scene, colors, figure_side):
    w, h = size
    top, bottom = _hex(colors[0], (20, 24, 60)) if colors else (20, 24, 60), \
        _hex(colors[1], (60, 90, 200)) if len(colors) > 1 else (60, 90, 200)
    bg = Image.new("RGBA", size)
    d = ImageDraw.Draw(bg)
    for y in range(h):
        k = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(bottom, top)) + (255,))
    if scene is not None:
        # Szene (Ort mit Figur) groß und kräftiger, damit sie auch klein auf dem Handy wirkt
        sc = ImageEnhance.Color(scene).enhance(1.35)
        luma = ImageStat.Stat(sc.convert("L")).mean[0]
        if luma < 80:   # Horror-Szenen sind sehr dunkel: aufhellen, sonst sieht man klein nichts
            sc = ImageEnhance.Brightness(sc).enhance(min(2.2, 95 / max(luma, 1)))
        sc = ImageEnhance.Contrast(sc).enhance(1.12)
        if w > h:   # Querformat: Ausschnitt um die Figur (die steht im Hochformat mittig, ca. y 650 bis 1650)
            region = sc.crop((140, 380, 940, 1380)).resize((h * 800 // 1000, h), Image.LANCZOS)
            blur = sc.resize((w, int(w * 1920 / 1080)), Image.LANCZOS).crop((0, int(w * 1920 / 1080 * 0.32), w, int(w * 1920 / 1080 * 0.32) + h))
            blur = ImageEnhance.Brightness(blur.filter(ImageFilter.GaussianBlur(18))).enhance(0.55)
            bg.alpha_composite(blur.convert("RGBA"))
            x = w - region.width + 30 if figure_side == "right" else -30
            mask = Image.new("L", region.size, 255)
            md = ImageDraw.Draw(mask)
            fade = 170
            for i in range(fade):   # weicher Rand zur Textseite
                xx = i if figure_side == "right" else region.width - 1 - i
                md.line([(xx, 0), (xx, region.height)], fill=int(255 * i / fade))
            bg.paste(region.convert("RGBA"), (x, 0), mask)
        else:       # Hochformat: ganze Szene, etwas größer gezoomt
            z = 1.3   # Figur größer und etwas nach unten, oben ist Platz für den Text
            big = sc.resize((int(w * z), int(h * z)), Image.LANCZOS)
            bg.alpha_composite(big.convert("RGBA"), (-(big.width - w) // 2, min(0, -(big.height - h) // 2 + 300)))
    # Abdunkeln auf der Textseite, damit die Schrift knallt
    shade = Image.new("L", size, 0)
    sd = ImageDraw.Draw(shade)
    if w > h:
        for x in range(w):
            k = (1 - x / (w * 0.62)) if figure_side == "right" else (x - w * 0.38) / (w * 0.62)
            sd.line([(x, 0), (x, h)], fill=int(200 * max(0.0, min(1.0, k))))
    else:
        for y in range(h):
            k = 1 - y / (h * 0.5)
            sd.line([(0, y), (w, y)], fill=int(210 * max(0.0, min(1.0, k))))
    bg.paste(Image.new("RGBA", size, INK + (255,)), (0, 0), shade)
    # dunkler Rand rundum (Vignette)
    vig = Image.new("L", size, 0)
    ImageDraw.Draw(vig).rectangle((0, 0, w, h), outline=150, width=max(w, h) // 30)
    bg.paste(Image.new("RGBA", size, (0, 0, 0, 255)), (0, 0), vig.filter(ImageFilter.GaussianBlur(max(w, h) // 25)))
    return bg


def render(spec, variant="A", scene=None, size=None):
    """Baut ein Thumbnail (PIL-Bild, RGB). variant: "A" oder "B". scene: fertiges Szenenbild (spart Chromium)."""
    variant = str(variant)[:1].upper()
    long = spec.get("laenge") == "lang"
    w, h = size or (LONG_SIZE if long else SHORT_SIZE)
    txt = texts(spec)
    accent = _hex(spec.get("accent"), YELLOW)
    figure_side = "right" if variant == "A" else "left"
    img = _background((w, h), scene, spec.get("colors") or [], figure_side)
    em = _emoji(emoji_for(spec), int(h * (0.36 if w > h else 0.2)))

    if w > h:   # ---- Querformat 1280x720: Figur auf einer Seite, Text groß auf der anderen
        if variant == "A":
            big, line = txt["A"]
            text_w = int(w * 0.56)
            f_big, big_lines = _wrap(big, text_w, 200, 2, 80)
            layer = _text_layer(big_lines, f_big, (255, 255, 255), max(7, f_big.size // 13))
            parts = []
            if line:
                f_line, lines = _wrap(line, text_w, min(120, int(f_big.size * 0.8)), 2, 48)
                parts = [_text_layer(lines, f_line, YELLOW, max(6, f_line.size // 11))]
            total = layer.height + sum(p.height for p in parts)
            y = int(h * 0.60) - total // 2
            _shadowed(img, layer, (30, y))
            for p in parts:
                _shadowed(img, p, (34, y + layer.height - 8))
            if em:   # Emoji mit rotem Kreis oben in der Mitte, zwischen Text und Figur
                cx, cy, r = int(w * 0.50), int(h * 0.22), int(h * 0.17)
                _glow(img, (cx, cy), int(r * 1.5), accent, 110)
                em = em.resize((int(r * 1.55), int(r * 1.55 * em.height / em.width)), Image.LANCZOS)
                em = em.rotate(-8, resample=Image.BICUBIC, expand=True)
                _shadowed(img, em, (cx - em.width // 2, cy - em.height // 2))
                ring = Image.new("RGBA", (2 * r + 40, 2 * r + 40), (0, 0, 0, 0))
                rd = ImageDraw.Draw(ring)
                rd.ellipse((10, 10, ring.width - 10, ring.height - 10), outline=(255, 255, 255, 255), width=20)
                rd.ellipse((14, 14, ring.width - 14, ring.height - 14), outline=RED + (255,), width=12)
                _shadowed(img, ring, (cx - ring.width // 2, cy - ring.height // 2), blur=6, offset=(3, 4))
        else:
            f, lines = _wrap(txt["B"], int(w * 0.48), 140, 3, 56)
            layer = _text_layer(lines, f, INK, 0, align="left")
            pad = 26
            box = Image.new("RGBA", (layer.width + 2 * pad, layer.height + pad), (0, 0, 0, 0))
            ImageDraw.Draw(box).rounded_rectangle((0, 0, box.width - 1, box.height - 1), radius=22, fill=YELLOW + (255,),
                                                  outline=INK, width=6)
            box.alpha_composite(layer, (pad, pad // 2 + 4))
            box = box.rotate(-3, resample=Image.BICUBIC, expand=True)
            bx, by = w - box.width - 28, max(24, int(h * 0.42) - box.height // 2)
            _shadowed(img, box, (bx, by))
            if em:   # Emoji unten rechts, schräg unter dem Kasten
                em = em.resize((int(h * 0.30), int(h * 0.30 * em.height / em.width)), Image.LANCZOS)
                em = em.rotate(10, expand=True, resample=Image.BICUBIC)
                cx, cy = int(w * 0.86), min(h - em.height // 2 - 16, by + box.height + em.height // 2 - 10)
                _glow(img, (cx, cy), int(h * 0.2), accent, 110)
                _shadowed(img, em, (cx - em.width // 2, cy - em.height // 2))
    else:       # ---- Hochformat 1080x1920 (Shorts)
        if variant == "A":
            big, line = txt["A"]
            f_big, big_lines = _wrap(big, w - 100, 230, 2, 90)
            layer = _text_layer(big_lines, f_big, (255, 255, 255), max(8, f_big.size // 13), align="center")
            _shadowed(img, layer, (w // 2 - layer.width // 2, 170))
            if line:
                f, lines = _wrap(line, w - 140, 120, 2, 60)
                ll = _text_layer(lines, f, YELLOW, max(6, f.size // 12), align="center")
                _shadowed(img, ll, (w // 2 - ll.width // 2, 170 + layer.height))
            if em:
                _glow(img, (int(w * 0.80), int(h * 0.80)), int(w * 0.2), accent, 120)
                em = em.rotate(-10, expand=True, resample=Image.BICUBIC)
                _shadowed(img, em, (int(w * 0.80) - em.width // 2, int(h * 0.80) - em.height // 2))
        else:
            f, lines = _wrap(txt["B"], w - 200, 150, 3, 70)
            layer = _text_layer(lines, f, INK, 0, align="center")
            pad = 34
            box = Image.new("RGBA", (layer.width + 2 * pad, layer.height + pad), (0, 0, 0, 0))
            ImageDraw.Draw(box).rounded_rectangle((0, 0, box.width - 1, box.height - 1), radius=30, fill=YELLOW + (255,),
                                                  outline=INK, width=8)
            box.alpha_composite(layer, (pad, pad // 2 + 4))
            box = box.rotate(-3, resample=Image.BICUBIC, expand=True)
            _shadowed(img, box, (w // 2 - box.width // 2, 200))
            if em:
                _glow(img, (int(w * 0.20), int(h * 0.80)), int(w * 0.18), accent, 120)
                _shadowed(img, em, (int(w * 0.20) - em.width // 2, int(h * 0.80) - em.height // 2))
    return img.convert("RGB")


def save(img, path):
    """Speichert als JPEG unter 2 MB."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    q = 92
    while True:
        img.save(path, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(path) <= MAX_BYTES or q <= 60:
            return path
        q -= 8


def build(spec, out_dir, slug=None):
    """Beide Varianten speichern: {"A": pfad, "B": pfad}. Lange Videos 1280x720, Shorts 1080x1920."""
    scene = scene_image(spec)
    slug = slug or spec["slug"]
    return {v: save(render(spec, v, scene), os.path.join(out_dir, f"{slug}-{v}.jpg")) for v in ("A", "B")}


def variant_key(value):
    """'A: Wort + Satz' -> 'A'."""
    return str(value or "A")[:1].upper()


if __name__ == "__main__":
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    for s in data if isinstance(data, list) else [data]:
        print(build(s, sys.argv[2]))
