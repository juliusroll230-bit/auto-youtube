"""Hook-Prüfliste und Humanizer."""
import copy, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tempfile
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
import hookcheck, learn, store

H = hookcheck.humanize
assert H("Das Licht — und es bewegt sich.") == "Das Licht, und es bewegt sich."
assert H("Hallo Leute! Du stehst auf der Straße.", first=True) == "Du stehst auf der Straße."
assert H("In diesem Video zeige ich dir das Rätsel. Ein Schiff treibt leer.", first=True) == "Ein Schiff treibt leer."
assert H("Ein Schiff treibt leer. Lass uns eintauchen. Niemand ist an Bord!!") == "Ein Schiff treibt leer. Niemand ist an Bord!"
assert H("Hallo", first=False) == "Hallo"

good = {"niche": "Erklären", "stil": "cartoon", "title": "Was passiert, wenn du nicht schläfst?",
        "segments": [{"text": "Du bleibst wach, und plötzlich siehst du Dinge.",
                      "szene": {"typ": "figur", "aktion": "zittert", "objekt": "😵"}}]
        + [{"text": "eins zwei drei vier fünf sechs sieben acht neun zehn", "szene": {}}] * 6}
r = hookcheck.check(good)
assert r["score"] == 8, r

bad = copy.deepcopy(good)
bad["segments"][0] = {"text": "Hallo Leute, heute erkläre ich euch etwas sehr Faszinierendes über den Schlaf und seine Geheimnisse.",
                      "szene": {"typ": "figur", "aktion": "steht"}}
r = hookcheck.check(bad)
assert r["score"] <= 4, r
assert len(r["tips"]) == r["max"] - r["score"]

spec, changed = hookcheck.clean(copy.deepcopy(bad))
assert changed and not spec["segments"][0]["text"].lower().startswith("hallo")

assert learn.features(good, {})["hook"] == "stark (8 von 8)"
assert "hook" in learn.FEATURE_NAMES

# alle echten Skripte lassen sich prüfen und bereinigen, ohne dass Text verloren geht
for f in glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "*.json")):
    s = json.load(open(f, encoding="utf-8"))
    hookcheck.check(s)
    c, _ = hookcheck.clean(copy.deepcopy(s))
    assert all(seg.get("text") for seg in c["segments"]), f
# neue Skripte werden beim Einlesen bereinigt, die Warteschlange zeigt die Note
store.init()
raw = copy.deepcopy(good)
raw["slug"] = "test-hook"
raw["segments"][0]["text"] = "Du bleibst wach — und plötzlich siehst du Dinge."
assert store.add_scripts({"9999-test-hook.json": json.dumps(raw, ensure_ascii=False)}) == 1
q = store.load_spec(store.path("queue", "9999-test-hook.json"))
assert q["segments"][0]["text"] == "Du bleibst wach, und plötzlich siehst du Dinge.", q["segments"][0]["text"]
assert store.card(q)["hook_check"]["score"] == 8
print("ok")

# --- unslop: Titel, Beschreibung, Thumbnail-Text -------------------------------------
P = hookcheck.polish
assert P("Hallo Leute!! Das Rätsel vom Pass 😱🔥👀.", "title") == "Das Rätsel vom Pass 😱"
assert P("Dieser Autogigant trägt den Namen eines Schweizers 🇨🇭", "title") == "Dieser Autogigant trägt den Namen eines Schweizers 🇨🇭"
assert P("Was geschah 1959–1960 wirklich?", "title") == "Was geschah 1959–1960 wirklich?"
assert P("Er lügt dich an — wirklich", "line") == "Er lügt dich an wirklich"
assert P("Willkommen zurück! Ein Zelt im Schnee – von innen aufgeschnitten.\n\n#mystery #shorts", "description") \
    == "Ein Zelt im Schnee, von innen aufgeschnitten.\n\n#mystery #shorts"
tips = hookcheck.text_tips({"title": "Du wirst nicht glauben, was 99 % der Menschen falsch machen!!! 😱🔥",
                            "description": "Hallo Leute, hier ist es", "thumb_text": ["Menschen | falsch machen"]})
assert len(tips) == 6, tips
assert [t for t in hookcheck.text_tips(good) if "Zwischen-Haken" not in t] == []
assert "Füllwort" in hookcheck.tells({"segments": [{"text": "Heutzutage spielt das darüber hinaus keine Rolle."}]})
s2, ch = hookcheck.clean({"title": "Das Rätsel — gelöst!!", "description": "Hey Leute! Ein Schiff treibt leer.",
                          "thumb_text": ["Schiff | treibt leer.", "Niemand an Bord!!"], "segments": [{"text": "Ein Schiff."}]})
assert ch and s2["title"] == "Das Rätsel, gelöst!" and s2["description"] == "Ein Schiff treibt leer."
assert s2["thumb_text"] == ["Schiff | treibt leer", "Niemand an Bord!"], s2["thumb_text"]
# alle echten Skripte: Titel bleiben gleich, keine Text-Tipps
for f in glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed", "*.json")):
    s = json.load(open(f, encoding="utf-8"))
    c, _ = hookcheck.clean(copy.deepcopy(s))
    assert c.get("title") == s.get("title"), (f, c.get("title"))
print("unslop ok")
