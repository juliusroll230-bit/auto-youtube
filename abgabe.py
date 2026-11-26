"""Plätze ab Nr. X an Clipi abgeben (Phase D, seit 26.11.2026, Julius' Wunsch).

Uploads ab dem ca. 11. am Tag bekommen auf dem Hauptkanal kaum Aufrufe (Auswertung 20. bis 22.11.).
Darum gibt der Publisher diese Sendeplätze an Clipi ab: Statt eines KI-Shorts lädt Clipi einen
freigegebenen Clip einer Content-Rewards-Kampagne hoch. Der Clip steht danach in der Einreich-Station,
absenden macht Julius selbst (keine Bots bei Content Rewards).

Reihenfolge: Wert = YouTube-Rate × Restbudget der Kampagne. Übersprungen werden Kampagnen,
die nicht „läuft“ sind, keine YouTube-Rate haben oder weniger als 10 % Budget übrig haben, und Clips,
die gegen die Vorgaben verstoßen (Mindestlänge, Pflicht-Text, verbotene Wörter).
Gibt es keinen passenden Clip oder keinen Clip-Kanal, bleibt der Platz beim Hauptkanal.
"""
import datetime as dt
import os

import agents
import clips
import store
import whop

MIN_LEFT = 0.10        # unter 10 % Restbudget: Kampagne überspringen
COMPARE_DAYS = 14      # Vergleichskarte nach 14 Tagen
YT_RPM = (0.03, 0.07)  # ungefähres YouTube-Werbegeld für Shorts in Deutschland, € pro 1.000 Aufrufe (wie Reiter Geld)


def from_slot(cfg=None):
    """Ab welchem Sendeplatz des Tages abgegeben wird (0 = aus)."""
    return int(agents.settings(cfg or store.config())["publisher"].get("abgabe_ab") or 0)


def slot_number(cfg, key):
    """Nummer des Sendeplatzes am Tag (1 = erster), aus dem Schlüssel „JJJJ-MM-TT-HH“."""
    try:
        at = dt.datetime.strptime(key, "%Y-%m-%d-%H")
    except (TypeError, ValueError):
        return 0
    hours = sorted(int(h) for h in store.hours_for(cfg, at) or [])
    return hours.index(at.hour) + 1 if at.hour in hours else 0


def youtube_rate(camp):
    return next((r["rate"] for r in camp.get("rates") or [] if r.get("platform") == "YouTube"), None)


def budget_left(camp):
    """(übrig, Anteil übrig) oder (None, None), wenn die Kampagnenseite kein Budget zeigt."""
    total, used = camp.get("budget_total"), camp.get("budget_used")
    if total is None or used is None or total <= 0:
        return None, None
    left = max(0.0, total - used)
    return left, left / total


def camp_problem(camp):
    """Warum eine Kampagne gerade keine Plätze bekommt (None = passt)."""
    if not camp:
        return "Kampagne nicht mehr verknüpft"
    if camp.get("status") != "läuft":
        return "Kampagne läuft nicht" + (f" ({camp['status']})" if camp.get("status") else "")
    if not youtube_rate(camp):
        return "keine YouTube-Rate"
    _, share = budget_left(camp)
    if share is not None and share < MIN_LEFT:
        return "weniger als 10 % Budget übrig"
    if camp.get("rules") is None:
        return "Vorgaben fehlen (Kampagnen > ⋯ > Vorgaben)"
    return None


def clip_problem(c, clip, camp):
    """Prüft einen Clip gegen die Vorgaben der Kampagne (None = passt)."""
    rules = camp.get("rules") or {}
    if rules.get("min_len") and (clip.get("duration") or 0) + 0.05 < rules["min_len"]:
        return f"kürzer als {rules['min_len']} s"
    spec = clips.upload_spec(c, clip)
    if (rules.get("caption") or "").strip() and rules["caption"].strip() not in spec["description"]:
        return "Pflicht-Text fehlt"
    for text in (spec["title"], spec["description"], clip.get("title"), clip.get("text")):
        hit = clips.banned_hit(text, rules.get("banned"))
        if hit:
            return f"verbotenes Wort „{hit}“"
    return None


def value(camp):
    """Wert = YouTube-Rate × Restbudget. Ohne Budget-Angabe zählt nur die Rate (dann hinter allen mit Budget)."""
    left, _ = budget_left(camp)
    rate = youtube_rate(camp) or 0
    return (1, rate * left) if left is not None else (0, rate)


def candidates():
    """Alle Clips, die auf einem abgegebenen Platz laufen dürfen, bester zuerst. Dazu die Gründe für den Rest."""
    camps = {x["id"]: x for x in whop.load()}
    ok, skipped = [], {}
    for c in clips.all_campaigns():
        pid = c.get("program")
        if not pid:
            continue
        waiting = [k for k in c.get("clips", []) if k.get("status") == "freigegeben"
                   and os.path.exists(clips.clip_path(c, k))]
        if not waiting:
            continue
        camp = camps.get(pid)
        why = camp_problem(camp)
        name = (camp or {}).get("title") or c.get("name") or "Kampagne"
        if why:
            skipped[name] = why
            continue
        for k in waiting:
            bad = clip_problem(c, k, camp)
            if bad:
                skipped[f"{name}: {k.get('title') or 'Clip ' + str(k['n'])}"] = bad
                continue
            ok.append((value(camp), -(k.get("n") or 0), c, k, camp))
    ok.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [(c, k, camp) for _, _, c, k, camp in ok], skipped


def choose(slot, cfg=None):
    """Clip für diesen Sendeplatz, wenn er abgegeben wird. Sonst None (Platz bleibt beim Hauptkanal)."""
    cfg = cfg or store.config()
    x = from_slot(cfg)
    if not x or not cfg.get("clip_token") or slot_number(cfg, slot) < x:
        return None
    found, _ = candidates()
    return found[0] if found else None


def record_extra(cfg, slot):
    return {"abgabe": True, "slot_nr": slot_number(cfg, slot)}


# --- Anzeige in der Zentrale ---------------------------------------------------------------

def _views(stats, vid):
    return int(((stats.get(vid) or {}).get("views")) or 0) if vid else 0


def compare(cfg, uploads, stats, today=None, skip=()):
    """Vergleich nach 14 Tagen: abgegebene Plätze (Clips) gegen dieselben Plätze auf dem Hauptkanal davor."""
    today = today or store.now().date()
    mine = [u for u in uploads if u.get("abgabe")]
    if not mine:
        return None
    start = min(dt.date.fromisoformat(u["posted_at"][:10]) for u in mine)
    days = (today - start).days
    x = from_slot(cfg) or 11
    if days < COMPARE_DAYS:
        return {"ready": False, "since": start.isoformat(), "days": days, "ready_on": (start + dt.timedelta(days=COMPARE_DAYS)).isoformat()}
    before_from = start - dt.timedelta(days=COMPARE_DAYS)
    main = [u for u in uploads if u.get("kind") != "clip" and not u.get("long") and not u.get("lang") and u.get("channel") != "clips"
            and before_from.isoformat() <= str(u.get("posted_at") or "")[:10] < start.isoformat()
            and u.get("slot") not in skip and slot_number(cfg, u.get("slot")) >= x]
    camps = {c["id"]: c for c in whop.load()}
    progs = {c["id"]: c.get("program") for c in clips.all_campaigns()}
    clip_views = [_views(stats, u.get("video_id")) for u in mine]
    money = 0.0
    for u, v in zip(mine, clip_views):
        camp = camps.get(progs.get(u.get("campaign")))
        money += (whop.estimate(camp, v) or 0) if camp else 0
    main_views = [_views(stats, u.get("video_id")) for u in main]
    avg = lambda xs: round(sum(xs) / len(xs)) if xs else 0
    return {"ready": True, "since": start.isoformat(), "days": days,
            "clips": {"n": len(mine), "views": sum(clip_views), "avg": avg(clip_views), "money": round(money, 2)},
            "main": {"n": len(main), "views": sum(main_views), "avg": avg(main_views),
                     "money": [round(sum(main_views) / 1000 * r, 2) for r in YT_RPM]}}


def overview(cfg, st):
    """Für das Dashboard: Einstellung, heute abgegebene Plätze, nächster Clip, Gründe, Vergleich."""
    x = from_slot(cfg)
    today = store.now().date().isoformat()
    ups = st.get("uploads", [])
    found, skipped = candidates()
    nxt = found[0] if found else None
    hours = sorted(int(h) for h in store.hours_for(cfg, store.now()) or [])
    slots = [f"{h}:00" for i, h in enumerate(hours, 1) if x and i >= x]
    return {
        "from": x, "on": bool(x), "connected": bool(cfg.get("clip_token")),
        "today": sum(1 for u in ups if u.get("abgabe") and str(u.get("posted_at") or "")[:10] == today),
        "total": sum(1 for u in ups if u.get("abgabe")),
        "slots": slots,
        "ready": len(found),
        "next": {"title": nxt[1].get("title"), "campaign": nxt[2].get("title"), "rate": youtube_rate(nxt[2]),
                 "left": budget_left(nxt[2])[0], "currency": nxt[2].get("currency") or "$"} if nxt else None,
        "skipped": [{"what": k, "why": v} for k, v in list(skipped.items())[:6]],
        "compare": compare(cfg, ups, (store.read("stats.json", {}) or {}).get("videos") or {},
                           skip=set(st.get("firma_slots", []))),
    }
