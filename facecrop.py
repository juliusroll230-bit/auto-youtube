"""Gesichts-Zuschnitt: Querformat-Videos so auf Hochkant schneiden, dass der Sprecher im Bild bleibt.

Ablauf: alle 0,5 Sekunden ein kleines Graubild, Gesichter mit dem mitgelieferten OpenCV-Erkenner suchen
(nur das größte zählt), die Mitte sanft nachführen und als ffmpeg-Ausdruck für x zurückgeben.
Ohne OpenCV, ohne Gesicht oder bei Fehlern gibt plan() None zurück, dann bleibt es beim alten Zuschnitt.
"""
import subprocess

STEP = 0.5          # Sekunden zwischen zwei Messungen
SMALL_W = 480       # Breite der Messbilder
MIN_SHARE = 0.3     # so viel Anteil der Messungen braucht ein Gesicht, damit sich der Zuschnitt lohnt
HOLD = 0.06         # Bild bleibt stehen, solange das Gesicht weniger als 6 % der Bildbreite wandert
MAX_POINTS = 24     # so viele Stützpunkte höchstens im ffmpeg-Ausdruck


def _detector():
    try:
        import cv2
    except ImportError:
        return None, None
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return (cv2, det) if not det.empty() else (None, None)


def detect(path, start, dur, width, height):
    """Liste (Zeit, Gesichtsmitte als Anteil der Breite oder None) für den Ausschnitt."""
    cv2, det = _detector()
    if not cv2 or width <= 0 or height <= 0:
        return None
    sh = max(2, int(SMALL_W * height / width / 2 + 0.5) * 2)
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", path,
           "-vf", f"fps={1 / STEP},scale={SMALL_W}:{sh}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    try:
        raw = subprocess.run(cmd, capture_output=True, timeout=600).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    import numpy as np
    size = SMALL_W * sh
    out = []
    for i in range(len(raw) // size):
        img = np.frombuffer(raw[i * size:(i + 1) * size], np.uint8).reshape(sh, SMALL_W)
        faces = det.detectMultiScale(img, scaleFactor=1.1, minNeighbors=6, minSize=(SMALL_W // 16, SMALL_W // 16))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            out.append((i * STEP, (x + w / 2) / SMALL_W))
        else:
            out.append((i * STEP, None))
    return out


def smooth(samples):
    """Aus den Messungen ruhige Stützpunkte [(Zeit, Mitte)] machen: Lücken füllen, Ausreißer glätten, ruhig halten."""
    seen = [x for _, x in samples if x is not None]
    if not samples or len(seen) < max(2, MIN_SHARE * len(samples)):
        return None
    fill, last = [], None
    for _, x in samples:  # Lücken mit dem letzten bekannten Wert füllen, am Anfang mit dem ersten
        last = x if x is not None else last
        fill.append(last)
    first = next(x for x in fill if x is not None)
    fill = [first if x is None else x for x in fill]
    med = [sorted(fill[max(0, i - 2):i + 3])[len(fill[max(0, i - 2):i + 3]) // 2] for i in range(len(fill))]
    points = [(t, x) for (t, _), x in zip(samples, med)]
    # Stützpunkte weglassen, solange die Linie dadurch kaum abweicht (ruhige Kamera, wenige Punkte)
    def err(k):
        (t0, x0), (t1, x1), (t2, x2) = points[k - 1], points[k], points[k + 1]
        return abs(x1 - (x0 + (x2 - x0) * (t1 - t0) / (t2 - t0)))
    while len(points) > 2:
        k = min(range(1, len(points) - 1), key=err) if len(points) > 2 else None
        if k is None or (err(k) > HOLD and len(points) <= MAX_POINTS):
            break
        del points[k]
    return points


def x_expr(points, scaled_w, out_w):
    """ffmpeg-Ausdruck für den linken Rand des Ausschnitts (Zeit t in Sekunden), auf die Bildgrenzen begrenzt."""
    hi = max(0, scaled_w - out_w)

    def px(c):
        return min(hi, max(0.0, c * scaled_w - out_w / 2))
    pts = [(t, px(c)) for t, c in points]
    expr = f"{pts[-1][1]:.1f}"
    for (t0, x0), (t1, x1) in reversed(list(zip(pts, pts[1:]))):
        if t1 <= t0:
            continue
        seg = f"{x0:.1f}" if x0 == x1 else f"{x0:.1f}+({x1 - x0:.1f})*(t-{t0:.2f})/{t1 - t0:.2f}"
        expr = f"if(lt(t,{t1:.2f}),{seg},{expr})"
    return f"if(lt(t,{pts[0][0]:.2f}),{pts[0][1]:.1f},{expr})".replace(",", r"\,")


def plan(path, start, dur, width, height, out_w, out_h):
    """Gibt (Anteil Messungen mit Gesicht, scale-Breite, x-Ausdruck) zurück oder None, wenn kein Gesicht gefunden wurde."""
    samples = detect(path, start, dur, width, height)
    if not samples:
        return None
    pts = smooth(samples)
    if not pts:
        return None
    scaled_w = int(width * out_h / height + 0.5)
    if scaled_w <= out_w:
        return None
    share = sum(x is not None for _, x in samples) / len(samples)
    return share, scaled_w, x_expr(pts, scaled_w, out_w)
