"""Echte Videoclips von Pexels als Hintergrund (kostenlos, für YouTube erlaubt).

Für jeden Satz wird ein passender Hochkant-Clip gesucht, geladen und zwischengespeichert.
Suchbegriff je Satz: das Feld "clip" im Skript (englisch, z. B. "porsche steering wheel"),
sonst die *Sternchen*-Wörter des Satzes, sonst ein allgemeiner Begriff zur Nische.
Wird nicht für jeden Satz ein Clip gefunden, bleibt das Video bei der Animation.
"""
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30
API = "https://api.pexels.com/videos/search"
KEEP_USED = 300  # so viele zuletzt benutzte Clips nicht wiederholen

NICHE_QUERY = {
    "Business": "sports car driving",
    "Psychologie": "people thinking",
    "Geschichte": "ancient ruins",
    "Geld": "money coins",
    "Geografie": "aerial landscape",
}


def _get(url, key, timeout=20):
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "shorts-zentrale"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def queries(spec, seg):
    """Suchbegriffe für einen Satz, der beste zuerst: (Begriff, Sprache)."""
    out = []
    if seg.get("clip"):
        out.append((seg["clip"], "en-US"))
    stars = re.findall(r"\*([^*]+)\*", seg.get("text", ""))
    if stars:
        out.append((" ".join(stars), "de-DE"))
    out.append((NICHE_QUERY.get(spec.get("niche"), "nature"), "en-US"))
    return out


def best_file(video):
    """Die passende Datei eines Pexels-Videos: hochkant, mindestens 1280 hoch, nicht unnötig groß."""
    files = [f for f in video.get("video_files", [])
             if f.get("width") and f.get("height") and f["height"] > f["width"] and f["height"] >= 1280
             and f.get("file_type") == "video/mp4"]
    if not files:
        return None
    return min(files, key=lambda f: (abs(f["height"] - 1920), f["width"]))


def search(key, query, locale, min_dur, skip):
    params = urllib.parse.urlencode({"query": query, "orientation": "portrait", "size": "medium",
                                     "per_page": 15, "locale": locale})
    data = json.loads(_get(f"{API}?{params}", key))
    for v in data.get("videos", []):
        if v["id"] in skip or v.get("duration", 0) < min(min_dur, 6):
            continue
        f = best_file(v)
        if f:
            return {"id": v["id"], "link": f["link"], "url": v.get("url"), "user": (v.get("user") or {}).get("name")}
    return None


class Background:
    """Spielt je Satz einen Clip ab (abgedunkelt, damit die Schrift gut lesbar bleibt)."""

    def __init__(self, clips, starts, total):
        self.clips, self.starts, self.total = clips, starts, total
        self.overlay = _overlay()
        self._idx, self._proc, self._pos = None, None, 0

    def _open(self, idx, local):
        self.close()
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
              "eq=brightness=-0.05:saturation=1.12")
        self._proc = subprocess.Popen(
            ["ffmpeg", "-nostdin", "-loglevel", "error", "-stream_loop", "-1", "-ss", f"{local:.3f}",
             "-i", self.clips[idx], "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)
        self._idx, self._pos = idx, round(local * FPS)

    def frame(self, t):
        idx = max(i for i, s in enumerate(self.starts) if s <= t or i == 0)
        want = round((t - self.starts[idx]) * FPS)
        if idx != self._idx or not (self._pos <= want <= self._pos + 5):
            self._open(idx, max(0.0, t - self.starts[idx]))
            want = self._pos
        raw = None
        while self._pos <= want:
            raw = self._proc.stdout.read(W * H * 3)
            self._pos += 1
            if len(raw) < W * H * 3:
                raise RuntimeError("Clip ließ sich nicht abspielen")
        img = Image.frombuffer("RGB", (W, H), raw, "raw", "RGB", 0, 1)
        return Image.alpha_composite(img.convert("RGBA"), self.overlay).convert("RGB")

    def close(self):
        if self._proc:
            self._proc.kill()
            self._proc.wait()
            self._proc = None

    __del__ = close


def _overlay():
    """Dunkler Schleier: oben (Label) und im Untertitel-Bereich etwas stärker."""
    y = np.arange(H, dtype=np.float32)[:, None]
    a = 70 + 70 * np.exp(-((y - 1230) / 260) ** 2) + 60 * np.clip(1 - y / 380, 0, 1) + 40 * np.clip((y - 1500) / 420, 0, 1)
    alpha = np.repeat(np.clip(a, 0, 200).astype(np.uint8), W, axis=1)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 3] = alpha
    return Image.fromarray(rgba, "RGBA")


def prepare(spec, timings, total, pause, key, cache_dir, log=print):
    """Lädt die Clips für alle Sätze. Gibt (Background, Quellen) zurück, oder (None, []) wenn es nicht klappt."""
    if not key:
        return None, []
    os.makedirs(cache_dir, exist_ok=True)
    used_file = os.path.join(cache_dir, "used.json")
    try:
        used = json.load(open(used_file))
    except (OSError, ValueError):
        used = []
    starts = [0.0] + [s for s, _ in timings[1:]]
    ends = starts[1:] + [total]
    clips, credits, mine = [], [], set()
    try:
        for seg, s, e in zip(spec["segments"], starts, ends):
            hit = None
            for q, loc in queries(spec, seg):
                hit = search(key, q, loc, e - s, set(used) | mine)
                if hit:
                    break
            if not hit:
                log(f"Kein Clip gefunden für: {seg['text'][:40]}")
                return None, []
            path = os.path.join(cache_dir, f"{hit['id']}.mp4")
            if not os.path.exists(path):
                data = _get(hit["link"], key, timeout=90)
                with open(path + ".tmp", "wb") as f:
                    f.write(data)
                os.replace(path + ".tmp", path)
            if not _playable(path):
                os.remove(path)
                log(f"Clip {hit['id']} ist kaputt")
                return None, []
            mine.add(hit["id"])
            clips.append(path)
            credits.append(hit)
    except Exception as e:  # Netz weg, Schlüssel falsch, Limit erreicht: dann eben Animation
        log(f"Pexels nicht erreichbar: {e}")
        return None, []
    with open(used_file, "w") as f:
        json.dump((used + sorted(mine))[-KEEP_USED:], f)
    _tidy(cache_dir, keep=set(clips))
    return Background(clips, starts, total), credits


def _playable(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                              "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30).stdout.strip()
        return bool(out) and all(int(x) > 0 for x in out.split(",")[:2])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def _tidy(cache_dir, keep, max_files=60):
    """Alte Clips löschen, damit die Festplatte nicht vollläuft."""
    files = sorted((os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith(".mp4")),
                   key=os.path.getmtime)
    for f in files[:-max_files]:
        if f not in keep:
            os.remove(f)
