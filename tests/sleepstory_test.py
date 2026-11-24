"""Einschlaf-Geschichten: Auswahl (nie doppelt), Länge, Titel und Tags (Quiet Corner)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import entspannung
import sleepstory

ss = sleepstory.stories()
assert ss and all(s["id"] and s["title"] and len(s["text"].split()) > 500 for s in ss)
assert len({s["id"] for s in ss}) == len(ss)                                   # keine doppelte ID
assert sleepstory.pick([]) == ss[0]
assert sleepstory.pick([ss[0]["id"]]) is None or sleepstory.pick([ss[0]["id"]])["id"] != ss[0]["id"]
assert sleepstory.pick([s["id"] for s in ss]) is None                          # alle gelaufen: kein Doppel
# Länge: Geschichte + 12 s + mind. 10 Min Szene, auf volle Stunden aufgerundet
assert sleepstory.total_minutes(600) == 60
assert sleepstory.total_minutes(2900) == 60
assert sleepstory.total_minutes(3000) == 120
assert sleepstory.total_minutes(10 * 3600) == 660
for s in ss:
    assert s.get("scene", "regenzimmer") in entspannung.SCENES
    for idea in entspannung.IDEAS:
        m = entspannung.story_meta(s, idea["id"], 120, 1)
        assert len(m["title"]) <= 100 and "Sleep Story" in m["title"] and "2 Hours" in m["title"], m["title"]
        assert sum(len(t) + 3 for t in m["tags"]) <= 500
        assert "synthetic voice" in m["description"] and len(m["thumb_text"].split()) <= 3
print("ok sleepstory")
