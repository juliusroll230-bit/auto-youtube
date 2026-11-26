"""Ton für die Shorts: eigene Hintergrundmusik und Soundeffekte, komplett selbst erzeugt.

Es werden keine fremden Aufnahmen benutzt, also gibt es keine Urheberrechtsprobleme.
Jedes Video bekommt über den seed eine eigene Variante (Tempo, Tonart, Akkordfolge).
"""
import numpy as np

# Akkordfolgen als (Halbtöne über dem Grundton, Moll?)
PROGRESSIONS = [
    [(0, True), (-4, False), (3, False), (-2, False)],   # i  VI III VII
    [(0, True), (5, True), (-4, False), (-2, False)],    # i  iv VI VII
    [(0, True), (-2, False), (-4, False), (-2, False)],  # i  VII VI VII
    [(0, True), (3, False), (-2, False), (5, True)],     # i  III VII iv
]


def _note_hz(semitones_from_a2):
    return 110.0 * 2 ** (semitones_from_a2 / 12)


def _env(n, rate, attack, decay):
    t = np.arange(n) / rate
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def _lowpass(x, alpha):
    """Einfacher Tiefpass (exponentielles Glätten), alpha zwischen 0 und 1."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def _add(buf, start, sound):
    i = int(start)
    if i >= len(buf):
        return
    end = min(len(buf), i + len(sound))
    buf[i:end] += sound[:end - i]


def music(seconds, rate, seed):
    """Lockerer, treibender Beat mit Bass, Flächen und Zupf-Melodie."""
    rng = np.random.default_rng(seed)
    bpm = float(rng.choice([96, 100, 104, 108, 112]))
    root = int(rng.choice([0, 2, 3, 5, 7, -2]))
    prog = PROGRESSIONS[int(rng.integers(len(PROGRESSIONS)))]
    beat = 60 / bpm
    n = int(seconds * rate)
    out = np.zeros(n, dtype=np.float64)

    # Kick (auf jedem Schlag), Hi-Hat (Achtel), Clap (2 und 4)
    kt = np.arange(int(0.3 * rate)) / rate
    kick = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-kt * 30)) / rate) * np.exp(-kt * 9)
    noise = rng.standard_normal(int(0.08 * rate))
    hat = np.diff(noise, prepend=0) * _env(len(noise), rate, 0.001, 0.018)
    clap_noise = rng.standard_normal(int(0.2 * rate))
    clap = _lowpass(clap_noise, 0.35) * _env(len(clap_noise), rate, 0.002, 0.06)

    beats = int(seconds / beat) + 1
    for b in range(beats):
        t0 = b * beat * rate
        _add(out, t0, 0.9 * kick)
        _add(out, t0 + beat * rate / 2, 0.16 * hat)
        _add(out, t0, 0.08 * hat)
        if b % 2 == 1:
            _add(out, t0, 0.35 * clap)

    # Bass, Flächen und Zupf-Arpeggio je Takt
    bar = 4 * beat
    for k in range(int(seconds / bar) + 1):
        semi, minor = prog[k % len(prog)]
        base = root + semi
        third = 3 if minor else 4
        start = k * bar * rate
        # Bass: Grundton auf 1, 2+ und 3
        for pos in (0, 1.5, 2):
            m = int(beat * 0.9 * rate)
            t = np.arange(m) / rate
            f = _note_hz(base - 12)
            tone = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
            _add(out, start + pos * beat * rate, 0.32 * tone * _env(m, rate, 0.005, 0.35))
        # Fläche: weicher Dreiklang über den ganzen Takt
        m = int(bar * rate)
        t = np.arange(m) / rate
        pad = sum(np.sin(2 * np.pi * _note_hz(base + 12 + iv) * t + h) for iv, h in ((0, 0), (third, 1), (7, 2)))
        swell = np.minimum(1, t / 0.4) * np.minimum(1, (bar - t) / 0.3)
        _add(out, start, 0.05 * pad * swell)
        # Zupf-Melodie: Akkordtöne in Achteln
        tones = [0, third, 7, 12, 7, third, 0, 7]
        for j, iv in enumerate(tones):
            m = int(beat / 2 * rate)
            t = np.arange(m) / rate
            f = _note_hz(base + 24 + iv)
            pl = np.sin(2 * np.pi * f * t) * _env(m, rate, 0.002, 0.09)
            _add(out, start + j * beat / 2 * rate, 0.07 * pl)

    out /= max(1e-6, np.abs(out).max())
    fade = int(0.8 * rate)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)


def whoosh(rate, seed=0, length=0.38):
    """Kurzes Rauschen, das an- und abschwillt: klingt nach schnellem Vorbeiziehen."""
    rng = np.random.default_rng(seed)
    n = int(length * rate)
    t = np.linspace(0, 1, n)
    shape = np.sin(np.pi * t) ** 2
    noise = rng.standard_normal(n)
    # Filter öffnet sich zur Mitte und schließt wieder
    alpha = 0.04 + 0.5 * shape
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc += alpha[i] * (noise[i] - acc)
        y[i] = acc
    y *= shape
    return (y / max(1e-6, np.abs(y).max())).astype(np.float32)


def pop(rate):
    """Kurzer, weicher Klick für den Einstieg."""
    n = int(0.12 * rate)
    t = np.arange(n) / rate
    f = 900 * np.exp(-t * 25) + 300
    return (np.sin(2 * np.pi * np.cumsum(f) / rate) * np.exp(-t * 35)).astype(np.float32)


def tick(rate):
    """Heller, kurzer Klick, wenn eine Zahl eingeblendet wird."""
    n = int(0.07 * rate)
    t = np.arange(n) / rate
    return (np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 60) + 0.5 * np.sin(2 * np.pi * 2700 * t) * np.exp(-t * 80)).astype(np.float32)


def riser(rate, seed=0, length=0.9):
    """Rauschen, das immer heller und lauter wird: baut Spannung kurz vor der Auflösung auf."""
    rng = np.random.default_rng(seed + 99)
    n = int(length * rate)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    alpha = 0.02 + 0.6 * t ** 2
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc += alpha[i] * (noise[i] - acc)
        y[i] = acc
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * t ** 2) / rate)
    y = (y / max(1e-6, np.abs(y).max()) + 0.35 * tone) * t ** 2.2
    return (y / max(1e-6, np.abs(y).max())).astype(np.float32)


def hit(rate):
    """Tiefer Schlag mit hellem Knall obendrauf: der Moment, in dem die Auflösung kommt."""
    n = int(0.7 * rate)
    t = np.arange(n) / rate
    low = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-t * 14)) / rate) * np.exp(-t * 5)
    snap = np.random.default_rng(7).standard_normal(n) * np.exp(-t * 45)
    return ((low + 0.4 * snap) / 1.4).astype(np.float32)


def bloop(rate):
    """Kurzer, steigender Ton auf einem Schlüsselwort (wie ein Daumen-hoch-Geräusch)."""
    n = int(0.11 * rate)
    t = np.arange(n) / rate
    f = 520 + 1500 * t
    return (np.sin(2 * np.pi * np.cumsum(f) / rate) * np.exp(-t * 28)).astype(np.float32)


def ding(rate):
    """Heller Glockenton für den Reaktions-Sticker (Aha!)."""
    n = int(0.9 * rate)
    t = np.arange(n) / rate
    y = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((1320, 1.0, 5), (1980, 0.5, 7), (2640, 0.25, 9)))
    return (y / 1.75).astype(np.float32)


DARK_MOODS = ("gruselig", "mysterioes")


def dark_music(seconds, rate, seed):
    """Unheimliche Musik: tiefes Brummen, langsame Moll-Fläche, leiser Herzschlag und Spieluhr-Töne."""
    rng = np.random.default_rng(seed)
    n = int(seconds * rate)
    t = np.arange(n) / rate
    root = int(rng.choice([-5, -3, -2, 0, 1]))
    out = np.zeros(n, dtype=np.float64)
    # Brummen: Grundton zwei Oktaven tiefer, leicht schwebend
    f0 = _note_hz(root - 12)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t)
    out += 0.35 * lfo * (np.sin(2 * np.pi * f0 * t) + 0.4 * np.sin(2 * np.pi * f0 * 1.007 * t))
    # Fläche: Moll-Akkorde, die langsam wechseln (je 6 Sekunden)
    prog = [(0, 3, 7), (-4, 0, 3), (1, 4, 8), (-2, 1, 5)]
    seg = 6.0
    for k in range(int(seconds / seg) + 1):
        m = int(seg * rate)
        tt = np.arange(m) / rate
        chord = prog[(k + int(rng.integers(4))) % len(prog)]
        pad = sum(np.sin(2 * np.pi * _note_hz(root + 12 + iv) * tt + j) for j, iv in enumerate(chord))
        swell = np.sin(np.pi * np.clip(tt / seg, 0, 1)) ** 2
        _add(out, k * seg * rate, 0.06 * pad * swell)
    # Herzschlag: zwei dumpfe Schläge, etwa 70 pro Minute
    kt = np.arange(int(0.25 * rate)) / rate
    thump = np.sin(2 * np.pi * np.cumsum(40 + 50 * np.exp(-kt * 25)) / rate) * np.exp(-kt * 14)
    beat = 60 / 70
    for b in range(int(seconds / beat) + 1):
        _add(out, b * beat * rate, 0.5 * thump)
        _add(out, (b * beat + 0.22) * rate, 0.3 * thump)
    # Spieluhr: einzelne hohe Töne, selten und unregelmäßig
    scale = [0, 3, 7, 8, 12, 15]
    at = 1.5
    while at < seconds - 1:
        m = int(1.6 * rate)
        tt = np.arange(m) / rate
        f = _note_hz(root + 36 + int(rng.choice(scale)))
        bell = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt * 2.2)
        _add(out, at * rate, 0.09 * bell)
        at += float(rng.uniform(1.4, 3.2))
    out /= max(1e-6, np.abs(out).max())
    fade = int(0.8 * rate)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)


def warm_music(seconds, rate, seed):
    """Ruhige, freundliche Musik für Geschichten: weiche Dur-Fläche und leise Spieluhr, ohne Schlagzeug."""
    rng = np.random.default_rng(seed)
    n = int(seconds * rate)
    root = int(rng.choice([0, 2, 5, 7]))
    out = np.zeros(n, dtype=np.float64)
    prog = [(0, 4, 7), (-3, 0, 4), (5, 9, 12), (7, 11, 14)]   # I, vi, IV, V
    seg = 4.0
    for k in range(int(seconds / seg) + 1):
        m = int(seg * rate)
        tt = np.arange(m) / rate
        chord = prog[k % len(prog)]
        pad = sum(np.sin(2 * np.pi * _note_hz(root + 12 + iv) * tt) + 0.3 * np.sin(2 * np.pi * _note_hz(root + 24 + iv) * tt)
                  for iv in chord)
        swell = np.sin(np.pi * np.clip(tt / seg, 0, 1)) ** 1.5
        _add(out, k * seg * rate, 0.07 * pad * swell)
        # Spieluhr: ein paar Töne aus dem Akkord, sanft verteilt
        for j in range(4):
            f = _note_hz(root + 36 + chord[int(rng.integers(3))])
            bt = np.arange(int(1.2 * rate)) / rate
            bell = (np.sin(2 * np.pi * f * bt) + 0.25 * np.sin(2 * np.pi * f * 3 * bt)) * np.exp(-bt * 3)
            _add(out, (k * seg + j * seg / 4 + float(rng.uniform(0, 0.15))) * rate, 0.05 * bell)
    out /= max(1e-6, np.abs(out).max())
    fade = int(0.8 * rate)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)


def tension_music(seconds, rate, seed):
    """Spannungsmusik wie bei den großen 3D-Erklärkanälen (Vorbild-Taktik, Test seit 25.11.2026):
    pulsierender tiefer Synth in Achteln, leises Uhr-Ticken, dunkle Fläche, die langsam anschwillt. Kein Schlagzeug."""
    rng = np.random.default_rng(seed)
    bpm = float(rng.choice([112, 118, 124]))
    root = int(rng.choice([-5, -3, -2, 0]))
    eighth = 30 / bpm
    n = int(seconds * rate)
    out = np.zeros(n, dtype=np.float64)
    prog = [0, 0, -4, -2] if rng.random() < .5 else [0, 1, 0, -2]
    m = int(eighth * 0.85 * rate)
    tt = np.arange(m) / rate
    env = _env(m, rate, 0.004, 0.12)
    tick_n = rng.standard_normal(int(0.02 * rate))
    tk = np.diff(tick_n, prepend=0) * _env(len(tick_n), rate, 0.0005, 0.006)
    for k in range(int(seconds / eighth) + 1):
        bar = k // 16   # alle 2 Takte ein neuer Ton
        semi = root + prog[bar % len(prog)]
        f = _note_hz(semi - 12)
        accent = 1.0 if k % 4 == 0 else 0.7
        saw = sum(np.sin(2 * np.pi * f * h * tt) / h for h in (1, 2, 3, 4))
        _add(out, k * eighth * rate, 0.22 * accent * _lowpass(saw, 0.25) * env)
        if k % 2 == 0:   # Uhr-Ticken auf jedem Viertel, das zweite leiser
            _add(out, k * eighth * rate, (0.10 if k % 4 == 0 else 0.06) * tk)
    t = np.arange(n) / rate
    swell = np.clip(t / max(1.0, seconds), 0, 1)   # wird bis zum Ende langsam dichter
    for iv, ph in ((0, 0), (3, 1), (7, 2)):
        out += (0.03 + 0.05 * swell) * np.sin(2 * np.pi * _note_hz(root + iv) * t + ph)
    out /= max(1e-6, np.abs(out).max())
    fade = int(0.8 * rate)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)


def light_music(seconds, rate, seed):
    """Verspielte, neugierige Musik (Vorbild-Taktik der Was-wäre-wenn-Kanäle, Test seit 25.11.2026):
    gezupfte Töne in Dur, leichter Shaker, weicher Bass. Kein Kick, damit die Stimme frei bleibt."""
    rng = np.random.default_rng(seed)
    bpm = float(rng.choice([100, 106, 112]))
    root = int(rng.choice([0, 2, 5, 7]))
    beat = 60 / bpm
    n = int(seconds * rate)
    out = np.zeros(n, dtype=np.float64)
    prog = [(0, 4, 7), (5, 9, 12), (7, 11, 14), (0, 4, 7)] if rng.random() < .5 else [(0, 4, 7), (-3, 0, 4), (5, 9, 12), (7, 11, 14)]
    pattern = [0, 2, 1, 2, 0, 2, 1, None]   # Akkordton je Achtel (None = Pause)
    shaker_n = rng.standard_normal(int(0.05 * rate))
    shaker = np.diff(shaker_n, prepend=0) * _env(len(shaker_n), rate, 0.004, 0.02)
    m = int(beat / 2 * rate)
    tt = np.arange(m) / rate
    for k in range(int(seconds / (beat / 2)) + 1):
        chord = prog[(k // 8) % len(prog)]
        at = k * beat / 2 * rate
        idx = pattern[k % 8]
        if idx is not None:
            f = _note_hz(root + 24 + chord[idx])
            pl = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt)) * _env(m, rate, 0.002, 0.07)
            _add(out, at, 0.16 * pl)
        _add(out, at, (0.05 if k % 2 else 0.03) * shaker)
        if k % 4 == 0:   # weicher Bass auf 1 und 3
            f = _note_hz(root - 12 + chord[0])
            bm = int(beat * 0.9 * rate)
            bt = np.arange(bm) / rate
            _add(out, at, 0.22 * np.sin(2 * np.pi * f * bt) * _env(bm, rate, 0.006, 0.3))
    out /= max(1e-6, np.abs(out).max())
    fade = int(0.8 * rate)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)


def drop_music(seconds, rate, seed, drop):
    """Bis zum Aha-Moment nur leises Ticken und eine Fläche, auf dem Aha-Moment setzt der volle Beat ein
    (Vorbild-Taktik „Beat-Drop auf der Auflösung“, Test seit 25.11.2026)."""
    beat_track = music(seconds, rate, seed)
    calm = tension_music(seconds, rate, seed + 1)
    n = min(len(beat_track), len(calm))
    d = int(max(0.0, min(seconds, drop or seconds * .7)) * rate)
    x = np.zeros(n, dtype=np.float32)
    x[d:] = 1.0
    win = int(0.05 * rate)
    x = np.convolve(x, np.ones(win) / win, mode="same")
    return (calm[:n] * 0.55 * (1 - x) + beat_track[:n] * x).astype(np.float32)


def boom(rate):
    """Tiefer, dumpfer Schlag für den Einstieg bei Grusel-Videos."""
    n = int(0.9 * rate)
    t = np.arange(n) / rate
    return (np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t * 8)) / rate) * np.exp(-t * 4)).astype(np.float32)


# --- Entspannungsvideos und Spannung (seit 20.11.2026), alles selbst erzeugt -------------------------------

def _shaped_noise(n, rate, seed, lo, hi, tilt=0.0):
    """Rauschen, auf ein Frequenzband begrenzt (per FFT, schnell auch bei langen Spuren). tilt < 0: dumpfer."""
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / rate)
    gain = ((f >= lo) & (f <= hi)) * (np.maximum(f, 20) / 1000.0) ** tilt
    y = np.fft.irfft(spec * gain, n)
    return y / max(1e-6, np.abs(y).max())


def ambience(kind, seconds, rate, seed, loop=False):
    """Geräusch für Entspannungsvideos: "regen" (Rauschen + Tropfen), "feuer" (Knistern), "pendel" (leises Klicken).

    loop: Ende geht nahtlos in den Anfang über (das Rauschen ist per FFT ohnehin rund, Tropfen am Ende laufen vorne
    weiter), dann kein Einblenden. So lässt sich eine kurze Schleife beliebig oft wiederholen.
    """
    n = int(seconds * rate)
    rng = np.random.default_rng(seed + 31)
    out = np.zeros(n)

    def _add(buf, start, sound):   # wie das globale _add, aber bei loop rund herum
        i = int(start)
        if not loop:
            return globals()["_add"](buf, i, sound)
        idx = (i + np.arange(len(sound))) % len(buf)
        np.add.at(buf, idx, sound)
    if kind == "regen":
        out += 0.6 * _shaped_noise(n, rate, seed, 300, 9000, tilt=-0.4)
        drop_t = np.arange(int(0.03 * rate)) / rate
        for _ in range(int(seconds * 9)):
            f = rng.uniform(1800, 4200)
            _add(out, rng.integers(n), rng.uniform(0.05, 0.25) * np.sin(2 * np.pi * f * drop_t) * np.exp(-drop_t * 160))
    elif kind == "feuer":
        out += 0.5 * _shaped_noise(n, rate, seed, 40, 900, tilt=-0.8)   # tiefes Rauschen der Flammen
        k = int(0.012 * rate)
        for _ in range(int(seconds * 14)):
            c = rng.standard_normal(k) * np.exp(-np.arange(k) / rate * 500)
            _add(out, rng.integers(n), rng.uniform(0.2, 1.0) * c)
    else:   # pendel: ganz leises, weiches Klicken wie ein Uhrwerk
        tt = np.arange(int(0.05 * rate)) / rate
        clk = np.sin(2 * np.pi * 1100 * tt) * np.exp(-tt * 90)
        for i in range(int(seconds / 0.5)):
            _add(out, int(i * 0.5 * rate), (0.35 if i % 2 else 0.22) * clk)
        tt = np.arange(n) / rate   # ruhige, weiche Fläche darunter (ganze Hertz-Zahlen: läuft nahtlos weiter)
        swell = 0.6 + 0.4 * np.sin(2 * np.pi * tt * round(seconds / 10) / seconds)
        out += 0.12 * swell * sum(np.sin(2 * np.pi * f * tt) for f in (110, 165, 220, 277))
    fade = min(n // 2, int(0.6 * rate))
    if fade and not loop:
        out[:fade] *= np.linspace(0, 1, fade)
    return (out / max(1e-6, np.abs(out).max())).astype(np.float32)


def _loop_env(n, rate, seed, every, lo=0.0, hi=1.0):
    """Weiche, zufällige Lautstärke-Kurve, die am Ende nahtlos in den Anfang übergeht (ein Wert alle `every` Sekunden)."""
    k = max(2, int(n / rate / every))
    pts = np.random.default_rng(seed).uniform(lo, hi, k)
    x = np.arange(n) / n * k
    xp = np.arange(k + 1)
    return np.interp(x, xp, np.append(pts, pts[0]))


def soundscape(recipe, seconds, rate, seed, loop=True):
    """Quiet Corner (seit 21.11.2026): mehrere Geräusch-Schichten, z. B. {"regen": 1, "uhr": .25, "donner": .6}.

    Alles selbst erzeugt, ohne fremde Aufnahmen. Mit loop=True geht das Ende nahtlos in den Anfang über.
    Schichten: regen, scheibe (dumpfer Regen an der Scheibe), feuer (Lagerfeuer), kamin, donner, uhr, cafe, wind,
    seiten (Buchseiten), grillen.
    """
    n = int(seconds * rate)
    rng = np.random.default_rng(seed + 77)
    out = np.zeros(n)

    def put(buf, start, sound):
        idx = (int(start) + np.arange(len(sound))) % len(buf) if loop else None
        if loop:
            np.add.at(buf, idx, sound)
        else:
            _add(buf, start, sound)

    def norm(y):
        return y / max(1e-6, np.abs(y).max())

    for name, gain in recipe.items():
        if not gain:
            continue
        lay = np.zeros(n)
        sd = seed + sum(map(ord, name))
        if name in ("regen", "feuer"):
            lay = ambience(name, seconds, rate, sd, loop=loop).astype(float)
        elif name == "scheibe":
            lay += 0.7 * _shaped_noise(n, rate, sd, 120, 5000, tilt=-0.9) * (0.85 + 0.15 * _loop_env(n, rate, sd, 4))
            tt = np.arange(int(0.05 * rate)) / rate
            for _ in range(int(seconds * 5)):
                f = rng.uniform(700, 1500)
                put(lay, rng.integers(n), rng.uniform(0.05, 0.18) * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 90))
        elif name == "kamin":
            lay += 0.45 * _shaped_noise(n, rate, sd, 30, 500, tilt=-1.0) * (0.7 + 0.3 * _loop_env(n, rate, sd, 2))
            for _ in range(int(seconds * 9)):
                k = int(rng.uniform(0.006, 0.02) * rate)
                put(lay, rng.integers(n), rng.uniform(0.15, 0.8) * rng.standard_normal(k) * np.exp(-np.arange(k) / rate * 400))
            for _ in range(int(seconds / 7)):   # ab und zu ein lauteres Knacken
                k = int(0.04 * rate)
                put(lay, rng.integers(n), rng.standard_normal(k) * np.exp(-np.arange(k) / rate * 120))
        elif name == "donner":   # zu den Blitzen in quiet.js (bei 38 % und 70 % der Schleife, kurz danach)
            for at, g in ((0.38, 1.0), (0.70, 0.7)):
                k = int(5.5 * rate)
                tt = np.arange(k) / rate
                env = np.minimum(1, tt / 0.35) * np.exp(-tt * 0.75) * (0.7 + 0.3 * np.sin(2 * np.pi * 1.3 * tt))
                put(lay, (at * seconds + 1.1) * rate, g * _shaped_noise(k, rate, sd + int(at * 100), 25, 220, tilt=-1.2) * env)
        elif name == "uhr":
            tt = np.arange(int(0.03 * rate)) / rate
            for i in range(int(seconds)):
                f = 2600 if i % 2 else 2100
                put(lay, i * rate, (0.8 if i % 2 else 0.6) * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 260))
        elif name == "cafe":   # leises Stimmengewirr ohne Worte, dazu Tassen und Löffel
            for v in range(7):
                band = _shaped_noise(n, rate, sd + v, 220 + v * 60, 1400 + v * 150, tilt=-0.6)
                lay += band * _loop_env(n, rate, sd + 50 + v, rng.uniform(0.25, 0.6), 0.0, 1.0) ** 2
            lay = 0.6 * norm(lay)
            tt = np.arange(int(0.5 * rate)) / rate
            for _ in range(int(seconds / 5)):
                f = rng.uniform(2800, 4200)
                clink = (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt * 14)
                put(lay, rng.integers(n), rng.uniform(0.04, 0.12) * clink)
        elif name == "wind":
            lay += _shaped_noise(n, rate, sd, 60, 1100, tilt=-1.1) * (0.25 + 0.75 * _loop_env(n, rate, sd, 5) ** 2)
        elif name == "seiten":
            for _ in range(max(1, int(seconds / 14))):
                k = int(0.4 * rate)
                env = np.sin(np.linspace(0, np.pi, k)) ** 2
                put(lay, rng.integers(n), 0.6 * _shaped_noise(k, rate, int(rng.integers(1 << 30)), 1500, 9000, tilt=-0.3) * env)
        elif name == "grillen":
            tt = np.arange(int(0.012 * rate)) / rate
            pulse = np.sin(2 * np.pi * 4600 * tt) * np.sin(np.pi * tt / tt[-1])
            t0 = 0.0
            while t0 < seconds - 1:
                for j in range(3):
                    put(lay, (t0 + j * 0.03) * rate, 0.3 * pulse)
                t0 += rng.uniform(0.6, 1.1)
        else:
            continue
        out += gain * norm(lay)
    return (out / max(1e-6, np.abs(out).max())).astype(np.float32)


def heartbeat(rate):
    """Ein Herzschlag (lub-dub): zwei tiefe, dumpfe Schläge kurz hintereinander."""
    n = int(0.5 * rate)
    t = np.arange(n) / rate

    def thump(at, f, g):
        tt = np.clip(t - at, 0, None)
        return g * (t >= at) * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 18) * np.minimum(1, tt / 0.004)
    y = thump(0, 55, 1.0) + thump(0.16, 48, 0.7)
    return (y / max(1e-6, np.abs(y).max())).astype(np.float32)


def tension_beats(reveal, start=0.4):
    """Zeitpunkte der Herzschläge bis zur Auflösung: anfangs ruhig (ca. 70/min), am Ende schnell (ca. 120/min)."""
    if not reveal or reveal <= start + 1:
        return []
    beats, t = [], start
    while t < reveal - 0.15:
        beats.append(round(t, 3))
        p = (t - start) / (reveal - start)
        t += 0.86 - 0.36 * p
    return beats


def snap(rate):
    """Sehr kurzer, trockener Klick mit Luft: der Schnitt-Ton im Tempo "schnell" (selbst erzeugt)."""
    n = int(0.09 * rate)
    t = np.arange(n) / rate
    rng = np.random.default_rng(7)
    click = np.sin(2 * np.pi * (1400 - 6000 * t) * t) * np.exp(-t * 90)
    air = rng.standard_normal(n) * np.exp(-t * 60) * 0.5
    y = click + _lowpass(air, 0.35)
    return (y / max(1e-6, np.abs(y).max())).astype(np.float32)


def mix(voice, rate, cuts, seed, pops=(), mood=None, accent=None, keys=(), sticker=False, beats=(), snaps=(), bell=None,
        style=None, drop=None):
    """Legt Musik (leiser, wenn gesprochen wird) und Effekte unter die Stimme.

    voice: Sprachspur als float32, cuts: Zeitpunkte (s) der Satzwechsel für die Whooshes,
    pops: Zeitpunkte, an denen eine Zahl kommt (kurzer Klick),
    mood: "gruselig" oder "mysterioes" für unheimliche Musik statt Beat, "warm" für ruhige Geschichten-Musik,
    accent: Zeitpunkt (s) der Auflösung. Dann steigt davor ein Riser an, auf ihr kommt ein Schlag und die Musik
    setzt kurz aus (Test "Soundeffekte: stark" seit 19.11.2026),
    keys: Zeitpunkte der Schlüsselwörter (kurzer steigender Ton), sticker: Glockenton auf der Auflösung ("voll").
    beats: Herzschläge (Variante "Spannung"), dann ist die Musik leiser.
    snaps: Zwischenschnitte (Tempo "schnell"): kurzer Snap, Musik leiser, damit die Stimme klar bleibt.
    bell: Zeitpunkt (s), an dem der Abo-Knopf erscheint: leiser Klick und Glockenton.
    style: Musik-Stil (learn.MUSIC_FOR_MOOD): "beat", "spannung", "leicht", "drop", "dunkel", "warm". None = nach Stimmung.
    drop: Zeitpunkt (s) der Auflösung, auf dem bei "drop" der Beat einsetzt.
    """
    n = len(voice)
    dark = mood in DARK_MOODS
    warm = mood == "warm"
    secs = n / rate + 0.1
    if style == "spannung":
        bed = tension_music(secs, rate, seed)
    elif style == "leicht" and not dark and not warm:
        bed = light_music(secs, rate, seed)
    elif style == "drop" and not dark and not warm:
        bed = drop_music(secs, rate, seed, drop)
    else:
        bed = (dark_music if dark else warm_music if warm else music)(secs, rate, seed)
    bed = bed[:n]
    if len(bed) < n:
        bed = np.pad(bed, (0, n - len(bed)))
    # Ducking: Musik geht runter, sobald die Stimme spricht
    win = int(0.08 * rate)
    env = np.convolve(np.abs(voice), np.ones(win) / win, mode="same")
    duck = 1 - 0.55 * np.clip(env / 0.04, 0, 1)
    duck = np.convolve(duck, np.ones(win) / win, mode="same")
    if accent is not None:  # Musik setzt für einen Moment aus: die Stille macht die Auflösung lauter
        a, b = int(accent * rate), int((accent + 0.7) * rate)
        gap = np.ones(n, dtype=np.float32)
        gap[max(0, a):max(0, min(n, b))] = 0.0
        duck = duck * np.convolve(gap, np.ones(win) / win, mode="same")
    out = voice * 1.0 + bed * (0.3 if dark else 0.2 if warm else 0.22) * (0.55 if beats else 0.8 if snaps else 1.0) * duck
    sfx = np.zeros(n, dtype=np.float32)
    _add(sfx, 0, 0.5 * boom(rate) if dark else 0.35 * pop(rate))
    for p in pops:
        _add(sfx, p * rate, 0.18 * tick(rate))
    for i, c in enumerate(cuts):
        if accent is not None and abs(c - accent) < 0.02:
            continue  # vor der Auflösung kein Whoosh: dort kommt Stille und der Schlag
        w = whoosh(rate, seed + i)
        _add(sfx, max(0, c - 0.2) * rate, (0.12 if dark else 0.08 if warm else 0.22) * w)
    if accent is not None:
        r = riser(rate, seed)
        _add(sfx, max(0, accent * rate - len(r)), (0.10 if warm else 0.16) * r)
        _add(sfx, accent * rate, (0.25 if warm else 0.45) * hit(rate))
        if sticker:
            _add(sfx, (accent + 0.12) * rate, (0.10 if dark else 0.16) * ding(rate))
    for k in keys:
        _add(sfx, k * rate, (0.07 if warm else 0.12) * bloop(rate))
    if snaps:
        sn = snap(rate)
        for c in snaps:
            if accent is None or abs(c - accent) > 0.3:
                _add(sfx, c * rate, (0.05 if dark else 0.07) * sn)
    if beats:
        hb = heartbeat(rate)
        for i, b in enumerate(beats):   # wird zum Ende hin etwas lauter
            _add(sfx, b * rate, (0.22 + 0.16 * i / max(1, len(beats) - 1)) * hb)
    if bell is not None:
        _add(sfx, bell * rate, 0.14 * pop(rate))
        _add(sfx, (bell + 0.18) * rate, (0.06 if dark else 0.09) * ding(rate))
    out = out + sfx
    return (out / max(1.0, np.abs(out).max() / 0.95)).astype(np.float32)
