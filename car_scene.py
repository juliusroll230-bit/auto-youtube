"""Animierter Hintergrund: Sportwagen fährt nachts durch die Stadt (Ansicht von hinten).

Alles wird selbst gezeichnet, es braucht also keine fremden Videos oder Lizenzen.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
HORIZON = 1060
CX = W // 2


def _scale(y):
    """Perspektive: 0 am Horizont, 1 am unteren Bildrand."""
    return (y - HORIZON) / (H - HORIZON)


# Himmel je Satz: (oben, unten, Dunst). Bei jedem neuen Satz wechselt die Tageszeit.
SKIES = [
    ((8, 10, 30), (48, 28, 80), (255, 140, 80)),      # Nacht
    ((36, 14, 58), (236, 108, 70), (255, 170, 90)),   # Sonnenuntergang
    ((16, 4, 40), (120, 30, 150), (255, 60, 190)),    # Neon
    ((8, 26, 64), (58, 118, 186), (140, 200, 255)),   # Blaue Stunde
    ((28, 28, 60), (222, 156, 88), (255, 210, 140)),  # Morgengold
]


def _sky_and_city(seed, sky=SKIES[0]):
    rnd = random.Random(seed)
    top, bottom, haze_col = sky
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(HORIZON):
        k = y / HORIZON
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)))
    # Skyline mit beleuchteten Fenstern
    x = -20
    while x < W:
        bw = rnd.randint(70, 170)
        bh = rnd.randint(140, 520)
        top = HORIZON - bh
        shade = rnd.randint(14, 30)
        d.rectangle((x, top, x + bw, HORIZON), fill=(shade, shade + 4, shade + 16))
        for wy in range(top + 14, HORIZON - 10, 22):
            for wx in range(x + 10, x + bw - 12, 18):
                if rnd.random() < 0.38:
                    warm = rnd.random() < 0.7
                    col = (255, 205, 120) if warm else (170, 210, 255)
                    d.rectangle((wx, wy, wx + 8, wy + 11), fill=tuple(int(c * rnd.uniform(0.45, 0.9)) for c in col))
        x += bw + rnd.randint(-10, 8)
    # Dunst über dem Horizont
    haze = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(haze).rectangle((0, HORIZON - 140, W, HORIZON + 20), fill=haze_col + (55,))
    img = img.convert("RGBA")
    img.alpha_composite(haze.filter(ImageFilter.GaussianBlur(60)))
    # Straße
    d = ImageDraw.Draw(img)
    d.rectangle((0, HORIZON, W, H), fill=(12, 12, 18))
    d.polygon([(CX - 6, HORIZON), (CX + 6, HORIZON), (W + 700, H), (-700, H)], fill=(28, 28, 36))
    # Randlinien
    for side in (-1, 1):
        d.line([(CX + side * 5, HORIZON), (CX + side * 1150, H)], fill=(200, 200, 210), width=8)
    return img


def _car_sprite(color):
    """Sportwagen von hinten, doppelt so groß gezeichnet und verkleinert für glatte Kanten."""
    s = 2
    cw, ch = 760 * s, 420 * s
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, g, b = color
    dark = (int(r * 0.35), int(g * 0.35), int(b * 0.35))
    # Reifen
    for wx in (95, 545):
        d.rounded_rectangle((wx * s, 300 * s, (wx + 120) * s, 410 * s), radius=24 * s, fill=(10, 10, 12))
    # Karosserie
    d.polygon([(40 * s, 330 * s), (20 * s, 250 * s), (70 * s, 170 * s), (690 * s, 170 * s),
               (740 * s, 250 * s), (720 * s, 330 * s)], fill=color)
    d.rounded_rectangle((30 * s, 240 * s, 730 * s, 345 * s), radius=40 * s, fill=color)
    # Dach und Heckscheibe
    d.polygon([(150 * s, 175 * s), (230 * s, 70 * s), (530 * s, 70 * s), (610 * s, 175 * s)], fill=dark)
    d.polygon([(185 * s, 168 * s), (250 * s, 88 * s), (510 * s, 88 * s), (575 * s, 168 * s)], fill=(20, 24, 34))
    # Glanzlicht
    d.line([(90 * s, 190 * s), (670 * s, 190 * s)], fill=tuple(min(255, c + 80) for c in color), width=5 * s)
    # Diffusor und Auspuff
    d.rounded_rectangle((150 * s, 300 * s, 610 * s, 350 * s), radius=14 * s, fill=(18, 18, 22))
    for ex in (300, 420):
        d.ellipse((ex * s, 312 * s, (ex + 40) * s, 340 * s), fill=(70, 70, 76))
    # Nummernschild (leer)
    d.rounded_rectangle((300 * s, 255 * s, 460 * s, 290 * s), radius=5 * s, fill=(225, 225, 230))
    # Rücklicht-Leiste
    d.rounded_rectangle((60 * s, 205 * s, 700 * s, 225 * s), radius=10 * s, fill=(255, 40, 50))
    img = img.resize((cw // s, ch // s), Image.LANCZOS)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((40, 195, 720, 235), radius=20, fill=(255, 30, 40, 200))
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(img)
    return out


def _glow_dot(radius, color):
    size = radius * 4
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((radius, radius, size - radius, size - radius), fill=color)
    return img.filter(ImageFilter.GaussianBlur(radius * 0.6))


class CarScene:
    def __init__(self, car_color=(200, 20, 30), seed=7, skies=1):
        self.bases = [_sky_and_city(seed, SKIES[(seed + k) % len(SKIES)]).convert("RGBA") for k in range(skies)]
        self.base = self.bases[0]
        car = _car_sprite(car_color)
        self.car = car.resize((int(car.width * 1.25), int(car.height * 1.25)), Image.LANCZOS)
        self.lamp = _glow_dot(40, (255, 180, 90, 230))
        self.reflection = _glow_dot(60, (255, 40, 50, 110)).resize((620, 140))
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        for y in range(0, 900, 4):  # oben dunkler, damit Text gut lesbar ist
            sd.rectangle((0, y, W, y + 4), fill=(0, 0, 0, int(150 * (1 - y / 900))))
        self.shade = shade

    def frame(self, t, timings=None, pause=0.0, speed=1.0):
        travel = t * 26 * speed
        img = self.base.copy()
        if timings:
            # Himmel blendet bei jedem Satz zur nächsten Tageszeit über, das Auto gibt kurz Gas
            i = next((k for k, (s, e) in enumerate(timings) if t < e + pause), len(timings) - 1)
            i = min(i, len(self.bases) - 1)
            since = t - timings[i][0]
            fade = min(1.0, max(0.0, since / 0.8))
            img = Image.blend(self.bases[i - 1], self.bases[i], fade) if i > 0 and fade < 1 else self.bases[i].copy()
            for s, _ in timings[1:]:
                if t > s:
                    travel += 14 * (1 - math.exp(-(t - s) * 3))
        d = ImageDraw.Draw(img)
        # Mittelstreifen, die auf die Kamera zukommen
        for i in range(14):
            z = 1 + ((i * 4.0 - travel) % 56)
            y1 = HORIZON + (H - HORIZON) * 2.2 / z
            y2 = HORIZON + (H - HORIZON) * 2.2 / (z + 1.6)
            if y2 > H:
                continue
            w1 = max(2, 18 * _scale(min(y1, H)))
            w2 = max(1, 18 * _scale(y2))
            d.polygon([(CX - w2, y2), (CX + w2, y2), (CX + w1, min(y1, H)), (CX - w1, min(y1, H))], fill=(235, 220, 160))
        # Straßenlaternen links und rechts
        for i in range(8):
            z = 1 + ((i * 7.0 - travel) % 56)
            y = HORIZON + (H - HORIZON) * 2.2 / z
            if y > H + 400:
                continue
            k = _scale(y)
            for side in (-1, 1):
                x = CX + side * 820 * k
                top = y - 1000 * k
                d.line([(x, y), (x, top)], fill=(40, 40, 50), width=max(1, int(22 * k)))
                arm = x - side * 200 * k
                d.line([(x, top), (arm, top)], fill=(40, 40, 50), width=max(1, int(16 * k)))
                size = max(6, int(130 * k))
                lamp = self.lamp.resize((size, size))
                img.alpha_composite(lamp, (int(arm - size / 2), int(top - size / 2))) if 0 <= arm - size / 2 and arm + size / 2 < W and top - size / 2 >= 0 else img.paste(lamp, (int(arm - size / 2), int(top - size / 2)), lamp)
        # Auto mit leichtem Federn
        bob = 3 * math.sin(t * 9) + 1.5 * math.sin(t * 23)
        sway = 10 * math.sin(t * 0.6)
        img.paste(self.reflection, (int(CX - 310 + sway), 1800), self.reflection)
        img.alpha_composite(self.car, (int(CX - self.car.width / 2 + sway), int(1370 + bob)))
        img.alpha_composite(self.shade)
        return img
