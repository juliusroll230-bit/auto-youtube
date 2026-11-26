"""Nischen-Kompass: Titel-Muster, Themenfeld, Zwischen-Haken, Vielfalt, Kompass."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
import nische, learn, hookcheck

P = nische.title_pattern
assert P("Was passiert, wenn du tagelang nicht schläfst? 😵 #shorts") == "Was passiert, wenn …?"
assert P("Warum bekommst du eigentlich Gänsehaut? 🥶") == "Warum …?"
assert P("Der Schlüssel, der in kein Schloss passt 🗝️") == "Das X, das niemand …"
assert P("Die Frau im Tal, die niemand kannte 🧳") == "Das X, das niemand …"
assert P("Geh nachts nie zum Eiswagen 🍦") == "Regel/Countdown"
assert P("Schule: 60 Sekunden bis zur Glocke 🔔") == "Regel/Countdown"
assert P("3 Psychologie-Tricks, die fast niemand kennt 🧠") == "Zahl/Liste"
assert P("Welche Tür würdest du nehmen?") == "Mitmachen/Wahl"
assert P("Elon Musk hat Tesla nicht gegründet ⚡") == "Mythos/Irrtum"
assert P("Warum Mama mir zwei Brote einpackt 🥪", "Erzählung") == "Warum …?"
assert P("Der Platz neben mir im Bus 🚌", "Erzählung") == "Ich-Geschichte"
assert P("Australien ist breiter als der Mond 🌕") == "Aussage/Fakt"

T = nische.topic_field
seg = lambda t: [{"text": t}]  # noqa: E731
assert T({"niche": "Erklären", "title": "Warum zittern deine Hände?", "segments": seg("x")}) == "Körper & Sinne"
assert T({"niche": "Erklären", "title": "Merkur: Was passiert dort?", "segments": seg("x")}) == "Weltall"
assert T({"niche": "Horror", "title": "Das Kellerlicht", "segments": seg("x")}) == "Grusel (ausgedacht)"
assert T({"niche": "Mystery", "title": "Die Bagdad-Batterie", "segments": seg("x")}) == "Echte Rätsel & Geschichte"
assert T({"niche": "Erklären", "title": "Was passiert, wenn alle springen?", "segments": seg("x")}) == "Sonstiges"

base = [{"text": w} for w in ("Du hältst die Luft an.", "Dein Körper merkt das sofort.", "Kohlendioxid steigt.")]
with_hook = {"segments": base + [{"text": "Aber dann passiert etwas Seltsames."}, {"text": "Du wirst ohnmächtig."},
                                 {"text": "Und atmest wieder."}]}
without = {"segments": base + [{"text": "Das Gehirn schlägt Alarm."}, {"text": "Du wirst ohnmächtig."},
                               {"text": "Und atmest wieder."}]}
assert nische.rehook(with_hook) == "mit", nische.rehook(with_hook)
assert nische.rehook(without) == "ohne"
assert nische.rehook({**with_hook, "laenge": "lang"}) is None

# Vielfalt: 10 von 40 fangen mit „Plötzlich“ an -> Tipp; Fragen-Einstieg ist Format, kein Tipp
recent = [{"title": f"T{i}", "segments": [{"text": "Plötzlich klopft es." if i < 10 else f"Im Jahr {i} …"}]} for i in range(40)]
assert nische.sameness({"title": "Neu", "segments": [{"text": "Plötzlich geht das Licht an."}]}, recent)
assert not nische.sameness({"title": "Warum niest du?", "segments": [{"text": "Was passiert, wenn du niest?"}]},
                           [{"title": "x", "segments": [{"text": "Was passiert hier?"}]}] * 40)

# Lernen: die neuen Merkmale stehen in features() und in der Übersicht
spec = {"niche": "Erklären", "stil": "cartoon", "title": "Warum juckt eine Wunde?", "segments": with_hook["segments"]}
f = learn.features(spec, {})
assert f["themenfeld"] == "Körper & Sinne" and f["titel_muster"] == "Warum …?" and f["zwischenhaken"] == "mit", f
assert learn.features({**spec, "laenge": "lang"}, {})["themenfeld"] is None
assert {"themenfeld", "titel_muster", "zwischenhaken"} <= set(learn.FEATURE_NAMES)

# Kompass: Bester/Schwächster und ehrliche Hinweise
rows = [{"key": "themenfeld", "values": [{"value": "Körper & Sinne", "videos": 12, "rel": 1.6, "chance": 90},
                                         {"value": "Weltall", "videos": 5, "rel": 0.7, "chance": 2},
                                         {"value": "Tiere", "videos": 2, "rel": 3.0}]},
        {"key": "platz", "values": [{"value": "1. bis 5.", "videos": 20, "rel": 1.4}, {"value": "11. bis 15.", "videos": 20, "rel": 0.3}]}]
k = nische.compass(rows)
assert k["rows"][0]["best"]["value"] == "Körper & Sinne" and k["rows"][0]["worst"]["value"] == "Weltall"   # Tiere: zu wenig Videos
assert any("Körper & Sinne" in a for a in k["advice"]) and any("11 bis 15" in a for a in k["advice"]), k["advice"]
assert nische.compass([])["rows"] == []

# Öffentliche Statistik (GitHub Actions)
vids = [{"title": "Warum A? 🅰️", "views": 900}, {"title": "Warum B?", "views": 800}, {"title": "Warum C?", "views": 1000},
        {"title": "Die Tür, die niemand öffnet", "views": 200}, {"title": "Die Uhr, die steht", "views": 300},
        {"title": "Das Licht, das flackert", "views": 250}]
st = nische.public_stats(vids)
assert st["titel_muster"][0]["value"] == "Warum …?" and st["titel_muster"][0]["faktor"] > 1, st

# Hook-Prüfung gibt den Tipp zum Zwischen-Haken
long_spec = {"niche": "Erklären", "title": "Warum x?", "segments": [{"text": "eins zwei drei vier fünf sechs sieben acht neun zehn"}] * 6}
assert any("Zwischen-Haken" in t for t in hookcheck.text_tips(long_spec))
print("nische ok")
