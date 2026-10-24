"""Zahlwörter in Ziffern umwandeln, nur für die Untertitel.

Die Stimme liest Zahlen besser, wenn sie als Wort im Skript stehen ("vierzehntausend").
Im Bild wirken Ziffern stärker ("14.000"), deshalb werden sie hier für die Anzeige umgewandelt.
"""
import re

UNITS = {"null": 0, "eins": 1, "ein": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7,
         "acht": 8, "neun": 9}
TEENS = {"zehn": 10, "elf": 11, "zwölf": 12, "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15, "sechzehn": 16,
         "siebzehn": 17, "achtzehn": 18, "neunzehn": 19}
TENS = {"zwanzig": 20, "dreißig": 30, "vierzig": 40, "fünfzig": 50, "sechzig": 60, "siebzig": 70, "achtzig": 80,
        "neunzig": 90}
# Wörter, die meistens Artikel sind und keine Zahl ("ein Auto")
SKIP = {"ein", "eine", "einen", "einem", "einer", "null"}


def _below100(s):
    for table in (TEENS, TENS):
        if s in table:
            return table[s]
    if s in UNITS:
        return UNITS[s]
    for m in re.finditer("und", s):
        unit, tens = s[:m.start()], s[m.end():]
        if unit in UNITS and unit != "eins" and tens in TENS:
            return UNITS[unit] + TENS[tens]
    return None


def _below1000(s):
    if "hundert" in s:
        head, tail = s.split("hundert", 1)
        h = 1 if head in ("", "ein") else _below100(head)   # auch "neunzehnhundert" = 19 x 100
        if h is None:
            return None
        if not tail:
            return h * 100
        t = _below100(tail)
        return None if t is None else h * 100 + t
    return _below100(s)


def parse(word):
    """Zahlwort -> Zahl (int oder float), sonst None."""
    s = word.lower()
    half = 0.0
    if s.endswith("einhalb") and len(s) > 7:
        s, half = s[:-7], 0.5
        if s == "ein":
            return 1.5
    if s == "anderthalb":
        return 1.5
    if "tausend" in s:
        head, tail = s.split("tausend", 1)
        th = 1 if head in ("", "ein") else _below1000(head)
        rest = 0 if not tail else _below1000(tail)
        if th is None or rest is None:
            return None
        value = th * 1000 + rest
    else:
        value = _below1000(s)
    if value is None:
        return None
    return value + half if half else value


def fmt(word, value):
    if isinstance(value, float):
        return f"{value:,.1f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    w = word.lower()
    year = (1100 <= value <= 2099 and "hundert" in w and "tausend" not in w) or \
           (2000 < value < 2100 and "tausend" in w and "hundert" not in w)
    if value < 1000 or year:
        return str(value)
    return f"{value:,}".replace(",", ".")


def _convert_part(part):
    m = re.fullmatch(r"([^\wäöüß]*)([\wäöüß]+)([^\wäöüß]*)", part)
    if not m:
        return part
    pre, core, post = m.groups()
    if core.lower() in SKIP:
        return part
    value = parse(core)
    return part if value is None else pre + fmt(core, value) + post


def display_word(word):
    """Ein Wort aus dem Skript, wie es im Untertitel stehen soll."""
    return "-".join(_convert_part(p) for p in word.split("-"))


def is_number(word):
    return any(c.isdigit() for c in word)
