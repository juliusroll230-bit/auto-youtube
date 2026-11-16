"""Video-Typ für den Vergleich Erklärvideo / Mystery / Horror / Serie / Normal."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import learn

def t(**kw):
    return learn.video_type({"segments": [], **kw})

assert t(niche="Erklären", title="Was passiert, wenn du nicht schläfst?") == "Erklärvideo: Was passiert, wenn"
assert t(niche="Erklären", title="Das Rätsel um das Bermuda-Dreieck") == "Erklärvideo: Warum/Rätsel"
assert t(niche="Mystery", stil="cartoon", title="Das Buch, das niemand lesen kann") == "Mystery"
assert t(niche="Horror", stil="cartoon", title="Station 13: Wer? (Teil 2)") == "Serie"
assert t(niche="Horror", stil="cartoon", title="Die Insel") == "Horror"
assert t(niche="Geschichte", stil="cartoon", title="Tanzwut") == "Mystery"
assert t(niche="Business", title="Autologo") == "Normal (Fakten)"
f = learn.features({"niche": "Erklären", "title": "Was passiert, wenn X", "segments": [{"text": "a b"}]}, {})
assert f["typ"] == "Erklärvideo: Was passiert, wenn"
assert learn.world({"stil": "cartoon", "welt": "block"}) == "Blockwelt 3D"
assert learn.world({"stil": "cartoon"}) == "Strichmännchen 2D"
assert learn.world({"niche": "Geld"}) is None
assert learn.features({"stil": "cartoon", "welt": "block", "niche": "Horror", "segments": [{"text": "a"}]}, {})["welt"] == "Blockwelt 3D"
assert learn.world_by_type({"stil": "cartoon", "welt": "block", "niche": "Horror", "title": "X"}) == "Horror · 3D"
assert learn.world_by_type({"stil": "cartoon", "niche": "Erklären", "title": "Was passiert, wenn X"}) == "Erklär: Was passiert, wenn · 2D"
assert learn.world_by_type({"niche": "Geld"}) is None
# Erzählte Geschichten (Test seit 16.11.2026): eigener Typ, warme Stimmung und Stimmen
g = {"niche": "Erzählung", "stil": "cartoon", "title": "Die Nachbarin", "segments": []}
assert learn.video_type(g) == "Erzählte Geschichte"
assert learn.cartoon_mood(g) == "warm"
assert "freundlich" in learn.VOICES_FOR_MOOD["warm"] and "freundlich" in learn.VOICES_FOR_MOOD["neugierig"]
assert learn.choose_voice({}, 0, g) == "freundlich"   # noch nichts bewertet: zuerst die neue Stimme
import hookcheck, json, glob
for f in glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "02[0-9][0-9]-geschichte-*.json")):
    assert hookcheck.check(json.load(open(f, encoding="utf-8")))["score"] >= 7, f
import fishtts
v = fishtts.Voice(None, "k", "normal", "dunkel", "warm")
assert v.pick("warm") == "warm" and v.pick("neugierig", "freundlich") == "warm" and v.pick("gruselig") == "dunkel"
assert v.pick("neugierig", "klar") == "normal" and fishtts.Voice(None, "k", "normal").pick("warm") == "normal"
print("ok")
