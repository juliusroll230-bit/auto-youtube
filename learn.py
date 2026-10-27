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


def plan(queue, history, scores, explore_every=EXPLORE_EVERY):
    """Sortiert die Warteschlange in die Reihenfolge, in der gepostet wird.

    queue:   Liste von (datei, skript) in Dateireihenfolge
    history: Themen der bisherigen Uploads, älteste zuerst
    """
    remaining = list(queue)
    last = {niche: i for i, niche in enumerate(history)}
    best = favorite(scores)
    step, order = len(history), []
    while remaining:
        niches = list(dict.fromkeys(spec["niche"] for _, spec in remaining))
        explore = best not in niches or step % explore_every == explore_every - 1
        if explore:
            # das Thema, das am längsten nicht dran war (nie gepostete zuerst)
            pick = min(niches, key=lambda n: (last.get(n, -1), niches.index(n)))
        else:
            pick = best
        item = next(x for x in remaining if x[1]["niche"] == pick)
        remaining.remove(item)
        order.append(item)
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
FEATURE_NAMES = {"caption_style": "Untertitel", "transition": "Übergang", "kopfzeile": "Kopfzeile", "laenge": "Länge",
                 "einstieg": "Erster Satz", "grafik": "Grafik"}


def default_look(spec):
    """Der Look, den make_short ohne Vorgabe gewählt hätte (gleicher Zufall wie dort)."""
    import random
    rng = random.Random(sum(map(ord, spec["slug"])) * 7919)
    style = rng.choice(CAPTION_STYLES)
    # Videos von vor der Kopfzeile hatten keine
    return {"caption_style": style, "transition": rng.choice(TRANSITIONS), "kopfzeile": "ohne"}


def features(spec, look):
    words = [len(s["text"].split()) for s in spec.get("segments", [])]
    total, hook = sum(words), (words[0] if words else 0)
    kinds = [str((s.get("visual") or {}).get("type", "")).lower() for s in spec.get("segments", [])]
    kinds = [k for k in kinds if k]
    return {
        "caption_style": look.get("caption_style"),
        "transition": look.get("transition"),
        "kopfzeile": look.get("kopfzeile") or "ohne",
        "laenge": "kurz (bis 60 Wörter)" if total <= 60 else "mittel (61 bis 75)" if total <= 75 else "lang (über 75)",
        "einstieg": "kurz (bis 8 Wörter)" if hook <= 8 else "mittel (9 bis 12)" if hook <= 12 else "lang (über 12)",
        "grafik": kinds[0] if kinds else "keine",
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
            e = out.setdefault(name, {}).setdefault(value, {"total": 0.0, "videos": 0, "pct": 0.0, "pn": 0})
            e["total"] += score
            e["videos"] += 1
            if v.get("avg_pct"):
                e["pct"] += v["avg_pct"]
                e["pn"] += 1
    return {name: {val: {"score": e["total"] / e["videos"], "videos": e["videos"],
                         "avg_pct": e["pct"] / e["pn"] if e["pn"] else None} for val, e in vals.items()}
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
            "kopfzeile": choose(HEADLINES, fscores.get("kopfzeile", {}), step + 2)}


def feature_summary(fscores):
    rows = []
    for name, label in FEATURE_NAMES.items():
        vals = fscores.get(name, {})
        ranked = sorted(vals.items(), key=lambda kv: kv[1]["score"], reverse=True)
        rows.append({"key": name, "label": label,
                     "values": [{"value": v, "score": round(s["score"]), "videos": s["videos"],
                                 "avg_pct": round(s["avg_pct"], 1) if s["avg_pct"] else None} for v, s in ranked]})
    return rows
