"""Kanal-Design: Banner, Profilbild und Kanalbeschreibung, passend zum Stil der Videos.

  python3 branding.py "60 Sekunden Wissen" out/   speichert banner.png und profilbild.png
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(HERE, "fonts", "InterDisplay-Black.otf")
FONT_SEMI = os.path.join(HERE, "fonts", "InterDisplay-SemiBold.otf")
FONT_EMOJI = os.path.join(HERE, "fonts", "NotoColorEmoji.ttf")

BG_TOP, BG_BOTTOM = (24, 16, 64), (8, 8, 14)
ACCENT = (255, 209, 102)   # Gelb wie die hervorgehobenen Wörter in den Videos
RED = (240, 68, 68)
NICHES = [("🏎️", "Business"), ("🧠", "Psychologie"), ("🏛️", "Geschichte"), ("💸", "Geld"), ("🌍", "Geografie")]

# Erhöhen, wenn sich Banner oder Beschreibung ändern: dann setzt die App sie neu.
VERSION = 1


def description(channel_title, hours):
    times = ", ".join(str(h) for h in hours[:-1]) + (f" und {hours[-1]}" if len(hours) > 1 else str(hours[0]))
    return (
        f"{channel_title}: Jeden Tag Fakten, die du in unter einer Minute verstehst.\n\n"
        "🏎️ Business & Autos\n🧠 Psychologie\n🏛️ Geschichte\n💸 Geld & Finanzen\n🌍 Geografie\n\n"
        f"🕛 Neue Shorts täglich um {times} Uhr\n"
        "🔔 Abonnieren, damit du keinen Fakt verpasst!\n\n"
        "Die Videos entstehen mit KI-Stimme und eigenen Animationen."
    )


KEYWORDS = ('Wissen Fakten Shorts "unnützes Wissen" Psychologie Geschichte Geld Finanzen Business Autos '
            'Geografie Lernen Allgemeinwissen')


def _font(path, size):
    return ImageFont.truetype(path, size)


def _gradient(w, h):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        k = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(BG_TOP, BG_BOTTOM)))
    return img.convert("RGBA")


def _glow(img, xy, radius, color, alpha):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x, y = xy
    ImageDraw.Draw(layer).ellipse((x - radius, y - radius, x + radius, y + radius), fill=color + (alpha,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius * 0.45)))


def _emoji(ch, size):
    font = _font(FONT_EMOJI, 109)
    tile = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((90, 90), ch, font=font, embedded_color=True, anchor="mm")
    tile = tile.crop(tile.getbbox() or (0, 0, 180, 180))
    return tile.resize((size, int(size * tile.height / tile.width)), Image.LANCZOS)


def _timer_ring(d, cx, cy, r, width, frac):
    # Eigene Ebene, damit der blasse Teil wirklich durchscheinend ist
    img = d._image
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 45), width=width)
    ld.arc((cx - r, cy - r, cx + r, cy + r), start=-90, end=-90 + 360 * frac, fill=RED + (255,), width=width)
    img.alpha_composite(layer)


def _split_title(title):
    """'60 Sekunden Wissen' -> ('60', 'SEKUNDEN WISSEN'); sonst ganzer Name als Text."""
    parts = title.split(" ", 1)
    if parts[0].isdigit() and len(parts) > 1:
        return parts[0], parts[1].upper()
    return "", title.upper()


def profile_picture(title, size=800):
    img = _gradient(size, size)
    _glow(img, (size * 0.5, size * 0.42), size * 0.42, (120, 80, 255), 90)
    d = ImageDraw.Draw(img, "RGBA")
    num, words = _split_title(title)
    c = size / 2
    _timer_ring(d, c, c, size * 0.36, int(size * 0.045), 0.78)
    if num:
        f = _font(FONT_BOLD, int(size * 0.34))
        d.text((c, c - size * 0.03), num, font=f, anchor="mm", fill=(255, 255, 255))
        d.text((c, c + size * 0.17), "SEK", font=_font(FONT_SEMI, int(size * 0.075)), anchor="mm", fill=ACCENT)
    else:
        initials = "".join(w[0] for w in title.split()[:2]).upper()
        d.text((c, c), initials, font=_font(FONT_BOLD, int(size * 0.3)), anchor="mm", fill=(255, 255, 255))
    return img.convert("RGB")


def banner(title, hours):
    """2560x1440. Alles Wichtige steht im mittleren Bereich (1546x423), der auf jedem Gerät sichtbar ist."""
    w, h = 2560, 1440
    img = _gradient(w, h)
    for x, y, r, col, a in [(700, 560, 520, (120, 80, 255), 80), (1900, 900, 600, (255, 120, 80), 50),
                            (1280, 720, 700, (255, 209, 102), 25)]:
        _glow(img, (x, y), r, col, a)
    d = ImageDraw.Draw(img, "RGBA")
    # Schwebende Emojis außerhalb des Textbereichs (auf großen Bildschirmen sichtbar)
    spots = [(330, 470, 210, -10), (2230, 520, 220, 12), (520, 1040, 180, 8), (2050, 1000, 190, -8), (1280, 1180, 150, 0)]
    for (ch, _), (x, y, s, rot) in zip(NICHES, spots):
        em = _emoji(ch, s).rotate(rot, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(em, (int(x - em.width / 2), int(y - em.height / 2)))
    # Sicherer Bereich: Name, Timer und Themen
    cx, cy = w // 2, h // 2
    num, words = _split_title(title)
    left = cx - 700
    _timer_ring(d, left + 120, cy - 20, 105, 18, 0.78)
    if num:
        d.text((left + 120, cy - 28), num, font=_font(FONT_BOLD, 110), anchor="mm", fill=(255, 255, 255))
        d.text((left + 120, cy + 42), "SEK", font=_font(FONT_SEMI, 26), anchor="mm", fill=ACCENT)
    tx = left + 270
    name = words if num else title.upper()
    size = 132
    while _font(FONT_BOLD, size).getlength(name) > 1130 and size > 60:
        size -= 4
    d.text((tx, cy - 70), name, font=_font(FONT_BOLD, size), anchor="lm", fill=(255, 255, 255),
           stroke_width=4, stroke_fill=(10, 10, 20))
    sub = "  ·  ".join(n for _, n in NICHES)
    d.text((tx + 4, cy + 30), sub.upper(), font=_font(FONT_SEMI, 40), anchor="lm", fill=ACCENT)
    times = " · ".join(f"{h_} Uhr" for h_ in hours)
    d.text((tx + 4, cy + 95), f"Täglich neue Shorts: {times}", font=_font(FONT_SEMI, 36), anchor="lm",
           fill=(255, 255, 255, 200))
    return img.convert("RGB")


def render_all(title, hours, out_dir):
    """Speichert banner.jpg (für YouTube, unter 6 MB) und profilbild.png."""
    os.makedirs(out_dir, exist_ok=True)
    b, p = os.path.join(out_dir, "banner.jpg"), os.path.join(out_dir, "profilbild.png")
    banner(title, hours).save(b, "JPEG", quality=92)
    profile_picture(title).save(p, optimize=True)
    return b, p


if __name__ == "__main__":
    print(render_all(sys.argv[1], [12, 17, 20], sys.argv[2]))
