"""Mehr Videos am Stück und mehr Kommentare (seit 26.11.2026, Julius' Wunsch).

1. Geschichten-Playlist: Die App legt auf dem Hauptkanal eine öffentliche Playlist „Ruhige Geschichten zum Zuhören“
   an, fügt jede erzählte Geschichte (Nische „Erzählung“) nach dem Upload hinzu und schiebt einmal am Tag die
   meistgesehenen nach oben. Wer eine Geschichte mag, findet so die nächste. Ehrlich: Es gibt keine Serien und
   darum auch kein „Teil 2“-Versprechen (CLAUDE.md). Links in Shorts-Beschreibungen kann man seit 2023 nicht
   anklicken, darum zeigt die App die Playlist auf der Kanalseite (Kanal-Abschnitt) und nennt sie im Frage-Kommentar.
2. Frage-Kommentar: Kurz nach jedem Upload schreibt der Kanal selbst einen Kommentar mit einer Frage an die Zuschauer
   („Was hättest du an meiner Stelle gemacht?“). Eigene Frage im Skript: Feld "frage". Anpinnen geht über die
   YouTube-Schnittstelle nicht (nur in YouTube Studio von Hand). Antworten darauf laufen wie immer über comments.py.
3. Gewinner nachbauen: winners() nennt die meistgesehenen Shorts je Video-Typ. Die tägliche Skript-Aufgabe baut
   2 bis 3 neue Skripte mit demselben Aufbau (Feld "nachbau", Lernmerkmal „Gewinner-Nachbau“), siehe CLAUDE.md.

Daten in binge.json. Kommentar schreiben braucht youtube.force-ssl (zweiter Zugang, wie comments.py),
die Playlist geht mit dem normalen Upload-Zugang.
"""
import datetime as dt
import re

import store

FILE = "binge.json"
DEFAULTS = {"fragen": True, "playlist": True}
PLAYLIST_TITLE = "Ruhige Geschichten zum Zuhören"
PLAYLIST_DESC = ("Ausgedachte Alltagsgeschichten, ruhig erzählt. Jede Geschichte ist für sich abgeschlossen. "
                 "Die meistgesehenen stehen oben.")
STORY = "Erzählte Geschichte"
ASK_AFTER_MIN = 3        # YouTube braucht kurz, bis das Video Kommentare annimmt
ASK_WITHIN_H = 36        # ältere Uploads bekommen keine Frage mehr
MAX_ASK_PER_RUN = 3
MAX_ADD_PER_RUN = 10     # beim ersten Mal nicht alle alten Geschichten auf einmal (API-Quote)
TOP_ORDER = 5            # so viele meistgesehene Geschichten stehen oben in der Playlist
KEEP_ASKED = 400
MIN_AGE_H = 20           # Gewinner erst, wenn das Video ca. einen Tag Aufrufe gesammelt hat

# Fragen je Video-Typ: kurz, ehrlich, ohne Link, ohne „Abonnier“, höchstens ein Emoji. Reihum, damit nichts gleich klingt.
QUESTIONS = {
    STORY: ["Was hättest du an meiner Stelle gemacht?", "Hast du so etwas auch schon mal erlebt?",
            "Wer hat dir schon mal heimlich geholfen? 🥹", "Ab welchem Satz hast du die Wendung geahnt?",
            "Wem würdest du diese Geschichte erzählen?"],
    "Horror": ["Wärst du geblieben oder sofort weggelaufen? 👻", "Was hättest du als Erstes gemacht?",
               "Ab welchem Moment wurde es dir unheimlich?", "Hättest du die Tür aufgemacht?"],
    "Mystery": ["Was glaubst du, was wirklich passiert ist?", "Welche Erklärung hältst du für am wahrscheinlichsten?",
                "Kanntest du den Fall schon?", "Was hättest du als Ermittler zuerst geprüft? 🤔"],
    "Erklärvideo": ["Wusstest du das schon?", "Ist dir das auch schon mal passiert?",
                    "Hättest du die Antwort gewusst? 🤯", "Was sollen wir als Nächstes erklären?"],
    "": ["Wusstest du das schon?", "Was sollen wir als Nächstes zeigen?"],
}
PLAYLIST_HINT = "Mehr ruhige Geschichten findest du in der Playlist „" + PLAYLIST_TITLE + "“ auf dem Kanal."
LINK = re.compile(r"https?://|www\.|\.(com|de|net|org|ly|io)\b", re.I)


def load():
    d = store.read(FILE, {}) or {}
    out = {"settings": {**DEFAULTS, **d.get("settings", {})}, "asked": d.get("asked", {}),
           "playlist": d.get("playlist", {}), "status": d.get("status", {}), "step": int(d.get("step", 0)),
           "since": d.get("since")}
    if not out["since"]:   # nur Uploads ab dem Einschalten bekommen eine Frage, nicht rückwirkend alle
        out["since"] = store.now().isoformat(timespec="seconds")
    out["playlist"].setdefault("items", {})
    return out


def save(d):
    if len(d["asked"]) > KEEP_ASKED:
        keep = sorted(d["asked"].items(), key=lambda kv: kv[1].get("at", ""))[-KEEP_ASKED:]
        d["asked"] = dict(keep)
    store.write(FILE, d)


def set_settings(fragen=None, playlist=None):
    with store.LOCK:
        d = load()
        if fragen is not None:
            d["settings"]["fragen"] = bool(fragen)
        if playlist is not None:
            d["settings"]["playlist"] = bool(playlist)
        save(d)
        return d["settings"]


def _group(vtype):
    if vtype.startswith("Erklärvideo"):
        return "Erklärvideo"
    return vtype if vtype in QUESTIONS else ""


def clean_question(text):
    """Eigene Frage aus dem Skript: eine Zeile, ohne Link und Gedankenstriche, höchstens 150 Zeichen. Sonst None."""
    t = " ".join(str(text or "").split())
    t = re.sub(r"\s*[–—]\s*", ", ", t).strip(" ,")
    if not t or LINK.search(t) or re.search(r"abonnier", t, re.I) or len(t) > 150:
        return None
    return t


def question(spec, vtype, step, playlist=False):
    """Die Frage für ein Video: aus dem Skript (Feld "frage") oder reihum aus QUESTIONS je Video-Typ."""
    own = clean_question(spec.get("frage"))
    if own:
        text = own
    else:
        options = QUESTIONS[_group(vtype)]
        text = options[step % len(options)]
    if playlist and vtype == STORY:
        text += "\n\n" + PLAYLIST_HINT
    return text


def wants_question(spec, upload):
    """Nur eigene Videos des Hauptkanals, nicht das Firmen-Spiel (da sammeln die Kommentare Wunschjobs)."""
    return upload.get("channel") != "clips" and spec.get("format") != "firma" and bool(upload.get("video_id"))


def pending_questions(d, uploads, specs, now=None):
    """Uploads, die jetzt eine Frage bekommen sollen: [(upload, spec)], älteste zuerst, höchstens MAX_ASK_PER_RUN."""
    now = now or store.now()
    early = (now - dt.timedelta(minutes=ASK_AFTER_MIN)).isoformat()
    late = (now - dt.timedelta(hours=ASK_WITHIN_H)).isoformat()
    since = d.get("since") or now.isoformat()
    out = []
    for u in sorted(uploads, key=lambda x: x.get("posted_at", "")):
        at = u.get("posted_at", "")
        if not at or at > early or at < late or at < since or u.get("video_id") in d["asked"]:
            continue
        spec = specs.get(u.get("slug"))
        if spec is None or not wants_question(spec, u):
            continue
        out.append((u, spec))
    return out[:MAX_ASK_PER_RUN]


def story_ids(uploads, specs):
    """video_ids aller erzählten Geschichten (Shorts) des Hauptkanals, älteste zuerst."""
    import learn
    out = []
    for u in sorted(uploads, key=lambda x: x.get("posted_at", "")):
        spec = specs.get(u.get("slug"))
        if spec and u.get("channel") != "clips" and not u.get("lang") and u.get("video_id") \
                and learn.video_type(spec) == STORY:
            out.append(u["video_id"])
    return out


def wanted_order(ids, views):
    """Meistgesehene zuerst (die oberen TOP_ORDER Plätze), dahinter der Rest in Upload-Reihenfolge."""
    top = sorted(ids, key=lambda i: (-int(views.get(i, 0)), ids.index(i)))[:TOP_ORDER]
    return top + [i for i in ids if i not in top]


def winners(uploads, specs, views, now=None, per_type=1, days=45):
    """Meistgesehene Shorts je Video-Typ (für „Gewinner nachbauen“): [{title, slug, type, views}], beste zuerst."""
    import learn
    now = now or store.now()
    old = (now - dt.timedelta(hours=MIN_AGE_H)).isoformat()
    start = (now - dt.timedelta(days=days)).isoformat()
    best = {}
    for u in uploads:
        spec = specs.get(u.get("slug"))
        at = u.get("posted_at", "")
        if not spec or u.get("lang") or u.get("channel") == "clips" or spec.get("format") == "firma" \
                or not (start <= at <= old):
            continue
        row = {"title": u.get("title", ""), "slug": u.get("slug"), "type": learn.video_type(spec),
               "views": int(views.get(u.get("video_id"), 0)), "video_id": u.get("video_id")}
        best.setdefault(row["type"], []).append(row)
    out = []
    for rows in best.values():
        out += sorted(rows, key=lambda r: -r["views"])[:per_type]
    return sorted((r for r in out if r["views"]), key=lambda r: -r["views"])


def nachbau(spec):
    """Lernmerkmal: wurde das Skript nach dem Aufbau eines Gewinners gebaut? (nur Shorts)"""
    if spec.get("laenge") == "lang" or spec.get("format") == "firma":
        return None
    return "Gewinner nachgebaut" if spec.get("nachbau") else "eigener Aufbau"


def overview(cfg, uploads=None, specs=None, views=None):
    d = load()
    pl = d["playlist"]
    asked = sorted(d["asked"].values(), key=lambda a: a.get("at", ""), reverse=True)
    today = store.now().date().isoformat()
    out = {"settings": d["settings"], "status": d["status"],
           "playlist": {"id": pl.get("id"), "count": len(pl.get("items", {})), "section": bool(pl.get("section")),
                        "url": "https://www.youtube.com/playlist?list=" + pl["id"] if pl.get("id") else None,
                        "ordered_at": pl.get("ordered_at")},
           "asked_today": sum(1 for a in asked if a.get("at", "")[:10] == today), "asked_total": len(asked),
           "asked": asked[:10],
           "can_ask": bool(cfg.get("analytics_token") and "youtube.force-ssl" in cfg.get("analytics_scopes", ""))}
    if uploads is not None:
        out["winners"] = winners(uploads, specs or {}, views or {})[:5]
    return out


def posted_specs():
    """slug → Skript aller hochgeladenen Videos (aus posted/)."""
    import glob
    import json
    import os
    out = {}
    for f in glob.glob(store.path("posted", "*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                spec = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(spec, dict):
            out[spec.get("slug") or os.path.basename(f)[5:-5]] = spec
    return out
