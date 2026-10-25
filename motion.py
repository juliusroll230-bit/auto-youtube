"""Animierte Bausteine über dem Hintergrund: Untertitel, Zahlen-Zähler und Emoji-Abzeichen.

- Untertitel: Jedes Wort fliegt herein, sobald es gesprochen wird. Das gesprochene Wort
  bekommt einen farbigen Kasten, Zahlen und Schlüsselwörter (im Skript mit *Sternchen*) sind farbig.
- Zahlen: Wird eine Zahl gesprochen, erscheint ein Zähler, der hochzählt, mit Ring und Einheit.
- Emoji: sitzt auf einem leuchtenden Kreis, springt herein und wird von kleinen Funken umkreist.
"""
import math
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = 1080


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def clamp01(x):
    return max(0.0, min(1.0, x))


def scaled(img, s):
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)


def paste_center(frame, img, cx, cy):
    frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


def dark_text_for(rgb):
    lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return (14, 14, 22) if lum > 140 else (255, 255, 255)


_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


# --- Untertitel ------------------------------------------------------------

def word_sprite(text, fnt, fill, box=None, underline=None):
    """Ein Wort als Bild mit Umrandung und Schatten, optional auf einem farbigen Kasten oder unterstrichen."""
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    l, t, r, b = probe.textbbox((0, 0), text, font=fnt, anchor="mm")
    pad = 40
    w, h = int(r - l) + 2 * pad, int(b - t) + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cx, cy = w / 2, h / 2
    d, ds = ImageDraw.Draw(img), ImageDraw.Draw(shadow)
    if box:
        bx = (cx - (r - l) / 2 - 20, cy - (b - t) / 2 - 16, cx + (r - l) / 2 + 20, cy + (b - t) / 2 + 16)
        ds.rounded_rectangle((bx[0] + 5, bx[1] + 8, bx[2] + 5, bx[3] + 8), radius=22, fill=(0, 0, 0, 150))
        d.rounded_rectangle(bx, radius=22, fill=box)
        d.text((cx, cy), text, font=fnt, anchor="mm", fill=fill)
    else:
        ds.text((cx + 6, cy + 8), text, font=fnt, anchor="mm", fill=(0, 0, 0, 150))
        d.text((cx, cy), text, font=fnt, anchor="mm", fill=fill, stroke_width=10, stroke_fill=(12, 12, 20))
        if underline:
            uy = cy + (b - t) / 2 + 14
            d.rounded_rectangle((cx - (r - l) / 2, uy, cx + (r - l) / 2, uy + 14), radius=7, fill=underline)
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    shadow.alpha_composite(img)
    return shadow


class Caption:
    """Ein Untertitel (bis zu 3 Wörter): Layout und Bilder werden einmal berechnet, pro Bild nur bewegt."""

    STYLES = ("kasten", "unterstrich", "pop")

    def __init__(self, words, accent, font_path, style="kasten"):
        """words: Liste von (text, start, ende, schluesselwort). style: wie das gesprochene Wort aussieht."""
        self.style = style
        self.words = words
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        up = [w[0].upper() for w in words]
        size = 112
        while size > 60:
            f, big = font(font_path, size), font(font_path, int(size * 1.1))
            space = probe.textlength(" ", font=f) * 1.5
            widths = [probe.textlength(u, font=big) + 30 for u in up]
            lines, cur, cur_w = [], [], 0.0
            for i, ww in enumerate(widths):
                if cur and cur_w + space + ww > W - 150:
                    lines.append(cur)
                    cur, cur_w = [], 0.0
                cur.append(i)
                cur_w += (space if len(cur) > 1 else 0) + ww
            lines.append(cur)
            # lieber drei Zeilen als winzige Schrift bei langen Wörtern
            if (len(lines) <= 2 or (size <= 88 and len(lines) <= 3)) and all(sum(widths[i] for i in ln) + space * (len(ln) - 1) <= W - 150 for ln in lines):
                break
            size -= 6
        f, big = font(font_path, size), font(font_path, int(size * 1.1))
        lh = size * 1.3
        self.pos = [None] * len(words)
        for row, ln in enumerate(lines):
            line_w = sum(widths[i] for i in ln) + space * (len(ln) - 1)
            x = W / 2 - line_w / 2
            y = (row - (len(lines) - 1) / 2) * lh
            for i in ln:
                self.pos[i] = (x + widths[i] / 2, y)
                x += widths[i] + space
        acc = accent
        self.normal, self.active = [], []
        for u, (_, _, _, key) in zip(up, words):
            colored = key or any(c.isdigit() for c in u)
            self.normal.append(word_sprite(u, big if key else f, acc if colored else (255, 255, 255)))
            if style == "unterstrich":
                self.active.append(word_sprite(u, big, acc, underline=acc))
            elif style == "pop":
                self.active.append(word_sprite(u, font(font_path, int(size * 1.18)), acc))
            else:
                self.active.append(word_sprite(u, big, dark_text_for(acc), box=acc))

    def draw(self, frame, t, cy):
        for i, (_, ws, we, _) in enumerate(self.words):
            since = t - ws
            if since < -0.02 and i > 0:  # noch nicht gesprochen: unsichtbar
                continue
            k = clamp01(since / 0.16) if i > 0 else clamp01((since + 0.02) / 0.14)
            s = 0.25 + 0.75 * ease_out_back(k)
            on = ws <= t < we
            spr = self.active[i] if on else self.normal[i]
            if on:
                s *= 1.0 + 0.05 * math.sin(clamp01(since / 0.2) * math.pi)
            dy = 60 * (1 - ease_out_cubic(k))
            if self.style == "pop" and on:
                dy -= 14 * math.sin(clamp01(since / 0.25) * math.pi)
            x, y = self.pos[i]
            paste_center(frame, scaled(spr, s), x, cy + y + dy)


# --- Zahlen-Zähler ---------------------------------------------------------

BIG_UNITS = {"MILLIONEN", "MILLION", "MILLIARDEN", "MILLIARDE", "TAUSEND", "BILLIONEN"}


def number_value(word):
    """'1.600' -> 1600, '16,5' -> 16.5, sonst None."""
    m = re.search(r"\d[\d.]*(,\d+)?", word)
    if not m:
        return None
    s = m.group(0).rstrip(".")
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def number_events(words):
    """Zahlen in einem Satz: [(zeit, wert, jahr?, einheit, vorher, nachher), ...]

    words: Liste von (text, start, ende) des ganzen Satzes. Die Einheit ist das folgende großgeschriebene Wort
    ("Meter", "Euro", "Millionen Jahre").
    """
    out = []
    for i, (w, ws, _) in enumerate(words):
        v = number_value(w)
        if v is None or v <= 2:  # "2 Inseln" lohnt keinen Zähler
            continue
        digits = re.search(r"\d[\d.,]*", w).group(0).rstrip(".,")
        unit = []
        for nxt, _, _ in words[i + 1:i + 3]:
            clean = re.sub(r"[^\wäöüÄÖÜß%€$]", "", nxt)
            if not clean or not (clean[0].isupper() or clean in "%€$"):
                break
            unit.append(clean.upper())
            if clean.upper() not in BIG_UNITS:
                break
        pre = re.match(r"[^\d]*", w).group(0)
        post = w[len(pre) + len(digits):].strip(".,!?:;")
        if post and post.isalpha():  # z.B. "16-mal" -> bleibt beim Wort
            unit.insert(0, post.upper())
            post = ""
        # Jahreszahl: vierstellig ohne Punkt und ohne Einheit dahinter ("1937 begann ...")
        year = not unit and re.fullmatch(r"\d{4}", digits) is not None and 1000 <= v <= 2100
        out.append((ws, v, year, "JAHR" if year else " ".join(unit), digits, post))
    return out


def fmt_number(v, decimals):
    if decimals:
        return f"{v:,.{decimals}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"{int(round(v)):,}".replace(",", ".")


class NumberCard:
    """Großer Zähler mit Ring: zählt beim Sprechen der Zahl hoch."""

    COUNT = 0.9   # Sekunden zum Hochzählen

    def __init__(self, accent, font_path, semi_path, scale=1.0):
        self.accent = accent
        self.font_path, self.semi_path = font_path, semi_path
        self.scale = scale
        r = int(250 * scale)
        self.r = r
        size = 2 * r + 160
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((80 - 20, 80 - 20, size - 60, size - 60), fill=accent + (90,))
        self.glow = glow.filter(ImageFilter.GaussianBlur(40))
        disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(disc).ellipse((80, 80, size - 80, size - 80), fill=(8, 10, 20, 185))
        self.disc = disc
        self.size = size
        self._text_cache = {}

    def _num_img(self, text):
        if text in self._text_cache:
            return self._text_cache[text]
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        size = int(170 * self.scale)
        while size > 40 and probe.textlength(text, font=font(self.font_path, size)) > self.r * 1.62:
            size -= 6
        img = word_sprite(text, font(self.font_path, size), (255, 255, 255))
        if len(self._text_cache) > 400:
            self._text_cache.clear()
        self._text_cache[text] = img
        return img

    def draw(self, frame, t, cx, cy, event, appear):
        ws, v, year, unit, digits, _ = event
        since = t - ws
        pop = ease_out_back(clamp01((t - appear) / 0.32))
        k = ease_out_cubic(clamp01(since / self.COUNT))
        decimals = len(digits.split(",")[1]) if "," in digits else 0
        start = v - 40 if year else 0
        shown = start + (v - start) * k
        text = str(int(round(shown))) if year else fmt_number(shown, decimals)

        size = self.size
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        pulse = 1.0 + 0.04 * math.sin(t * 4)
        layer.alpha_composite(scaled(self.glow, pulse), (int(size / 2 - self.glow.width * pulse / 2),) * 2)
        layer.alpha_composite(self.disc)
        d = ImageDraw.Draw(layer)
        box = (80, 80, size - 80, size - 80)
        d.ellipse(box, outline=(255, 255, 255, 50), width=int(18 * self.scale))
        if k > 0:
            d.arc(box, -90, -90 + 360 * k, fill=self.accent, width=int(18 * self.scale))
            # leuchtender Punkt an der Spitze des Rings
            a = math.radians(-90 + 360 * k)
            rr = (size - 160) / 2 - 9 * self.scale
            px, py = size / 2 + rr * math.cos(a), size / 2 + rr * math.sin(a)
            dot = 16 * self.scale
            d.ellipse((px - dot, py - dot, px + dot, py + dot), fill=(255, 255, 255))
        # kleine Striche rundherum wie bei einer Uhr, drehen sich langsam
        for i in range(24):
            a = math.radians(i * 15 + t * 20)
            r1, r2 = size / 2 - 50, size / 2 - 38
            d.line([(size / 2 + r1 * math.cos(a), size / 2 + r1 * math.sin(a)),
                    (size / 2 + r2 * math.cos(a), size / 2 + r2 * math.sin(a))], fill=self.accent + (150,), width=4)
        num = self._num_img(text)
        ny = size / 2 - (30 * self.scale if unit else 0)
        layer.alpha_composite(num, (int(size / 2 - num.width / 2), int(ny - num.height / 2)))
        if unit:
            uf = font(self.semi_path, int(54 * self.scale))
            while d.textlength(unit, font=uf) > self.r * 1.5 and uf.size > 24:
                uf = font(self.semi_path, uf.size - 4)
            d.text((size / 2, ny + num.height / 2 - 10 * self.scale), unit, font=uf, anchor="mt", fill=self.accent)
        paste_center(frame, scaled(layer, max(0.05, pop)), cx, cy)


# --- Emoji-Abzeichen -------------------------------------------------------

class EmojiBadge:
    """Emoji auf leuchtendem Kreis, mit kreisenden Funken."""

    def __init__(self, accent, size=400):
        self.accent = accent
        s = int(size * 1.5)
        glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((s * 0.18, s * 0.18, s * 0.82, s * 0.82), fill=accent + (110,))
        self.glow = glow.filter(ImageFilter.GaussianBlur(50))
        self.size = s

    def draw(self, frame, t, cx, cy, emoji_img, since, out=0.0):
        """since: Sekunden seit Satzanfang; out: 0..1 wie weit das Emoji schon verschwunden ist."""
        pop = ease_out_back(clamp01(since / 0.32)) * (1 - ease_out_cubic(clamp01(out)))
        if pop <= 0.02:
            return
        g = scaled(self.glow, pop * (1 + 0.06 * math.sin(t * 3)))
        paste_center(frame, g, cx, cy)
        # Funken, die um das Emoji kreisen
        d = ImageDraw.Draw(frame, "RGBA")
        for i in range(5):
            a = t * 1.6 + i * 2 * math.pi / 5
            rad = (250 + 20 * math.sin(t * 2 + i)) * pop
            px, py = cx + rad * math.cos(a), cy + rad * 0.55 * math.sin(a)
            r = (9 + 4 * math.sin(t * 5 + i)) * pop
            d.ellipse((px - r, py - r, px + r, py + r), fill=(255, 255, 255, 220))
        em = scaled(emoji_img, max(0.05, pop * (1 + 0.04 * math.sin(t * 5))))
        em = em.rotate(7 * math.sin(t * 2.6), resample=Image.BICUBIC, expand=True)
        paste_center(frame, em, cx, cy)
