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
print("ok")
