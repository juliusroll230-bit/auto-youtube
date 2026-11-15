"""Prüft die eigenen Thumbnails ohne Chromium (Szene als Platzhalter):
    python tests/thumbnail_test.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="thumb-test-")

from PIL import Image  # noqa: E402

import learn  # noqa: E402
import thumbnail  # noqa: E402
import yt  # noqa: E402

long_spec = json.load(open(os.path.join(ROOT, "seed", "0112-erklaert-kuehlschrank-lang.json"), encoding="utf-8"))
t = thumbnail.texts(long_spec)
assert t["A"][0] == "KÜHLSCHRANK", t
assert all(len(x.split()) <= 4 for x in (" ".join(t["A"]), t["B"])), "höchstens 4 Wörter"
assert thumbnail.emoji_for(long_spec) == "🧊"

own = dict(long_spec, thumb_text=["Kühlschrank | macht keine Kälte", "Er lügt dich an"])
t = thumbnail.texts(own)
assert t["A"] == ("KÜHLSCHRANK", "MACHT KEINE KÄLTE") and t["B"] == "ER LÜGT DICH AN", t
assert thumbnail.texts(dict(long_spec, thumb_text=["Nie wieder warm"]))["A"] == ("NIE WIEDER WARM", "")

short = {"slug": "s", "title": "Was passiert, wenn du tagelang nicht schläfst? 😵", "niche": "Erklären",
         "segments": [{"text": "x", "szene": {"typ": "figur", "objekt": "🛏️"}}]}
assert thumbnail.texts(short)["A"] == ("UND DANN?", ""), thumbnail.texts(short)
assert thumbnail.emoji_for(short) == "😵"
assert thumbnail.subject({"title": "Das Schiff, das niemand fand 🚢"}) == "Schiff"

scene = Image.new("RGB", (1080, 1920), (200, 180, 140))
out = tempfile.mkdtemp()
for spec, size in ((long_spec, (1280, 720)), (short, (1080, 1920))):
    for v in "AB":
        img = thumbnail.render(spec, v, scene)
        assert img.size == size, img.size
        p = thumbnail.save(img, os.path.join(out, f"{spec['slug']}-{v}.jpg"))
        assert os.path.getsize(p) < 2 * 1024 * 1024
    assert thumbnail.render(spec, "A", None).size == size, "ohne Szenenbild geht es mit Farbverlauf"

assert thumbnail.VARIANTS == learn.THUMBS
assert learn.choose_thumb({}, 0) == learn.THUMBS[0] and learn.choose_thumb({"thumbnail": {learn.THUMBS[0]: {"videos": 1, "score": 1}}}, 1) == learn.THUMBS[1]
assert learn.features(long_spec, {"thumbnail": learn.THUMBS[1]})["thumbnail"] == learn.THUMBS[1]


class Resp:
    status = 403


class Err(Exception):
    resp = Resp()


assert yt.thumb_not_allowed(Err("The authenticated user doesn't have permissions to upload and set custom video thumbnails"))
assert not yt.thumb_not_allowed(RuntimeError("timeout"))
print("ok: Thumbnails")
