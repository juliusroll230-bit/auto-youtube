"""Bewegte Hintergründe passend zum Thema. Bei jedem neuen Satz ändert sich der Hintergrund.

Alles wird selbst gezeichnet, es braucht also keine fremden Bilder oder Videos:
- Psychologie: Netz aus Nervenzellen, das sich bei jedem Satz neu anordnet
- Geschichte: Bauwerke als Silhouette im Abendlicht (Tempel, Pyramiden, Burg, Kolosseum)
- Geld: Börsenkurs, der sich bei jedem Satz neu zeichnet, dazu fallende Münzen
- Geografie: Erde aus Punkten, die sich bei jedem Satz weiterdreht (zu genannten Ländern)
- Sonst: Farbverlauf mit Lichtflecken und Partikeln
Die Farben wechseln bei jedem Satz mit einer weichen Überblendung.
"""
import colorsys
import math
import os
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(HERE, "fonts", "InterDisplay-Black.otf")
FADE = 0.7          # Sekunden Überblendung zwischen zwei Sätzen
HUES = [0, 30, -24, 48, -40, 16, -54]   # Farbton-Verschiebung je Satz (Grad)


# --- Hilfen -------------------------------------------------------------------

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def shift(rgb, deg, light=1.0):
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    r, g, b = colorsys.hls_to_rgb((h + deg / 360) % 1, max(0, min(1, l * light)), s)
    return int(r * 255), int(g * 255), int(b * 255)


def palette(colors, i, spread=1.0):
    c1, c2 = (hex_rgb(c) for c in colors[:2])
    d = HUES[i % len(HUES)] * spread
    return shift(c1, d), shift(c2, d, 1.06 if i % 2 else 0.94)


def gradient(c1, c2, w=W, h=H):
    """Verlauf von oben nach unten mit dunklen Rändern."""
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    t = np.clip(y * 0.85 + x * 0.15, 0, 1)[..., None]
    img = np.array(c1, float) * (1 - t) + np.array(c2, float) * t
    v = 1 - 0.38 * np.clip(((x - 0.5) * 2) ** 2 * 0.6 + ((y - 0.5) * 2) ** 2 * 0.4, 0, 1)
    return Image.fromarray(np.clip(img * v[..., None], 0, 255).astype(np.uint8), "RGB")


def glow(radius, color, alpha=255, blur=0.5):
    size = int(radius * 4)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    c = size / 2
    ImageDraw.Draw(img).ellipse((c - radius, c - radius, c + radius, c + radius), fill=tuple(color) + (alpha,))
    return img.filter(ImageFilter.GaussianBlur(radius * blur))


def put(dst, sprite, cx, cy):
    """Sprite mittig auf (cx, cy) legen, auch wenn es über den Rand ragt."""
    dst.paste(sprite, (int(cx - sprite.width / 2), int(cy - sprite.height / 2)), sprite)


def mix(a, b, k):
    return tuple(int(x + (y - x) * k) for x, y in zip(a, b))


class Theme:
    def __init__(self, spec, timings, total, pause):
        self.spec, self.timings, self.total, self.pause = spec, timings, total, pause
        self.n = len(timings)
        self.seed = sum(map(ord, spec["slug"]))
        self.accent = hex_rgb(spec.get("accent") or "#ffd166")
        self.colors = spec.get("colors") or ["#1d1a39", "#5a3fc0"]
        self.texts = [s["text"].replace("*", "") for s in spec["segments"]]
        self.emojis = [s.get("emoji", "") for s in spec["segments"]]

    def seg(self, t):
        """(Satz, Sekunden seit Satzanfang, Fortschritt der Überblendung 0..1)"""
        i = next((k for k, (s, e) in enumerate(self.timings) if t < e + self.pause), self.n - 1)
        since = t - self.timings[i][0]
        return i, since, 1.0 if i == 0 else smooth(since / FADE)

    def backdrop(self, grads, t):
        i, _, k = self.seg(t)
        if k >= 1 or i == 0:
            return grads[i].copy()
        return Image.blend(grads[i - 1], grads[i], k)


# --- Psychologie: Nervenzellen ------------------------------------------------

class Neural(Theme):
    N, LINK = 46, 300

    def __init__(self, *a):
        super().__init__(*a)
        rng = np.random.default_rng(self.seed)
        self.grads = [gradient(*palette(self.colors, i)) for i in range(self.n)]
        self.layouts = [self._layout(rng) for _ in range(self.n)]
        self.freq = rng.uniform(0.25, 0.8, (self.N, 2))
        self.phase = rng.uniform(0, 6.28, (self.N, 2))
        self.size = rng.uniform(5, 10, self.N)
        self.line = mix((255, 255, 255), self.accent, 0.35)
        self.halo = glow(16, self.line, 110)
        self.spark = glow(12, self.accent, 255, 0.4)
        self.pulses = [(int(rng.integers(self.N)), rng.uniform(0.5, 1.0), rng.uniform(0, 1), j % 2)
                       for j in range(16)]

    def _layout(self, rng):
        cols, rows = 6, 9
        cells = rng.choice(cols * rows, self.N, replace=False)
        cw, ch = (W + 160) / cols, (H + 160) / rows
        x = (cells % cols + rng.uniform(0.15, 0.85, self.N)) * cw - 80
        y = (cells // cols + rng.uniform(0.15, 0.85, self.N)) * ch - 80
        return np.stack([x, y], 1)

    def frame(self, t):
        img = self.backdrop(self.grads, t)
        i, since, _ = self.seg(t)
        move = smooth(since / 1.1) if i > 0 else 1.0
        base = self.layouts[i - 1] + (self.layouts[i] - self.layouts[i - 1]) * move if i > 0 else self.layouts[0]
        p = base + 28 * np.sin(t * self.freq + self.phase)
        d = ImageDraw.Draw(img, "RGBA")
        dist = np.sqrt(((p[:, None, :] - p[None, :, :]) ** 2).sum(-1))
        a_idx, b_idx = np.triu_indices(self.N, 1)
        near = dist[a_idx, b_idx] < self.LINK
        for a, b in zip(a_idx[near], b_idx[near]):
            al = int(150 * (1 - dist[a, b] / self.LINK) ** 1.2)
            d.line([tuple(p[a]), tuple(p[b])], fill=self.line + (al,), width=3)
        # Welle bei jedem neuen Satz, Zellen leuchten auf, wenn sie vorbeizieht
        r = 1500 * (1 - (1 - min(1, since / 1.3)) ** 3)
        wave = max(0.0, 1 - since / 1.3)
        if wave > 0:
            d.ellipse((W / 2 - r, 620 - r, W / 2 + r, 620 + r), outline=self.accent + (int(110 * wave),), width=8)
        for k in range(self.N):
            x, y = p[k]
            boost = wave * max(0.0, 1 - abs(math.hypot(x - W / 2, y - 620) - r) / 110)
            put(img, self.halo, x, y)
            s = self.size[k] * (1 + boost)
            d.ellipse((x - s, y - s, x + s, y + s), fill=mix(self.line, self.accent, boost) + (255,))
        # Signale, die zwischen benachbarten Zellen wandern
        for a, speed, off, which in self.pulses:
            b = int(np.argsort(dist[a])[1 + which])
            f = (t * speed + off) % 1
            put(img, self.spark, *(p[a] + (p[b] - p[a]) * f))
        return img


# --- Geschichte: Bauwerke im Abendlicht ---------------------------------------

def _temple(d, h):
    for k, (x0, x1) in enumerate([(120, 960), (150, 930), (180, 900)]):
        d.rectangle((x0, h - 36 * (k + 1), x1, h - 36 * k), fill=255)
    for k in range(8):
        cx = 220 + 640 * k / 7
        d.rectangle((cx - 24, h - 430, cx + 24, h - 108), fill=255)
        d.rectangle((cx - 34, h - 452, cx + 34, h - 430), fill=255)
    d.rectangle((160, h - 520, 920, h - 452), fill=255)
    d.polygon([(140, h - 520), (940, h - 520), (540, h - 650)], fill=255)


def _pyramids(d, h):
    d.polygon([(120, h), (780, h), (450, h - 600)], fill=255)
    d.polygon([(620, h), (1040, h), (830, h - 400)], fill=255)
    d.polygon([(960, h), (1180, h), (1070, h - 210)], fill=255)
    # Palme
    pts = [(70 + 12 * math.sin(k / 6), h - k * 14) for k in range(26)]
    d.line(pts, fill=255, width=22)
    tx, ty = pts[-1]
    for ang in (-150, -110, -60, -20, 20):
        a = math.radians(ang)
        ex, ey = tx + 150 * math.cos(a), ty + 90 * math.sin(a) + 40
        d.polygon([(tx, ty), (ex, ey), (tx + 70 * math.cos(a), ty + 30 * math.sin(a) + 26)], fill=255)


def _castle(d, h):
    d.rectangle((210, h - 270, 870, h), fill=255)
    for x in range(210, 870, 60):
        d.rectangle((x, h - 300, x + 32, h - 270), fill=255)
    for x0 in (140, 790):
        d.rectangle((x0, h - 440, x0 + 150, h), fill=255)
        d.polygon([(x0 - 14, h - 440), (x0 + 164, h - 440), (x0 + 75, h - 560)], fill=255)
    d.rectangle((420, h - 520, 660, h), fill=255)
    for x in range(420, 660, 52):
        d.rectangle((x, h - 552, x + 30, h - 520), fill=255)
    d.line([(540, h - 552), (540, h - 660)], fill=255, width=6)
    d.polygon([(543, h - 660), (620, h - 638), (543, h - 616)], fill=255)
    d.rectangle((490, h - 150, 590, h), fill=0)
    d.ellipse((490, h - 200, 590, h - 100), fill=0)
    for x in (470, 586):
        d.rectangle((x, h - 420, x + 24, h - 370), fill=0)


def _colosseum(d, h):
    top = [(60, h - 470), (680, h - 470), (700, h - 410), (800, h - 410), (820, h - 340), (1020, h - 340)]
    d.polygon([(60, h)] + top + [(1020, h)], fill=255)
    for tier, (y0, y1) in enumerate([(h - 120, h - 12), (h - 240, h - 140), (h - 355, h - 258)]):
        for k in range(9):
            x = 90 + k * 104
            limit = 470 if x < 680 else 410 if x < 800 else 340
            if h - y0 > limit - 30:
                continue
            d.rectangle((x, y0 + 26, x + 60, y1), fill=0)
            d.ellipse((x, y0, x + 60, y0 + 52), fill=0)


MONUMENTS = {"temple": _temple, "pyramids": _pyramids, "castle": _castle, "colosseum": _colosseum}
MONUMENT_WORDS = [
    (r"\brom|römer|römisch|gladiator|kolosseum|cäsar|caesar", "colosseum"),
    (r"ägypt|pharao|pyramide|kleopatra|nil\b|mumie", "pyramids"),
    (r"könig|ritter|burg|mittelalter|napoleon|kaiser|sultan|palast|schloss|krieg", "castle"),
    (r"griech|athen|sparta|sokrates|platon|olymp|tempel|universität", "temple"),
]
MONUMENT_EMOJI = {"🏛️": "temple", "🎓": "temple", "📜": "temple", "👑": "castle", "🏰": "castle",
                  "⚔️": "castle", "🛡️": "castle", "🐫": "pyramids", "🏺": "pyramids", "🦁": "colosseum"}


class History(Theme):
    MH, GROUND = 720, 1780

    def __init__(self, *a):
        super().__init__(*a)
        rng = np.random.default_rng(self.seed)
        self.grads = [gradient(*palette(self.colors, i, 0.4)) for i in range(self.n)]
        names, last = [], None
        cycle = [m for m in MONUMENTS if True]
        rng.shuffle(cycle)
        for k, (text, emoji) in enumerate(zip(self.texts, self.emojis)):
            pick = next((m for pat, m in MONUMENT_WORDS if re.search(pat, text.lower())), None)
            pick = pick or MONUMENT_EMOJI.get(emoji)
            if not pick or pick == last:
                pick = next(m for m in cycle[k % 4:] + cycle if m != last)
            names.append(pick)
            last = pick
        dark = mix(hex_rgb(self.colors[0]), (0, 0, 0), 0.6)
        self.layers = {}
        for m in set(names):
            mask = Image.new("L", (W, self.MH), 0)
            MONUMENTS[m](ImageDraw.Draw(mask), self.MH)
            layer = Image.new("RGBA", mask.size, dark + (255,))
            layer.putalpha(mask)
            self.layers[m] = layer
        self.names = names
        # Hügel im Hintergrund (bewegen sich langsamer: Tiefe)
        hw = W * 3
        hill = Image.new("L", (hw, 420), 0)
        xs = np.arange(hw)
        top = 220 - 70 * np.sin(xs / 260) - 40 * np.sin(xs / 97 + 1)
        ImageDraw.Draw(hill).polygon([(0, 420)] + list(zip(xs.tolist(), top.tolist())) + [(hw, 420)], fill=255)
        self.hill = Image.new("RGBA", hill.size, mix(hex_rgb(self.colors[1]), (0, 0, 0), 0.55) + (200,))
        self.hill.putalpha(hill.point(lambda v: v * 200 // 255))
        self.sun = glow(170, (255, 196, 120), 255, 0.25)
        self.sun_halo = glow(320, (255, 170, 90), 90, 0.6)
        self.cloud = Image.new("RGBA", (620, 200), (0, 0, 0, 0))
        ImageDraw.Draw(self.cloud).ellipse((40, 60, 580, 140), fill=(255, 230, 200, 46))
        self.cloud = self.cloud.filter(ImageFilter.GaussianBlur(22))
        self.clouds = [(rng.uniform(0, W), rng.uniform(260, 1000), rng.uniform(8, 20)) for _ in range(4)]
        self.birds = [(rng.uniform(0, W), rng.uniform(380, 900), rng.uniform(40, 80), rng.uniform(0, 6)) for _ in range(5)]
        self.dust = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(10, 35), rng.uniform(2, 5), rng.uniform(0, 6))
                     for _ in range(36)]

    def frame(self, t):
        img = self.backdrop(self.grads, t)
        i, since, _ = self.seg(t)
        pan = smooth(since / 1.0) if i > 0 else 1.0
        put(img, self.sun_halo, W / 2, 1360 + 30 * t / self.total)
        put(img, self.sun, W / 2, 1360 + 30 * t / self.total)
        for x0, y, v in self.clouds:
            put(img, self.cloud, (x0 + v * t) % (W + 600) - 300, y)
        d = ImageDraw.Draw(img, "RGBA")
        dark = mix(hex_rgb(self.colors[0]), (0, 0, 0), 0.6)
        for x0, y0, v, ph in self.birds:
            x = (x0 + v * t) % (W + 200) - 100
            y = y0 + 12 * math.sin(t * 1.3 + ph)
            wing = 0.5 + 0.45 * math.sin(t * 9 + ph)
            d.line([(x - 22, y - 22 * wing), (x, y), (x + 22, y - 22 * wing)], fill=dark + (220,), width=4)
        hx = -((12 * t + 300 * (i - 1 + pan)) % (W * 2))
        img.paste(self.hill, (int(hx), self.GROUND - 420 + 40), self.hill)
        # Bauwerk: das alte gleitet links hinaus, das neue kommt von rechts (wie ein Kameraschwenk)
        drift = 10 * math.sin(t * 0.3)
        if i > 0 and pan < 1:
            old = self.layers[self.names[i - 1]]
            img.paste(old, (int(-pan * W + drift), self.GROUND - self.MH), old)
        cur = self.layers[self.names[i]]
        img.paste(cur, (int((1 - pan) * W + drift), self.GROUND - self.MH), cur)
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, self.GROUND, W, H), fill=dark + (255,))
        for x0, y0, v, r, ph in self.dust:
            y = (y0 - v * t) % H
            x = x0 + 18 * math.sin(t * 0.6 + ph)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 225, 180, 70))
        return img


# --- Geld: Börsenkurs und Münzen ----------------------------------------------

DOWN_WORDS = r"inflation|verlier|verlust|weniger wert|sinkt|sinken|fällt|fallen|schulden|minus|teurer|pleite|crash|kopfkissen"


def _coin(size):
    s = size * 3
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, s - 1, s - 1), fill=(196, 140, 34))
    d.ellipse((s * 0.07, s * 0.07, s * 0.93, s * 0.93), fill=(246, 196, 64))
    d.ellipse((s * 0.14, s * 0.14, s * 0.86, s * 0.86), outline=(206, 150, 40), width=max(2, s // 40))
    f = ImageFont.truetype(FONT_BOLD, int(s * 0.5))
    d.text((s / 2, s / 2), "€", font=f, anchor="mm", fill=(190, 132, 26))
    return img.resize((size, size), Image.LANCZOS)


class Money(Theme):
    def __init__(self, *a):
        super().__init__(*a)
        rng = np.random.default_rng(self.seed)
        self.grads = [gradient(*palette(self.colors, i, 0.7)) for i in range(self.n)]
        self.charts = []
        for k, text in enumerate(self.texts):
            down = bool(re.search(DOWN_WORDS, text.lower()))
            steps = rng.normal(-0.42 if down else 0.42, 1.0, 46)
            v = np.concatenate([[0], np.cumsum(steps)])
            v = (v - v.min()) / max(1e-6, v.max() - v.min())
            xs = np.linspace(40, W - 40, len(v))
            ys = 1640 - v * 620
            color = (255, 92, 92) if down else (92, 235, 150)
            self.charts.append((xs, ys, color))
        self.coins = []
        for j in range(14):
            near = j % 3 == 0
            size = int(rng.uniform(110, 150) if near else rng.uniform(50, 80))
            sprite = _coin(size)
            if not near:
                sprite.putalpha(sprite.getchannel("A").point(lambda v: v * 120 // 255))
            self.coins.append((sprite, rng.uniform(0, W), rng.uniform(0, H + 300),
                               rng.uniform(240, 360) if near else rng.uniform(110, 180), rng.uniform(1.5, 3.5),
                               rng.uniform(0, 6)))
        self.head = glow(18, (255, 255, 255), 255, 0.45)

    def _chart(self, img, k, frac, alpha):
        xs, ys, color = self.charts[k]
        n = max(2, int(len(xs) * frac))
        pts = list(zip(xs[:n].tolist(), ys[:n].tolist()))
        if frac < 1:
            # Letzten Punkt weich zwischen zwei Stützpunkten
            f = len(xs) * frac - int(len(xs) * frac)
            if n < len(xs):
                pts.append((xs[n - 1] + (xs[n] - xs[n - 1]) * f, ys[n - 1] + (ys[n] - ys[n - 1]) * f))
        d = ImageDraw.Draw(img, "RGBA")
        d.polygon(pts + [(pts[-1][0], 1760), (pts[0][0], 1760)], fill=color + (int(38 * alpha),))
        d.line(pts, fill=color + (int(60 * alpha),), width=26, joint="curve")
        d.line(pts, fill=color + (int(255 * alpha),), width=9, joint="curve")
        if alpha > 0.5:
            put(img, self.head, *pts[-1])

    def frame(self, t):
        img = self.backdrop(self.grads, t)
        i, since, k = self.seg(t)
        d = ImageDraw.Draw(img, "RGBA")
        off = (t * 50) % 120
        for x in np.arange(-off, W + 120, 120):
            d.line([(x, 0), (x, H)], fill=(255, 255, 255, 18), width=2)
        for y in range(40, H, 120):
            d.line([(0, y), (W, y)], fill=(255, 255, 255, 18), width=2)
        if i > 0 and k < 1:
            self._chart(img, i - 1, 1.0, 1 - k)
        self._chart(img, i, smooth(since / 2.4) if i > 0 else smooth(t / 2.4), 1.0)
        for sprite, x0, y0, v, flip, ph in self.coins:
            y = (y0 + v * t) % (H + 300) - 150
            x = x0 + 30 * math.sin(t * 0.7 + ph)
            w = max(3, int(sprite.width * abs(math.cos(t * flip + ph))))
            put(img, sprite.resize((w, sprite.height), Image.BILINEAR), x, y)
        return img


# --- Geografie: Erde aus Punkten ----------------------------------------------

PLACES = {  # Stichwort im Satz -> (Breite, Länge)
    "deutschland": (51, 10), "frankreich": (46, 2), "spanien": (40, -4), "italien": (42, 12), "europa": (50, 10),
    "england": (52, -1), "großbritannien": (54, -2), "norwegen": (61, 9), "schweden": (62, 15), "island": (65, -18),
    "russland": (60, 90), "sibirien": (62, 105), "baikal": (53, 108), "china": (35, 104), "japan": (36, 138),
    "indien": (22, 79), "türkei": (39, 35), "arabien": (24, 45), "ägypten": (26, 30), "sahara": (23, 12),
    "afrika": (5, 20), "südafrika": (-30, 25), "australien": (-25, 134), "neuseeland": (-41, 174),
    "kanada": (58, -100), "usa": (39, -98), "amerika": (39, -98), "mexiko": (23, -102), "brasilien": (-10, -52),
    "amazonas": (-4, -62), "argentinien": (-35, -65), "chile": (-33, -71), "grönland": (72, -40),
    "antarktis": (-75, 0), "pazifik": (0, -160), "atlantik": (20, -40), "himalaya": (28, 86), "everest": (28, 87),
}


def _land_points():
    land = np.array(Image.open(os.path.join(HERE, "assets", "land.png")).convert("L")) > 0
    n = 16000
    k = np.arange(n) + 0.5
    lat = np.degrees(np.arcsin(1 - 2 * k / n))
    lon = (np.degrees(np.pi * (1 + 5 ** 0.5) * k) % 360) - 180
    px = ((lon + 180) / 360 * land.shape[1]).astype(int) % land.shape[1]
    py = np.clip(((90 - lat) / 180 * land.shape[0]).astype(int), 0, land.shape[0] - 1)
    keep = land[py, px]
    return np.radians(lat[keep]), np.radians(lon[keep])


def _grid_points():
    lats, lons = [], []
    for la in range(-60, 61, 30):
        lo = np.arange(-180, 180, 0.8)
        lats.append(np.full_like(lo, la))
        lons.append(lo)
    for lo0 in range(-180, 180, 30):
        la = np.arange(-88, 88, 0.8)
        lats.append(la)
        lons.append(np.full_like(la, lo0))
    return np.radians(np.concatenate(lats)), np.radians(np.concatenate(lons))


class Globe(Theme):
    CX, CY, R = W // 2, 1330, 500

    def __init__(self, *a):
        super().__init__(*a)
        rng = np.random.default_rng(self.seed)
        self.grads = [gradient(*palette(self.colors, i, 0.5)) for i in range(self.n)]
        self.land = _land_points()
        self.grid = _grid_points()
        self.stars = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 3), rng.uniform(0, 6)) for _ in range(110)]
        self.targets, lon = [], float(rng.uniform(-180, 180))
        for text in self.texts:
            hit = next((v for key, v in PLACES.items() if key in text.lower()), None)
            if hit:
                self.targets.append((min(45, max(-35, hit[0])), hit[1], hit))
                lon = hit[1]
            else:
                lon = (lon + 80 + 180) % 360 - 180
                self.targets.append((15, lon, None))
        r = self.R
        ocean = Image.new("RGBA", (2 * r + 200, 2 * r + 200), (0, 0, 0, 0))
        od = ImageDraw.Draw(ocean)
        od.ellipse((100 - 26, 100 - 26, 100 + 2 * r + 26, 100 + 2 * r + 26), fill=self.accent + (70,))
        ocean = ocean.filter(ImageFilter.GaussianBlur(26))
        ImageDraw.Draw(ocean).ellipse((100, 100, 100 + 2 * r, 100 + 2 * r), fill=(6, 18, 40, 215))
        self.ocean = ocean
        self.land_rgb = np.array(mix(self.accent, (255, 255, 255), 0.35), float)

    def view(self, t):
        i, since, _ = self.seg(t)
        lat1, lon1, _ = self.targets[i]
        if i == 0:
            return lat1, lon1 + 3 * since
        lat0, lon0, _ = self.targets[i - 1]
        dur0 = self.timings[i][0] - self.timings[i - 1][0]
        lon0 += 3 * dur0
        dl = (lon1 - lon0 + 180) % 360 - 180
        k = smooth(since / 1.4)
        return lat0 + (lat1 - lat0) * k, lon0 + dl * k + 3 * max(0, since - 1.4) * k

    def project(self, lat, lon, vlat, vlon):
        la0, lo0 = math.radians(vlat), math.radians(vlon)
        x = np.cos(lat) * np.sin(lon - lo0)
        y = np.sin(lat)
        z = np.cos(lat) * np.cos(lon - lo0)
        y2 = y * math.cos(la0) - z * math.sin(la0)
        z2 = y * math.sin(la0) + z * math.cos(la0)
        return self.CX + self.R * x, self.CY - self.R * y2, z2

    def frame(self, t):
        img = self.backdrop(self.grads, t)
        d = ImageDraw.Draw(img, "RGBA")
        for x, y, r, ph in self.stars:
            a = int(90 + 90 * math.sin(t * 2 + ph))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, a))
        put(img, self.ocean, self.CX, self.CY)
        vlat, vlon = self.view(t)
        size = 2 * self.R + 8
        layer = np.zeros((size, size, 4), np.uint8)
        ox, oy = self.CX - size // 2, self.CY - size // 2
        gx, gy, gz = self.project(*self.grid, vlat, vlon)
        m = gz > 0
        layer[(gy[m] - oy).astype(int).clip(0, size - 1), (gx[m] - ox).astype(int).clip(0, size - 1)] = (150, 200, 255, 70)
        lx, ly, lz = self.project(*self.land, vlat, vlon)
        m = lz > 0.02
        xs, ys, zs = (lx[m] - ox).astype(int), (ly[m] - oy).astype(int), lz[m]
        col = np.clip(self.land_rgb[None, :] * (0.35 + 0.65 * zs[:, None]), 0, 255).astype(np.uint8)
        for dx in range(5):
            for dy in range(5):
                if (dx in (0, 4)) and (dy in (0, 4)):
                    continue
                layer[(ys + dy).clip(0, size - 1), (xs + dx).clip(0, size - 1), :3] = col
                layer[(ys + dy).clip(0, size - 1), (xs + dx).clip(0, size - 1), 3] = 235
        sprite = Image.fromarray(layer, "RGBA")
        img.paste(sprite, (ox, oy), sprite)
        # Markierung am genannten Ort
        i, since, _ = self.seg(t)
        hit = self.targets[i][2]
        if hit and since > 1.0:
            px, py, pz = self.project(np.radians([hit[0]]), np.radians([hit[1]]), vlat, vlon)
            if pz[0] > 0.1:
                d = ImageDraw.Draw(img, "RGBA")
                ring = (t * 1.2) % 1
                rr = 14 + 46 * ring
                d.ellipse((px[0] - rr, py[0] - rr, px[0] + rr, py[0] + rr), outline=(255, 80, 80, int(255 * (1 - ring))), width=6)
                d.ellipse((px[0] - 13, py[0] - 13, px[0] + 13, py[0] + 13), fill=(255, 70, 70, 255), outline=(255, 255, 255), width=4)
        return img


# --- Standard: Farbverlauf mit Lichtflecken -----------------------------------

class Default(Theme):
    def __init__(self, *a):
        super().__init__(*a)
        rng = np.random.default_rng(self.seed)
        self.grads = [gradient(*palette(self.colors, i)) for i in range(self.n)]
        c2 = hex_rgb(self.colors[1])
        self.blobs = [(glow(150, self.accent, 70, 0.6), 0.11, 0.0), (glow(200, (255, 255, 255), 40, 0.6), 0.07, 2.0),
                      (glow(120, c2, 120, 0.6), 0.15, 4.0)]
        self.particles = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(40, 140), rng.uniform(3, 9),
                           rng.uniform(0, 6.28), int(rng.uniform(50, 150))) for _ in range(26)]

    def frame(self, t):
        img = self.backdrop(self.grads, t)
        for blob, speed, phase in self.blobs:
            put(img, blob, W / 2 + 380 * math.sin(t * speed * 6 + phase), H / 2 + 700 * math.cos(t * speed * 4 + phase))
        d = ImageDraw.Draw(img, "RGBA")
        for x0, y0, speed, r, ph, a in self.particles:
            y = (y0 - speed * t) % (H + 40) - 20
            x = x0 + 24 * math.sin(t * 0.8 + ph)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, a))
        return img


def for_spec(spec, timings, total, pause):
    niche = spec.get("niche", "").lower()
    if "psych" in niche:
        cls = Neural
    elif "gesch" in niche:
        cls = History
    elif "geld" in niche or "finanz" in niche:
        cls = Money
    elif "geo" in niche:
        cls = Globe
    else:
        cls = Default
    return cls(spec, timings, total, pause)
