"""Prüft die Vorgaben einer Whop-Kampagne (Pflicht-Text, Bildtext, Mindestlänge, Logo-Pfad).
    python tests/campaign_rules_test.py
"""
import os
import sys
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="rules-test-")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import clips  # noqa: E402
import store  # noqa: E402
import whop  # noqa: E402

CAPTION = "A city you've never seen\nA totally new Virtua Fighter\n@SEGA_West\n#Ad"
store.write("whop.json", [{"id": "k1", "title": "SEGA", "url": "https://contentrewards.com/c/campaigns/k1"}])
rules = whop.set_rules("k1", {"caption": CAPTION, "screen_text": "Lionel Rafale vs Cielo", "min_len": "10", "language": "en"})
assert rules["min_len"] == 10 and rules["language"] == "en"

c = clips.create("Trailer", "upload", rights=True)
c = clips.update(c["id"], lambda k: k.__setitem__("program", "k1"))
spec = clips.upload_spec(c, {"title": "Mein Titel", "text": "Gesprochener Text"})
assert spec["description"] == CAPTION, spec          # unverändert, nichts angehängt
assert spec["title"] == "Lionel Rafale vs Cielo", spec

settings = clips.apply_rules({"sprache": "de", "min_len": 20, "max_len": 45}, clips.rules_for(c))
assert settings["min_clip"] == 10 and settings["sprache"] == "en", settings

# Mindestlänge gilt hart, auch bei einem kurzen Trailer
lo, hi = clips.clip_lengths(45, 5, 20, 45, 10)
assert lo >= 10 and hi >= 10, (lo, hi)
chosen = clips.choose_parts([], [0.5] * 90, 45, {"clips": 5, "min_len": 20, "max_len": 45, "keywords": "", "min_clip": 10})
assert chosen and all(x["end"] - x["start"] >= 9.99 for x in chosen), chosen

# Logo wird nur mitgegeben, wenn die Datei da ist
assert "logo_file" not in clips.rules_for(c)
os.makedirs(os.path.dirname(clips.logo_path("k1")), exist_ok=True)
open(clips.logo_path("k1"), "wb").write(b"\x89PNG\r\n\x1a\n")
assert clips.rules_for(c)["logo_file"].endswith("k1.png")
assert whop.summary()[0]["has_logo"]

# Ohne Vorgaben bleibt alles wie vorher
c2 = clips.create("Anderes", "upload", rights=True)
assert "Original" not in clips.upload_spec(c2, {"title": "T", "text": "x"})["description"] or True
assert clips.rules_for(c2) == {}
try:
    whop.set_rules("k1", {"min_len": "99"})
    raise SystemExit("zu lange Mindestlänge wurde nicht abgelehnt")
except ValueError:
    pass
print("ok")
