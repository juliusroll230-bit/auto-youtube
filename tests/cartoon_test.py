"""Baut ein kurzes Cartoon-Video mit jedem Szenentyp und prüft, dass ein echtes Video herauskommt."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cartoon  # noqa: E402
import make_short  # noqa: E402

TYPES = [
    {"typ": "figur", "ort": "stadt", "gefuehl": "freude", "aktion": "winkt", "objekt": "🚗", "text": "Hallo"},
    {"typ": "zwei", "ort": "schule", "tafel": "2 + 2", "zweite": {"farbe": "gelb", "hut": "krone"}},
    {"typ": "gruppe", "ort": "burg", "anzahl": 5, "aktion": "jubelt"},
    {"typ": "objekt", "objekt": "🦈", "text": "Hai"},
    {"typ": "zahl", "zahl": 700, "einheit": "Meter", "objekt": "🌉"},
    {"typ": "jahr", "jahr": "1347", "text": "Pest", "stempel": "wahr"},
    {"typ": "liste", "text": "Plan", "punkte": ["Eins", "Zwei", "Drei"]},
    {"typ": "vergleich", "links": {"objekt": "🐘", "text": "Elefant"}, "rechts": {"objekt": "🐭", "text": "Maus"}},
    {"typ": "horror", "ort": "keller", "aktion": "zittert", "objekt": "👻", "text": "Wer ist da"},
    {"typ": "akte", "text": "Was geschah?", "punkte": ["🛶", "Brief", "🧭"]},
    {"typ": "raetsel", "ort": "meer", "objekt": "🚢", "text": "Ungelöst"},
    {"typ": "karte", "objekt": "💎", "text": "Atlantik"},
]
spec = {
    "slug": "cartoon-test", "stil": "cartoon", "title": "Test", "stimmung": "mysterioes", "stimme": "unheimlich", "figur": {"farbe": "rot", "hut": "zylinder"},
    "segments": [{"text": f"Das ist Szene Nummer {i + 1}.", "szene": s} for i, s in enumerate(TYPES)],
}
assert not cartoon.validate(spec), cartoon.validate(spec)
out = "/tmp/cartoon-test"
shots = cartoon.stills(spec, [i * 2.2 + 1 for i in range(len(TYPES))], out)
assert all(os.path.getsize(p) > 30000 for p in shots), "Einzelbild leer"
path, dur, _ = make_short.build_video(spec, out, make_short.load_tts())
assert os.path.getsize(path) > 300000, "Video zu klein"
assert dur > 10, dur
make_short.render_thumbnail(spec, os.path.join(out, "thumb.jpg"))
print("ok", path, round(dur, 1), "Sekunden")
