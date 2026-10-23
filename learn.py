"""Lernmodus: Themen, die bei den Zuschauern gut ankommen, kommen öfter dran.

Jedes Video bekommt einen Wert: seine Aufrufe, hochgerechnet auf die ersten 3 Tage
(da sammeln Shorts die meisten Aufrufe). Ein Thema zählt als bewertet, sobald es
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


def video_score(views, age_h):
    """Aufrufe, hochgerechnet auf 3 Tage. Unter einem Tag wird nicht weiter hochgerechnet."""
    return views * FULL_AGE_H / min(max(age_h, 24), FULL_AGE_H)


def niche_scores(posted, now):
    """posted: Liste von {"niche", "views", "posted_at"}. Gibt je Thema Durchschnitt und Anzahl zurück."""
    sums = {}
    for v in posted:
        if v.get("views") is None or not v.get("niche") or not v.get("posted_at"):
            continue
        age_h = (now - dt.datetime.fromisoformat(v["posted_at"])).total_seconds() / 3600
        if age_h < MIN_AGE_H:
            continue
        total, n = sums.get(v["niche"], (0.0, 0))
        sums[v["niche"]] = (total + video_score(v["views"], age_h), n + 1)
    return {niche: {"score": total / n, "videos": n} for niche, (total, n) in sums.items()}


def favorite(scores):
    """Das beste bewertete Thema, oder None, solange es noch kein klares Signal gibt."""
    rated = {n: s["score"] for n, s in scores.items() if s["videos"] >= MIN_VIDEOS}
    if not rated or max(rated.values()) <= 0:
        return None
    return max(rated, key=rated.get)


def plan(queue, history, scores):
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
        explore = best not in niches or step % EXPLORE_EVERY == EXPLORE_EVERY - 1
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


def summary(scores):
    best = favorite(scores)
    ranked = sorted(scores.items(), key=lambda kv: kv[1]["score"], reverse=True)
    return {
        "favorite": best,
        "min_videos": MIN_VIDEOS,
        "explore_every": EXPLORE_EVERY,
        "niches": [{"niche": n, "score": round(s["score"]), "videos": s["videos"]} for n, s in ranked],
    }
