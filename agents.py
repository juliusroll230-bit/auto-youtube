"""Die Agenten der Shorts-Zentrale: jede Aufgabe der App als eigene Station mit Einstellungen.

Kein Agent ist ausgedacht, jeder steht für einen echten Teil der App:
  planer     Das Gehirn: Lernmodus, wählt Thema und Reihenfolge (learn.py)
  autor      Writers' Room: holt die neuen Skripte aus dem Repo (täglich schreibt Claude 6 neue)
  sprecher   Stimme: liest das Skript vor (Piper, make_short.synthesize)
  studio     Video-Studio: baut das Video, Untertitel-Stil, Übergang, Kopfzeile (make_short.Scene)
  clipper    Video-Clipper: schneidet lange Videos zu Shorts mit Untertiteln und Hook (clips.py)
  publisher  Lädt zu den Sendezeiten auf YouTube hoch
  analyst    Holt Aufrufe, Likes und Abonnenten
  zuschauer  Holt aus YouTube Analytics, wo Zuschauer abschalten
  designer   Setzt Banner, Kanalbeschreibung und Stichwörter (branding.py)

Die Einstellungen liegen in config.json unter "agents".
"""
import datetime as dt

BASE_SPEED = 0.88  # wie make_short.SPEED; Sprechtempo 100 % entspricht diesem Wert

DEFAULTS = {
    "planer": {"on": True, "explore_every": 4},
    "autor": {"on": True, "hours": 2},
    "sprecher": {"tempo": 100},
    "studio": {"kopfzeile": "auto", "untertitel": "auto"},
    "clipper": {"on": True, "auto_start": False, "clips": 5, "min_len": 20, "max_len": 45, "crop": "auto",
                "untertitel": "pop", "hook": True, "keywords": "", "sprache": "de", "modell": "base",
                "freigabe": True},
    "publisher": {"on": True, "clips_per_day": 2},
    "analyst": {"minutes": 20},
    "zuschauer": {"hours": 3},
    "designer": {"on": True},
}
# (kleinster Wert, größter Wert, Schritt)
RANGES = {
    ("planer", "explore_every"): (2, 10, 1),
    ("autor", "hours"): (1, 12, 1),
    ("sprecher", "tempo"): (85, 115, 1),
    ("analyst", "minutes"): (10, 120, 5),
    ("zuschauer", "hours"): (1, 12, 1),
    ("clipper", "clips"): (1, 10, 1),
    ("clipper", "min_len"): (10, 60, 5),
    ("clipper", "max_len"): (15, 90, 5),
    ("publisher", "clips_per_day"): (0, 6, 1),
}
CHOICES = {
    ("studio", "kopfzeile"): ("auto", "mit", "ohne"),
    ("studio", "untertitel"): ("auto", "kasten", "unterstrich", "pop"),
    ("clipper", "crop"): ("auto", "mitte", "rahmen"),
    ("clipper", "untertitel"): ("pop", "kasten", "unterstrich"),
    ("clipper", "sprache"): ("de", "en", "auto"),
    ("clipper", "modell"): ("base", "small"),
}
# Freitext (höchstens so viele Zeichen)
TEXTS = {("clipper", "keywords"): 200}

INFO = {
    "planer": ("Das Gehirn", "Lernmodus",
               "Entscheidet, welches Video als Nächstes kommt. Themen und Looks, die mehr Aufrufe bringen und "
               "länger angesehen werden, kommen öfter dran. Jedes N-te Video testet etwas anderes."),
    "autor": ("Writers' Room", "Skripte",
              "Jeden Morgen um 5:44 Uhr schreibt Claude 6 neue Skripte. Der Writers' Room holt sie regelmäßig "
              "ab und legt sie in die Warteschlange."),
    "sprecher": ("Sprecher", "Stimme",
                 "Liest jedes Skript mit der KI-Stimme vor. Musik und Effekte kommen automatisch dazu, "
                 "die Lautstärke passt zum YouTube-Standard."),
    "studio": ("Video-Studio", "Schnitt und Grafik",
               "Baut aus Stimme, Hintergrund, Untertiteln und Grafiken das fertige Video. Untertitel-Stil, "
               "Übergang und Kopfzeile wählt es nach Erfolg, außer du legst sie hier fest."),
    "clipper": ("Video-Clipper", "Clipping",
                "Nimmt lange Videos aus dem Eingang (Ordner, Upload oder Webhook), schreibt mit, was gesagt wird, "
                "und schneidet die stärksten Stellen zu Shorts: 9:16, Untertitel Wort für Wort, Hook-Text oben. "
                "Fertige Clips warten in der Freigabe-Station."),
    "publisher": ("Publisher", "Upload",
                  "Lädt zu den Sendezeiten das nächste Video auf YouTube hoch, KI-Shorts und freigegebene Clips "
                  "verteilt über den Tag. Ausgeschaltet wird nichts gepostet."),
    "analyst": ("Analyst", "Statistiken",
                "Holt Aufrufe, Likes, Kommentare und Abonnenten von YouTube. Daraus entstehen die Diagramme "
                "und die Werte für den Lernmodus."),
    "zuschauer": ("Research", "Zuschauer-Daten",
                  "Holt aus YouTube Analytics, wie lange Zuschauer dranbleiben und bei welchem Satz sie abschalten."),
    "designer": ("Designer", "Kanal-Design",
                 "Setzt Banner, Kanalbeschreibung und Stichwörter auf YouTube und hält sie aktuell."),
}
ORDER = ["planer", "autor", "sprecher", "studio", "clipper", "publisher", "analyst", "zuschauer", "designer"]


def settings(cfg):
    saved = cfg.get("agents") or {}
    return {a: {**DEFAULTS[a], **{k: v for k, v in (saved.get(a) or {}).items() if k in DEFAULTS[a]}}
            for a in ORDER}


def validate(agent, changes):
    """Prüft neue Einstellungen eines Agenten und gibt die bereinigten Werte zurück."""
    if agent not in DEFAULTS or not isinstance(changes, dict):
        raise ValueError("Unbekannter Agent.")
    out = {}
    for key, value in changes.items():
        if key not in DEFAULTS[agent]:
            raise ValueError(f"Unbekannte Einstellung: {key}")
        if (agent, key) in RANGES:
            lo, hi, _ = RANGES[(agent, key)]
            try:
                value = int(round(float(value)))
            except (TypeError, ValueError):
                raise ValueError("Bitte eine Zahl angeben.")
            out[key] = max(lo, min(hi, value))
        elif (agent, key) in CHOICES:
            if value not in CHOICES[(agent, key)]:
                raise ValueError("Ungültige Auswahl.")
            out[key] = value
        elif (agent, key) in TEXTS:
            value = " ".join(str(value or "").split())
            if len(value) > TEXTS[(agent, key)]:
                raise ValueError(f"Bitte höchstens {TEXTS[(agent, key)]} Zeichen.")
            out[key] = value
        else:
            out[key] = bool(value)
    return out


def voice_speed(ag):
    """Sprechtempo in Prozent als length_scale für Piper (kleiner = schneller)."""
    return round(BASE_SPEED * 100 / ag["sprecher"]["tempo"], 3)


def apply_look(look, ag):
    """Feste Vorgaben aus dem Video-Studio überschreiben den gelernten Look."""
    look = dict(look)
    st = ag["studio"]
    if st["kopfzeile"] != "auto":
        look["kopfzeile"] = st["kopfzeile"]
    if st["untertitel"] != "auto":
        look["caption_style"] = st["untertitel"]
    return look


def _iso(t):
    return t.isoformat(timespec="seconds") if t else None


def overview(cfg, runs, ctx):
    """Alle Agenten für die Website: Status, Kennzahlen, Einstellungen, nächster Lauf.

    runs: {agent: {"at": iso, "count": n, "error": text|None}}
    ctx:  connected, analytics, working (Menge der Agenten, die gerade arbeiten), queue, posted, favorite,
          next_slot (datetime|None), now (datetime), repo (bool), branding_at,
          tasks ({agent: was er gerade tut}), clips (clips.summary()["totals"])
    """
    ag = settings(cfg)
    now = ctx["now"]
    out = []
    for a in ORDER:
        name, role, desc = INFO[a]
        run = runs.get(a) or {}
        last = dt.datetime.fromisoformat(run["at"]) if run.get("at") else None
        s = ag[a]
        on = s.get("on", True)
        needs = {"publisher": ctx["connected"], "analyst": ctx["connected"], "designer": ctx["connected"],
                 "zuschauer": ctx["analytics"], "autor": ctx["repo"]}.get(a, True)
        nxt, metrics = None, []
        if a == "planer":
            metrics = [("Lieblingsthema", ctx["favorite"] or "noch in der Testphase"),
                       ("Test", f"jedes {s['explore_every']}. Video")]
        elif a == "autor":
            nxt = last + dt.timedelta(hours=s["hours"]) if last else now
            metrics = [("In der Warteschlange", f"{ctx['queue']} Skripte"), ("Abholen", f"alle {s['hours']} Std.")]
        elif a == "sprecher":
            metrics = [("Sprechtempo", f"{s['tempo']} %"), ("Stimme", "Thorsten (Piper)")]
        elif a == "studio":
            nice = {"auto": "lernt selbst", "mit": "immer", "ohne": "nie"}
            metrics = [("Kopfzeile", nice[s["kopfzeile"]]),
                       ("Untertitel", "lernt selbst" if s["untertitel"] == "auto" else s["untertitel"].capitalize())]
        elif a == "publisher":
            nxt = ctx["next_slot"] if on else None
            metrics = [("Sendezeiten", ", ".join(f"{h} Uhr" for h in cfg["post_hours"])),
                       ("Gepostet", f"{ctx['posted']} Videos"),
                       ("Clips pro Tag", f"bis zu {s['clips_per_day']}" if s["clips_per_day"] else "keine")]
        elif a == "analyst":
            nxt = last + dt.timedelta(minutes=s["minutes"]) if last else now
            metrics = [("Abfrage", f"alle {s['minutes']} Min.")]
        elif a == "zuschauer":
            nxt = last + dt.timedelta(hours=s["hours"]) if last else now
            metrics = [("Abfrage", f"alle {s['hours']} Std.")]
        elif a == "designer":
            when = dt.datetime.fromisoformat(ctx["branding_at"]).strftime("%d.%m., %H:%M Uhr") if ctx["branding_at"] else "noch nie"
            metrics = [("Zuletzt gesetzt", when)]
        elif a == "clipper":
            ct = ctx.get("clips") or {}
            metrics = [("Aktive Kampagnen", str(ct.get("active", 0))), ("Clips erstellt", str(ct.get("clips", 0))),
                       ("Warten auf Freigabe", str(ct.get("waiting", 0))),
                       ("Im Eingang", f"{ct.get('inbox', 0)} Videos")]
        if a in ctx["working"]:
            state = "arbeitet"
        elif not on:
            state = "aus"
        elif not needs:
            state = "wartet"
        elif run.get("error"):
            state = "fehler"
        else:
            state = "aktiv"
        if nxt and nxt < now:
            nxt = now
        out.append({
            "id": a, "name": name, "role": role, "desc": desc, "state": state,
            "task": (ctx.get("tasks") or {}).get(a) or None,
            "settings": s, "last_run": run.get("at"), "next_run": _iso(nxt) if state in ("aktiv", "fehler") else None,
            "tasks": max(run.get("count", 0), ctx["posted"]) if a == "publisher" else run.get("count", 0),
            "error": run.get("error"),
            "metrics": [{"label": k, "value": v} for k, v in metrics],
            "can_run": a in ("autor", "publisher", "analyst", "zuschauer", "designer", "sprecher", "studio", "clipper")
                       and needs,
        })
    return out
