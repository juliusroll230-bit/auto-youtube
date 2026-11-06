"""Stimme von Fish Audio (fish.audio) statt der eingebauten Piper-Stimme.

Julius trägt im Reiter Kanal den API-Schlüssel und die ID der Stimme ein (aus dem Link
https://fish.audio/m/<ID>/). Optional eine zweite Stimme für Grusel und Mystery.
Klappt etwas nicht (Schlüssel falsch, Guthaben leer, kein Netz), spricht wieder Piper.
"""
import io
import json
import re
import urllib.error
import urllib.request
import wave

import numpy as np

URL = "https://api.fish.audio/v1/tts"
MODEL = "s2.1-pro"
DARK_MOODS = ("gruselig", "mysterioes")


def voice_id(text):
    """Holt die ID aus einem Fish-Audio-Link oder nimmt die eingegebene ID, sonst ""."""
    text = (text or "").strip()
    m = re.search(r"fish\.audio/(?:[a-z-]+/)?m/([A-Za-z0-9_-]+)", text)
    if m:
        return m.group(1)
    return text if re.fullmatch(r"[A-Za-z0-9_-]{8,64}", text) else ""


def speak(text, key, voice, rate, speed=1.0, timeout=60):
    """Spricht einen Satz und gibt float32-Samples mit der Abtastrate rate zurück."""
    body = json.dumps({"text": text, "reference_id": voice, "format": "wav", "latency": "normal", "normalize": True,
                       "prosody": {"speed": round(speed, 2), "volume": 0}}).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}", "model": MODEL, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        msg = {401: "Schlüssel ungültig", 402: "kein Guthaben mehr"}.get(e.code, f"Fehler {e.code}")
        raise RuntimeError(f"Fish Audio: {msg}") from None
    with wave.open(io.BytesIO(data)) as w:
        src, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise RuntimeError("Fish Audio: unerwartetes Tonformat")
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if src != rate:  # auf die Abtastrate der übrigen Tonspur bringen
        n = int(len(x) * rate / src)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    # Stille am Anfang und Ende abschneiden, damit die Sätze dicht aufeinander folgen
    loud = np.flatnonzero(np.abs(x) > 0.01)
    if len(loud):
        x = x[max(0, loud[0] - int(0.03 * rate)):loud[-1] + int(0.08 * rate)]
    return x


class Voice:
    """Piper mit Fish-Audio-Stimme davor. Alles andere (z. B. config.sample_rate) kommt von Piper."""

    def __init__(self, piper, key, voice, dark_voice=""):
        self.piper, self.key, self.voice, self.dark_voice = piper, key, voice, dark_voice or voice
        self.error = None   # letzter Fehler, damit die Zentrale ihn anzeigen kann

    def __getattr__(self, name):
        return getattr(self.piper, name)

    def pick(self, mood):
        return self.dark_voice if mood in DARK_MOODS else self.voice
