"""Grafiken zu einem Satz: Zeitstrahl, Vergleich, Liste, Anteil und großes Wort.

Im Skript steht dafür bei einem Segment ein Feld "visual", zum Beispiel:
  {"type": "zeitstrahl", "punkte": [[1862, "Nähmaschinen"], [1886, "Fahrräder"], [1899, "Autos"]]}
  {"type": "vergleich", "a": ["Ferrari", 14000], "b": ["VW", 9000000], "einheit": "Autos pro Jahr"}
  {"type": "liste", "punkte": ["Fahrräder", "Motorräder", "Autos"]}
  {"type": "anteil", "teil": 1, "von": 5, "text": "des Süßwassers"}
  {"type": "wort", "text": "Verloren"}
Die Grafik baut sich über die Dauer des Satzes auf. Fehlerhafte Angaben werden ignoriert (dann Emoji).
"""
import math

from PIL import Image, ImageDraw

from motion import clamp01, ease_out_back, ease_out_cubic, fmt_number, font, paste_center, scaled, word_sprite

BOX_W, BOX_H = 940, 600
WHITE = (255, 255, 255)


def _fit(d, text, path, size, max_w, min_size=26):
    while size > min_size and d.textlength(text, font=font(path, size)) > max_w:
        size -= 2
    return font(path, size)


def _wrap(d, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if cur and d.textlength(test, font=fnt) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines[:2]


def _panel(d, k=1.0):
    d.rounded_rectangle((10, 10, BOX_W - 10, BOX_H - 10), radius=44, fill=(8, 10, 20, int(170 * k)),
                        outline=(255, 255, 255, int(40 * k)), width=3)


class Visual:
    def __init__(self, spec, accent, fonts):
        self.spec, self.accent = spec, accent
        self.bold, self.semi = fonts

    def draw(self, frame, t, start, end, cx, cy, scale=1.0):
        since = t - start
        dur = max(1.0, end - start)
        layer = Image.new("RGBA", (BOX_W, BOX_H), (0, 0, 0, 0))
        self.paint(layer, ImageDraw.Draw(layer), since, dur, t)
        pop = ease_out_back(clamp01(since / 0.35))
        paste_center(frame, scaled(layer, max(0.05, pop * scale)), cx, cy)


class Zeitstrahl(Visual):
    def __init__(self, spec, accent, fonts):
        super().__init__(spec, accent, fonts)
        self.points = [(str(p[0]), str(p[1])) for p in spec["punkte"]][:4]
        if len(self.points) < 2:
            raise ValueError("Zeitstrahl braucht mindestens zwei Punkte")

    def paint(self, layer, d, since, dur, t):
        _panel(d)
        n = len(self.points)
        x0, x1, y = 160, BOX_W - 160, BOX_H / 2 + 10
        # Linie wächst von links nach rechts
        grow = ease_out_cubic(clamp01(since / (dur * 0.75)))
        d.rounded_rectangle((x0, y - 6, x1, y + 6), radius=6, fill=(255, 255, 255, 60))
        d.rounded_rectangle((x0, y - 6, x0 + (x1 - x0) * grow, y + 6), radius=6, fill=self.accent)
        for i, (year, label) in enumerate(self.points):
            x = x0 + (x1 - x0) * i / (n - 1)
            appear = (dur * 0.75) * i / (n - 1)
            k = clamp01((since - appear) / 0.3)
            if k <= 0:
                continue
            r = 22 * ease_out_back(k)
            d.ellipse((x - r - 8, y - r - 8, x + r + 8, y + r + 8), fill=self.accent + (70,))
            d.ellipse((x - r, y - r, x + r, y + r), fill=WHITE)
            yf = _fit(d, year, self.bold, 76, (x1 - x0) / max(1, n - 1) + 40)
            d.text((x, y - 50 - 20 * (1 - k)), year, font=yf, anchor="ms", fill=self.accent)
            slot = min((x1 - x0) / max(1, n - 1) + 20, 2 * min(x, BOX_W - x) - 40)
            lf = font(self.semi, 40 if n > 3 else 46)
            lines = _wrap(d, label, lf, slot)
            for j, line in enumerate(lines):
                lfit = _fit(d, line, self.semi, lf.size, slot, 24)
                d.text((x, y + 60 + j * 50), line, font=lfit, anchor="mt", fill=WHITE)


class Vergleich(Visual):
    def __init__(self, spec, accent, fonts):
        super().__init__(spec, accent, fonts)
        self.items = [(str(spec["a"][0]), float(spec["a"][1])), (str(spec["b"][0]), float(spec["b"][1]))]
        if min(v for _, v in self.items) < 0 or max(v for _, v in self.items) <= 0:
            raise ValueError("Vergleich braucht positive Zahlen")
        self.unit = str(spec.get("einheit", ""))

    def paint(self, layer, d, since, dur, t):
        _panel(d)
        top, bottom = 230, BOX_H - 100
        vmax = max(v for _, v in self.items)
        colors = [(255, 255, 255, 200), self.accent]
        for i, (label, v) in enumerate(self.items):
            cx = BOX_W / 2 + (-210 if i == 0 else 210)
            appear = 0.2 if i == 0 else dur * 0.45
            k = ease_out_cubic(clamp01((since - appear) / 0.9))
            h = max(10, (bottom - top) * v / vmax) * k
            d.rounded_rectangle((cx - 120, bottom - h, cx + 120, bottom), radius=22, fill=colors[i])
            if k > 0:
                txt = fmt_number(v * k, 1 if v < 10 and v != int(v) else 0)
                nf = _fit(d, txt, self.bold, 92, 360)
                d.text((cx, bottom - h - 18), txt, font=nf, anchor="ms", fill=WHITE, stroke_width=6,
                       stroke_fill=(8, 10, 20))
            lf = _fit(d, label, self.semi, 50, 360)
            d.text((cx, bottom + 26), label, font=lf, anchor="mt", fill=WHITE)
        if self.unit:
            uf = _fit(d, self.unit.upper(), self.semi, 42, BOX_W - 120)
            d.text((BOX_W / 2, 50), self.unit.upper(), font=uf, anchor="mt", fill=self.accent)


class Liste(Visual):
    def __init__(self, spec, accent, fonts):
        super().__init__(spec, accent, fonts)
        self.items = [str(x) for x in spec["punkte"]][:4]
        if not self.items:
            raise ValueError("leere Liste")

    def paint(self, layer, d, since, dur, t):
        n = len(self.items)
        row_h = 120
        y0 = BOX_H / 2 - (n - 1) * row_h / 2
        for i, item in enumerate(self.items):
            appear = (dur * 0.7) * i / max(1, n - 1) if n > 1 else 0
            k = clamp01((since - appear) / 0.35)
            if k <= 0:
                continue
            e = ease_out_cubic(k)
            y = y0 + i * row_h
            x = 60 - 400 * (1 - e)
            d.rounded_rectangle((x, y - 48, x + BOX_W - 120, y + 48), radius=48, fill=(8, 10, 20, 190),
                                outline=self.accent + (int(200 * e),), width=4)
            d.ellipse((x + 10, y - 38, x + 86, y + 38), fill=self.accent)
            d.text((x + 48, y), str(i + 1), font=font(self.bold, 46), anchor="mm", fill=(14, 14, 22))
            tf = _fit(d, item, self.bold, 54, BOX_W - 280)
            d.text((x + 116, y), item, font=tf, anchor="lm", fill=WHITE)


class Anteil(Visual):
    def __init__(self, spec, accent, fonts):
        super().__init__(spec, accent, fonts)
        self.part, self.whole = int(spec["teil"]), int(spec["von"])
        if not (0 < self.part <= self.whole <= 100):
            raise ValueError("Anteil muss zwischen 1 und 100 liegen")
        self.text = str(spec.get("text", ""))

    def paint(self, layer, d, since, dur, t):
        _panel(d)
        n = self.whole
        cols = n if n <= 5 else (5 if n <= 10 else 10)
        rows = math.ceil(n / cols)
        cell = min(150 if n <= 10 else 46, (BOX_W - 140) / cols)
        r = cell * 0.38
        gx = BOX_W / 2 - (cols - 1) * cell / 2
        gy = 70 + r + (330 - rows * cell) / 2
        fill_k = clamp01((since - 0.4) / (dur * 0.5))
        lit = round(self.part * ease_out_cubic(fill_k))
        for i in range(n):
            x, y = gx + (i % cols) * cell, gy + (i // cols) * cell
            appear = 0.4 * i / n
            k = ease_out_back(clamp01((since - appear) / 0.25))
            rr = r * k
            on = i < lit
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=self.accent if on else (255, 255, 255, 55))
        label = f"{self.part} VON {self.whole}"
        d.text((BOX_W / 2, BOX_H - 150), label, font=_fit(d, label, self.bold, 76, BOX_W - 100), anchor="mm",
               fill=WHITE, stroke_width=6, stroke_fill=(8, 10, 20))
        if self.text:
            d.text((BOX_W / 2, BOX_H - 80), self.text.upper(),
                   font=_fit(d, self.text.upper(), self.semi, 40, BOX_W - 100), anchor="mm", fill=self.accent)


class Wort(Visual):
    def __init__(self, spec, accent, fonts):
        super().__init__(spec, accent, fonts)
        self.text = str(spec["text"]).upper()[:16]
        if not self.text.strip():
            raise ValueError("leeres Wort")
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        f = _fit(probe, self.text, self.bold, 210, BOX_W - 80, 60)
        self.letters = []
        x = BOX_W / 2 - probe.textlength(self.text, font=f) / 2
        for ch in self.text:
            w = probe.textlength(ch, font=f)
            if ch.strip():
                self.letters.append((x + w / 2, word_sprite(ch, f, accent)))
            x += w

    def paint(self, layer, d, since, dur, t):
        n = len(self.letters)
        for i, (x, spr) in enumerate(self.letters):
            k = clamp01((since - 0.05 * i) / 0.3)
            if k <= 0:
                continue
            s = ease_out_back(k)
            wobble = 6 * math.sin(t * 4 + i * 0.7)
            y = BOX_H / 2 - 180 * (1 - ease_out_cubic(k)) + wobble
            paste_center(layer, scaled(spr, max(0.05, s)), x, y)
        # Unterstrich wächst unter dem Wort
        k = ease_out_cubic(clamp01((since - 0.05 * n) / 0.4))
        if k > 0:
            half = (BOX_W - 160) / 2 * k
            d.rounded_rectangle((BOX_W / 2 - half, BOX_H / 2 + 120, BOX_W / 2 + half, BOX_H / 2 + 136), radius=8,
                                fill=WHITE)

    def draw(self, frame, t, start, end, cx, cy, scale=1.0):
        # ohne Hineinspringen des ganzen Kastens: die Buchstaben fallen einzeln
        layer = Image.new("RGBA", (BOX_W, BOX_H), (0, 0, 0, 0))
        self.paint(layer, ImageDraw.Draw(layer), t - start, max(1.0, end - start), t)
        paste_center(frame, scaled(layer, scale) if scale != 1 else layer, cx, cy)


KINDS = {"zeitstrahl": Zeitstrahl, "vergleich": Vergleich, "liste": Liste, "anteil": Anteil, "wort": Wort}


def build(spec, accent, fonts):
    """Grafik aus dem Skript-Feld "visual", oder None wenn es fehlt oder fehlerhaft ist."""
    if not isinstance(spec, dict):
        return None
    kind = KINDS.get(str(spec.get("type", "")).lower())
    if not kind:
        return None
    try:
        return kind(spec, accent, fonts)
    except (KeyError, TypeError, ValueError, IndexError):
        return None
