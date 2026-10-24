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


def mix(voice, rate, cuts, seed, pops=()):
    """Legt Musik (leiser, wenn gesprochen wird) und Effekte unter die Stimme.

    voice: Sprachspur als float32, cuts: Zeitpunkte (s) der Satzwechsel für die Whooshes,
    pops: Zeitpunkte, an denen eine Zahl kommt (kurzer Klick).
    """
    n = len(voice)
    bed = music(n / rate + 0.1, rate, seed)[:n]
    if len(bed) < n:
        bed = np.pad(bed, (0, n - len(bed)))
    # Ducking: Musik geht runter, sobald die Stimme spricht
    win = int(0.08 * rate)
    env = np.convolve(np.abs(voice), np.ones(win) / win, mode="same")
    duck = 1 - 0.55 * np.clip(env / 0.04, 0, 1)
    duck = np.convolve(duck, np.ones(win) / win, mode="same")
    out = voice * 1.0 + bed * 0.22 * duck
    sfx = np.zeros(n, dtype=np.float32)
    _add(sfx, 0, 0.35 * pop(rate))
    for p in pops:
        _add(sfx, p * rate, 0.18 * tick(rate))
    for i, c in enumerate(cuts):
        w = whoosh(rate, seed + i)
        _add(sfx, max(0, c - 0.2) * rate, 0.22 * w)
    out = out + sfx
    return (out / max(1.0, np.abs(out).max() / 0.95)).astype(np.float32)
