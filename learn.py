"""Lernmodus: Themen, die bei den Zuschauern gut ankommen, kommen öfter dran.

Jedes Video bekommt einen Wert: seine Aufrufe, hochgerechnet auf die ersten 3 Tage
(da sammeln Shorts die meisten Aufrufe). Sind Zuschauer-Daten verbunden, zählt auch, wie lange
die Leute dranbleiben: Videos, die zu mehr als 80 % angesehen werden, zählen mehr, andere weniger. Ein Thema zählt als bewertet, sobald es
mindestens MIN_VIDEOS bewertete Videos hat. Dann gilt:

- 3 von 4 Videos kommen aus dem Thema mit dem besten Durchschnitt.
- Jedes 4. Video testet ein anderes Thema, damit neue Gewinner auffallen können.

Solange nichts bewertet ist (Testphase), wechseln sich die Themen gleichmäßig ab.
"""
import datetime as dt

MIN_AGE_H = 6       # jüngere Videos haben noch zu wenig Aufrufe für eine Aussage
FULL_AGE_H = 72     # Hochrechnung auf die ersten 3 Tage
MIN_VIDEOS = 2      # so viele bewertete Videos braucht ein Thema, bevor es bevorzugt wird
EXPLORE_EVERY = 4   # jedes 4. Video testet ein anderes Thema


RETENTION_REF = 80.0   # Ø angesehen in %, ab dem ein Video mehr zählt


def video_score(views, age_h, avg_pct=None):
    """Aufrufe, hochgerechnet auf 3 Tage, gewichtet mit der Zuschauerbindung (falls bekannt).

    Unter einem Tag wird nicht weiter hochgerechnet.
    """
    score = views * FULL_AGE_H / min(max(age_h, 24), FULL_AGE_H)
    if avg_pct:
        score *= min(1.5, max(0.5, avg_pct / RETENTION_REF))
    return score


def niche_scores(posted, now):
    """posted: Liste von {"niche", "views", "posted_at"}. Gibt je Thema Durchschnitt und Anzahl zurück."""
    sums = {}
    for v in posted:
        if v.get("views") is None or not v.get("niche") or not v.get("posted_at"):
            continue
        age_h = (now - dt.datetime.fromisoformat(v["posted_at"])).total_seconds() / 3600
        if age_h < MIN_AGE_H:
            continue
        total, n, pct, pn = sums.get(v["niche"], (0.0, 0, 0.0, 0))
        has = bool(v.get("avg_pct"))
        sums[v["niche"]] = (total + video_score(v["views"], age_h, v.get("avg_pct")), n + 1,
                            pct + (v["avg_pct"] if has else 0), pn + has)
    return {niche: {"score": total / n, "videos": n, "avg_pct": (pct / pn) if pn else None}
            for niche, (total, n, pct, pn) in sums.items()}


def favorite(scores):
    """Das beste bewertete Thema, oder None, solange es noch kein klares Signal gibt."""
    rated = {n: s["score"] for n, s in scores.items() if s["videos"] >= MIN_VIDEOS}
    if not rated or max(rated.values()) <= 0:
        return None
    return max(rated, key=rated.get)


BLOCK_WINDOW = 15  # über so viele Shorts wird der Anteil Blockwelt gehalten (ein Tag = 15 Sendeplätze)


def is_block(spec):
    return spec.get("welt") == "block"


def plan(queue, history, scores, explore_every=EXPLORE_EVERY, worlds=None, block_share=None):
    """Sortiert die Warteschlange in die Reihenfolge, in der gepostet wird.

    queue:   Liste von (datei, skript) in Dateireihenfolge
    history: Themen der bisherigen Uploads, älteste zuerst
    worlds:  Look der letzten Shorts (True = Blockwelt), älteste zuerst
    block_share: Anteil Blockwelt (z. B. 5/15). Dann ist jedes Video, das den Anteil sonst unterschreiten würde,
                 ein Blockwelt-Video, die übrigen Strichmännchen. Innerhalb des Looks wählt der Lernmodus das Thema.
    """
    remaining = list(queue)
    last = {niche: i for i, niche in enumerate(history)}
    best = favorite(scores) if scores is not None else None
    step, order = len(history), []
    window = list(worlds or [])[-(BLOCK_WINDOW - 1):]
    while remaining:
        pool = remaining
        if block_share:
            want = sum(window) < block_share * (len(window) + 1) - 1e-9
            pool = [x for x in remaining if is_block(x[1]) == want] or remaining
        if scores is None:  # Lernmodus aus: innerhalb des Looks einfach Dateireihenfolge
            item = pool[0]
            remaining.remove(item)
            order.append(item)
            window = (window + [is_block(item[1])])[-(BLOCK_WINDOW - 1):]
            continue
        niches = list(dict.fromkeys(spec["niche"] for _, spec in pool))
        explore = best not in niches or step % explore_every == explore_every - 1
        if explore:
            # das Thema, das am längsten nicht dran war (nie gepostete zuerst)
            pick = min(niches, key=lambda n: (last.get(n, -1), niches.index(n)))
        else:
            pick = best
        item = next(x for x in pool if x[1]["niche"] == pick)
        remaining.remove(item)
        order.append(item)
        window = (window + [is_block(item[1])])[-(BLOCK_WINDOW - 1):]
        last[pick] = step
        step += 1
    return order


def summary(scores, explore_every=EXPLORE_EVERY):
    best = favorite(scores)
    ranked = sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)
    return {
        "favorite": best,
        "min_videos": MIN_VIDEOS,
        "explore_every": explore_every,
        "niches": [{"niche": n, "score": round(s["score"]), "videos": s["videos"],
                    "avg_pct": round(s["avg_pct"], 1) if s.get("avg_pct") else None} for n, s in ranked],
    }


# --- Was im Video am besten funktioniert -------------------------------------
# Neben dem Thema lernt die App auch den Look: Untertitel-Stil und Übergang werden wie die Themen
# gewählt (3 von 4 Videos bekommen den besten, jedes 4. testet einen anderen), ebenso die Kopfzeile. Länge, Einstieg und
# Grafik kommen aus den Skripten; die Website zeigt, was davon am besten läuft.

CAPTION_STYLES = ("kasten", "unterstrich", "pop")       # wie motion.Caption.STYLES
TRANSITIONS = ("blitz", "wischen", "zoom", "glitch")   # wie make_short.Scene.TRANSITIONS
HEADLINES = ("mit", "ohne")                             # Titel als Kopfzeile oben im Bild
BACKGROUNDS = ("clips", "animation")                   # echte Pexels-Clips (stock.py) oder gezeichnet
# Cartoons: Stimme (wie make_short.VOICES), je nach Stimmung passen nur manche
# "warm": ruhige, freundliche Geschichten (seit 16.11.2026 Test); "freundlich" testet auch bei Erklärvideos mit.
VOICES_FOR_MOOD = {"gruselig": ("unheimlich", "erzaehler"), "mysterioes": ("erzaehler", "unheimlich"),
                   "neugierig": ("aufgeregt", "froehlich", "klar", "freundlich"),
                   "warm": ("freundlich", "erzaehlerin", "erzaehler")}
FEATURE_NAMES = {"typ": "Video-Typ", "hook": "Hook-Prüfung", "caption_style": "Untertitel", "transition": "Übergang", "kopfzeile": "Kopfzeile", "laenge": "Länge",
                 "einstieg": "Erster Satz", "grafik": "Grafik", "hintergrund": "Hintergrund",
                 "stil": "Video-Art", "stimmung": "Stimmung", "stimme": "Stimme", "serie": "Serie",
                 "thumbnail": "Thumbnail (Shorts)", "welt": "Look 2D/3D",
                 "welt_typ": "Look je Video-Typ", "ende": "Ende (Loop)",
                 "effekte": "Soundeffekte", "aufbau": "Spannung (Herzschlag)",
                 "tempo": "Tempo (schnell)", "abo": "Abo-Aufruf", "abo_text": "Abo-Aufruf (Satz)",
                 "aktuell": "Aktuelles Thema"}
# stark: Riser, Schlag, Musikpause und Bild-Stoß auf der Auflösung; voll: dazu Ton + Zoom auf Schlüsselwörtern,
# langsamer Kamera-Zug und Reaktions-Sticker; dezent: wie vorher. Alles selbst erzeugt (Test seit 19.11.2026).
EFFECTS = ("stark", "voll", "dezent")
THUMBS = ("A: Wort + Satz", "B: Satz im Kasten")       # wie thumbnail.VARIANTS
# Spannung (Test seit 20.11.2026): 1 von 15 Cartoon-Shorts bekommt einen leisen Herzschlag, der schneller wird,
# und einen Countdown bis zur Auflösung. Kein Split-Screen in den Shorts (Julius, 20.11.2026).
LAYOUTS = ("normal", "spannung")
LAYOUT_CYCLE = 15                     # ein Tag = 15 Sendeplätze
LAYOUT_SLOTS = {7: "spannung"}        # Platz im 15er-Kreis -> Variante
LAYOUT_BONUS = (2, 12)                # liegt die Variante klar vorn, bekommt sie diese Plätze dazu
LAYOUT_MIN = 5                        # so viele bewertete Videos je Seite, bevor eine Variante mehr bekommt
LAYOUT_LEAD = 1.3                     # ... und mindestens 30 % vorne
# Tempo (Test seit 21.11.2026, Julius' Vorbild-Reels): 2 von 15 Cartoon-Shorts "schnell" mit Schnitt alle ca. 1,3 s
# (wechselnde Einstellung, Stoß-Zoom, Snap-Ton), etwas flotterer Stimme, großen Wort-Untertiteln und Fortschrittsbalken.
TEMPOS = ("normal", "schnell")
TEMPO_SLOTS = {3: "schnell", 11: "schnell"}   # Plätze im 15er-Kreis (Spannung liegt auf 7)
TEMPO_BONUS = (0, 5, 9, 13)                   # läuft "schnell" klar besser, bekommt es diese Plätze dazu


# Abo-Aufruf (Test seit 22.11.2026, Julius will mehr Abos): kurzer Satz am Ende des Shorts, ca. 2 s.
# "gesprochen": die Stimme sagt ihn nach dem letzten Satz, dazu ein Abo-Knopf im Bild. "eingeblendet": nur der Knopf
# im Bild während des letzten Satzes (für Loop-Shorts, da würde ein gesprochener Satz den Loop zerstören). "ohne": Gegentest.
# Gelernt wird nach neuen Abos pro 1.000 Aufrufe (YouTube Analytics "subscribersGained").
ABO_MODES = ("gesprochen", "eingeblendet", "ohne")
ABO_LOOP = ("eingeblendet", "ohne")
ABO_MIN = 5          # so viele Videos mit Abo-Zahlen je Variante, bevor der Lernmodus die beste nimmt
# Sätze je Video-Typ, reihum, damit nicht jedes Video gleich endet. Kurz (bis 6 Wörter), ehrlich (es kommt
# wirklich jede Stunde ein neues Video), keine Floskeln, keine Gedankenstriche, nichts versprechen, was es nicht gibt.
ABO_LINES = {
    "Erklärvideo": ("Folge für die nächste Frage.", "Mehr solche Fragen? Folge uns.",
                    "Abonnier für mehr davon.", "Die nächste Frage kommt gleich. Folge uns."),
    "Mystery": ("Folge für das nächste Rätsel.", "Noch ein Rätsel? Abonnier.",
                "Das nächste Rätsel kommt gleich. Folge uns."),
    "Horror": ("Folge, wenn du dich traust.", "Noch eine Geschichte? Abonnier.",
               "Folge für die nächste Gruselgeschichte."),
    "Erzählte Geschichte": ("Folge für die nächste Geschichte.", "Mehr Geschichten? Folge uns."),
}


def abo_lines(spec):
    """Die passenden Abo-Sätze für den Video-Typ (Erklärvideos teilen sich eine Liste)."""
    typ = video_type(spec)
    return ABO_LINES["Erklärvideo" if typ.startswith("Erklär") else typ if typ in ABO_LINES else "Mystery"]


def abo_ok(spec):
    """Nur Cartoon-Shorts bekommen den Abo-Aufruf (keine langen Videos, nicht das Firmen-Spiel mit eigenem Aufruf)."""
    return spec.get("stil") == "cartoon" and spec.get("laenge") != "lang" and spec.get("format") != "firma"


def choose_abo(n, fscores, loop=False):
    """Abo-Aufruf für den n-ten Cartoon-Short: erst reihum (fairer Test), danach 3 von 4 die Variante
    mit den meisten neuen Abos pro 1.000 Aufrufe, jedes 4. Video testet reihum weiter."""
    opts = ABO_LOOP if loop else ABO_MODES
    vals = fscores.get("abo", {})
    rated = {o: vals[o]["abo_1k"] for o in opts
             if o in vals and vals[o].get("sn", 0) >= ABO_MIN and vals[o].get("abo_1k") is not None}
    if len(rated) == len(opts) and n % EXPLORE_EVERY != EXPLORE_EVERY - 1:
        return max(rated, key=rated.get)
    return opts[n % len(opts)]


def default_look(spec):
    """Der Look, den make_short ohne Vorgabe gewählt hätte (gleicher Zufall wie dort)."""
    import random
    rng = random.Random(sum(map(ord, spec["slug"])) * 7919)
    style = rng.choice(CAPTION_STYLES)
    # Videos von vor der Kopfzeile hatten keine
    return {"caption_style": style, "transition": rng.choice(TRANSITIONS), "kopfzeile": "ohne", "hintergrund": "animation"}


def cartoon_mood(spec):
    """Stimmung eines Cartoons: aus dem Skript, sonst Horror gruselig und alles andere mysteriös."""
    if spec.get("stimmung") in VOICES_FOR_MOOD:
        return spec["stimmung"]
    if str(spec.get("niche", "")).lower() == "erzählung":
        return "warm"
    return "gruselig" if str(spec.get("niche", "")).lower() == "horror" else "mysterioes"


def video_type(spec):
    """Grobe Art des Videos, damit die Zentrale Erklärvideos, Mystery, Horror, Serien und normale Shorts vergleicht."""
    niche = str(spec.get("niche", "")).lower()
    title = str(spec.get("title", "")).lower()
    if spec.get("serie") or "(teil " in title:
        return "Serie"
    if niche.startswith("erkl"):
        return "Erklärvideo: Was passiert, wenn" if title.startswith("was passiert") else "Erklärvideo: Warum/Rätsel"
    if niche == "mystery":
        return "Mystery"
    if niche == "horror":
        return "Horror"
    if niche == "erzählung":   # nicht "Geschichte": so heißt die alte Nische für echte Geschichte (History)
        return "Erzählte Geschichte"   # ausgedachte Ich-Geschichte mit Wendung, warme Stimme (Test seit 16.11.2026)
    if spec.get("stil") == "cartoon":
        return "Mystery"  # alte Cartoons wie die Tanzwut
    return "Normal (Fakten)"


def world(spec):
    """Look der Cartoons: Blockwelt in 3D ("welt": "block") oder Strichmännchen in 2D. Für den Vergleich in der Zentrale."""
    if spec.get("stil") != "cartoon" or spec.get("laenge") == "lang":
        return None
    return "Blockwelt 3D" if spec.get("welt") == "block" else "Strichmännchen 2D"


def world_by_type(spec):
    """Look und Video-Typ zusammen (z. B. "Horror · 3D"). Fairer Vergleich, weil Erklärvideos sonst den 2D-Schnitt heben."""
    w = world(spec)
    if not w:
        return None
    typ = video_type(spec).replace("Erklärvideo: ", "Erklär: ")
    return f"{typ} · {'3D' if w.startswith('Blockwelt') else '2D'}"


def _hook_bucket(spec):
    """Note der Hook-Prüfliste als Gruppe (stark/gut/schwach), damit man sieht, ob die Prüfung trifft."""
    try:
        import hookcheck
        return hookcheck.bucket(hookcheck.check(spec)["score"])
    except Exception:  # noqa: BLE001  ein seltsames altes Skript soll das Lernen nicht stoppen
        return None


def ending(spec):
    """Schluss eines Shorts: "Loop" (letzter Satz führt in den ersten zurück, Test seit 19.11.2026) oder "normal".

    Lange Videos und Videos von vor dem Test bekommen nichts, damit der Vergleich nur neue Shorts enthält.
    """
    if spec.get("laenge") == "lang" or spec.get("stil") != "cartoon":
        return None
    return "Loop" if str(spec.get("ende", "")).lower() == "loop" else "normal"


def features(spec, look):
    words = [len(s["text"].split()) for s in spec.get("segments", [])]
    total, hook = sum(words), (words[0] if words else 0)
    kinds = [str((s.get("visual") or {}).get("type", "")).lower() for s in spec.get("segments", [])]
    kinds = [k for k in kinds if k]
    return {
        "typ": video_type(spec),
        "hook": _hook_bucket(spec),
        "caption_style": look.get("caption_style"),
        "transition": look.get("transition"),
        "kopfzeile": look.get("kopfzeile") or "ohne",
        "hintergrund": look.get("hintergrund") or "animation",
        "laenge": "kurz (bis 60 Wörter)" if total <= 60 else "mittel (61 bis 75)" if total <= 75 else "lang (über 75)",
        "einstieg": "kurz (bis 8 Wörter)" if hook <= 8 else "mittel (9 bis 12)" if hook <= 12 else "lang (über 12)",
        "grafik": kinds[0] if kinds else "keine",
        "stil": "Cartoon" if spec.get("stil") == "cartoon" else "Normal",
        "stimmung": cartoon_mood(spec) if spec.get("stil") == "cartoon" else None,
        "stimme": look.get("stimme") if spec.get("stil") == "cartoon" else None,
        "serie": spec.get("serie") or None,
        "thumbnail": look.get("thumbnail"),   # nur gesetzt, wenn YouTube das eigene Thumbnail angenommen hat
        "welt": world(spec),
        "welt_typ": world_by_type(spec),
        "ende": ending(spec),
        "effekte": look.get("effekte") if spec.get("stil") == "cartoon" else None,
        "aufbau": look.get("aufbau") if spec.get("stil") == "cartoon" else None,
        "tempo": look.get("tempo") if spec.get("stil") == "cartoon" else None,
        "aktuell": ("aktuell" if spec.get("aktuell") else "zeitlos") if spec.get("stil") == "cartoon" and spec.get("laenge") != "lang" else None,
        "abo": look.get("abo") if abo_ok(spec) else None,   # nur neue Shorts haben den Wert, alte zählen nicht mit
        "abo_text": look.get("abo_text") if abo_ok(spec) and look.get("abo") in ("gesprochen", "eingeblendet") else None,
    }


def feature_scores(posted, now):
    """Je Merkmal und Wert: Durchschnitt der Video-Werte, Anzahl und Ø angesehen."""
    out = {}
    for v in posted:
        if v.get("views") is None or not v.get("features") or not v.get("posted_at"):
            continue
        age_h = (now - dt.datetime.fromisoformat(v["posted_at"])).total_seconds() / 3600
        if age_h < MIN_AGE_H:
            continue
        score = video_score(v["views"], age_h, v.get("avg_pct"))
        for name, value in v["features"].items():
            if value is None:
                continue
            e = out.setdefault(name, {}).setdefault(value, {"total": 0.0, "videos": 0, "pct": 0.0, "pn": 0,
                                                             "subs": 0, "sviews": 0, "sn": 0})
            e["total"] += score
            e["videos"] += 1
            if v.get("avg_pct"):
                e["pct"] += v["avg_pct"]
                e["pn"] += 1
            if v.get("subs_gained") is not None and v.get("a_views"):   # neue Abos durch dieses Video (YouTube Analytics)
                e["subs"] += v["subs_gained"]
                e["sviews"] += v["a_views"]
                e["sn"] += 1
    return {name: {val: {"score": e["total"] / e["videos"], "videos": e["videos"],
                         "avg_pct": e["pct"] / e["pn"] if e["pn"] else None,
                         "abo_1k": 1000 * e["subs"] / e["sviews"] if e["sviews"] else None, "sn": e["sn"]}
                   for val, e in vals.items()}
            for name, vals in out.items()}


def choose(options, scores, step):
    """Bester Wert (3 von 4 Mal) oder ein Test: der am wenigsten genutzte Wert."""
    rated = {o: scores[o]["score"] for o in options if o in scores and scores[o]["videos"] >= MIN_VIDEOS}
    if rated and len(rated) == len(options) and step % EXPLORE_EVERY != EXPLORE_EVERY - 1:
        return max(rated, key=rated.get)
    return min(options, key=lambda o: (scores.get(o, {}).get("videos", 0), options.index(o)))


def choose_look(fscores, step):
    return {"caption_style": choose(CAPTION_STYLES, fscores.get("caption_style", {}), step),
            "transition": choose(TRANSITIONS, fscores.get("transition", {}), step + 1),
            "kopfzeile": choose(HEADLINES, fscores.get("kopfzeile", {}), step + 2),
            "hintergrund": choose(BACKGROUNDS, fscores.get("hintergrund", {}), step + 3)}


def choose_voice(fscores, step, spec):
    """Stimme für ein Cartoon: die beste passende (3 von 4 Mal) oder ein Test der anderen."""
    return choose(VOICES_FOR_MOOD[cartoon_mood(spec)], fscores.get("stimme", {}), step)


def choose_effects(fscores, step):
    """Soundeffekte für einen Cartoon-Short: die bessere Stufe (3 von 4 Mal) oder ein Test der anderen."""
    return choose(EFFECTS, fscores.get("effekte", {}), step)


def layout_winner(fscores, name="aufbau"):
    """Die Variante, die klar besser läuft als normale Shorts (mind. LAYOUT_MIN Videos je Seite, 30 % vorn), sonst None."""
    vals = fscores.get(name, {})
    base = vals.get("normal")
    if not base or base["videos"] < LAYOUT_MIN or base["score"] <= 0:
        return None
    good = {k: v["score"] for k, v in vals.items()
            if k != "normal" and v["videos"] >= LAYOUT_MIN and v["score"] >= base["score"] * LAYOUT_LEAD}
    return max(good, key=good.get) if good else None


def choose_layout(n, fscores):
    """Für den n-ten Cartoon-Short: fest 1 "spannung" pro 15 (Test), sonst "normal".

    Läuft Spannung nach genug Videos klar besser, bekommt sie 2 Plätze mehr pro 15.
    """
    pos = n % LAYOUT_CYCLE
    if pos in LAYOUT_SLOTS:
        return LAYOUT_SLOTS[pos]
    win = layout_winner(fscores)
    return win if win and pos in LAYOUT_BONUS else "normal"


def choose_tempo(n, fscores):
    """Für den n-ten Cartoon-Short: fest 2 "schnell" pro 15 (Test), sonst "normal".

    Liegt "schnell" nach mind. 5 Videos je Seite 30 % vorn, bekommt es 4 Plätze mehr pro 15.
    """
    pos = n % LAYOUT_CYCLE
    if pos in TEMPO_SLOTS:
        return TEMPO_SLOTS[pos]
    win = layout_winner(fscores, "tempo")
    return win if win and pos in TEMPO_BONUS else "normal"


def choose_thumb(fscores, step):
    """Thumbnail-Variante: die bessere (3 von 4 Mal) oder ein Test der anderen."""
    return choose(THUMBS, fscores.get("thumbnail", {}), step)


def feature_summary(fscores):
    rows = []
    for name, label in FEATURE_NAMES.items():
        vals = fscores.get(name, {})
        if name in ("abo", "abo_text"):   # beim Abo-Aufruf zählen neue Abos pro 1.000 Aufrufe, nicht die Aufrufe
            ranked = sorted(vals.items(), key=lambda kv: (kv[1].get("abo_1k") is not None, kv[1].get("abo_1k") or 0,
                                                          kv[1]["score"]), reverse=True)
        else:
            ranked = sorted(vals.items(), key=lambda kv: kv[1]["score"], reverse=True)
        rows.append({"key": name, "label": label,
                     "values": [{"value": v, "score": round(s["score"]), "videos": s["videos"],
                                 "avg_pct": round(s["avg_pct"], 1) if s["avg_pct"] else None,
                                 "abo_1k": round(s["abo_1k"], 2) if s.get("abo_1k") is not None else None}
                                for v, s in ranked]})
    return rows
