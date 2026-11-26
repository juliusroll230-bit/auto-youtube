"""Einreich-Station für Content-Rewards-Clips.

Sobald der Publisher einen Clip einer Whop-Kampagne (Feld "program" der Clipper-Kampagne) auf YouTube gepostet hat,
steht er hier bereit. Julius reicht ihn mit einem Klick selbst ein: Die Zentrale kopiert den Shorts-Link und öffnet
die Kampagnenseite. Abschicken macht er dort von Hand.

Bewusst NICHT automatisch: Content Rewards erlaubt keine Bots als Teilnehmer und hat für Clipper keine offizielle
Schnittstelle zum Einreichen. Darum keine Browser-Automatisierung und keine inoffizielle API.

Gespeichert wird je Clip in einreichen.json (über store, unter store.LOCK):
    {"since": "<iso>", "clips": {"<kampagne>/<n>": {"eingereicht_at": "<iso>" | null, "skip": bool}}}
"""
import datetime as dt

import clips
import store
import whop

FILE = "einreichen.json"
LATE_MIN = 120   # länger offen: Karte wird orange


def key(cid, n):
    return f"{cid}/{int(n)}"


def _load():
    data = store.read(FILE, {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("clips", {})
    return data


def since():
    """Seit wann es die Station gibt. Ältere Clips ohne Eintrag zählen nicht als offen (die wurden vorher von Hand eingereicht)."""
    with store.LOCK:
        data = _load()
        if not data.get("since"):
            data["since"] = store.now().isoformat(timespec="seconds")
            store.write(FILE, data)
        return data["since"]


def _clip(cid, n):
    try:
        c = clips.load(cid)
    except (OSError, ValueError):
        raise ValueError("Unbekannte Kampagne.")
    clip = next((x for x in c.get("clips", []) if x.get("n") == n), None)
    if not clip:
        raise ValueError("Unbekannter Clip.")
    if clip.get("status") != "gepostet" or not clip.get("video_id"):
        raise ValueError("Der Clip ist noch nicht auf YouTube.")
    if not c.get("program") or not whop.find(c["program"]):
        raise ValueError("Der Clip gehört zu keiner Whop-Kampagne.")
    return c, clip


def _set(cid, n, **changes):
    try:
        n = int(n)
    except (TypeError, ValueError):
        raise ValueError("Unbekannter Clip.")
    c, clip = _clip(cid, n)
    with store.LOCK:
        data = _load()
        entry = {"eingereicht_at": None, "skip": False, **(data["clips"].get(key(cid, n)) or {}), **changes}
        data["clips"][key(cid, n)] = entry
        store.write(FILE, data)
    return c, clip, entry


def submit(cid, n):
    """Julius hat auf „Einreichen“ geklickt: Link ist kopiert, die Kampagne ist offen."""
    c, clip, entry = _set(cid, n, eingereicht_at=store.now().isoformat(timespec="seconds"), skip=False)
    store.log("ok", f"Clip zum Einreichen geöffnet: {clip['title']}", agent="publisher", kind="input")
    return entry


def undo(cid, n):
    """Rückgängig: wieder offen (auch nach „Nicht einreichen“)."""
    return _set(cid, n, eingereicht_at=None, skip=False)[2]


def skip(cid, n):
    """Nicht einreichen: verschwindet aus der Liste der offenen Clips."""
    return _set(cid, n, eingereicht_at=None, skip=True)[2]


def ready(c, clip):
    """Nach dem Posten (vom Publisher aufgerufen): Eintrag anlegen und im Live-Feed melden."""
    if not c.get("program") or not clip.get("video_id"):
        return False
    item = whop.find(c["program"])
    if not item:
        return False
    since()
    with store.LOCK:
        data = _load()
        data["clips"].setdefault(key(c["id"], clip["n"]), {"eingereicht_at": None, "skip": False})
        store.write(FILE, data)
    store.log("info", f"Clip bereit zum Einreichen: {clip['title']} ({item['title']})", agent="publisher", kind="submit")
    return True


def _age_min(posted_at, now):
    try:
        t = dt.datetime.fromisoformat(posted_at)
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None and now.tzinfo is not None:
        t = t.replace(tzinfo=now.tzinfo)
    return max(0, int((now - t).total_seconds() // 60))


def overview(camps=None, stats=None, now=None):
    """Für die Zentrale: alle geposteten Clips von Whop-Kampagnen mit Stand, dazu Zahlen je Kampagne."""
    camps = clips.all_campaigns() if camps is None else camps
    stats = ((store.read("stats.json", {}) or {}).get("videos") or {}) if stats is None else stats
    now = now or store.now()
    whops = {x["id"]: x for x in whop.load()}
    start = since()
    saved = _load()["clips"]
    items, per = [], {}
    for c in camps:
        w = whops.get(c.get("program") or "")
        if not w:
            continue
        for clip in c.get("clips", []):
            if clip.get("status") != "gepostet" or not clip.get("video_id"):
                continue
            e = saved.get(key(c["id"], clip["n"]))
            views = int((stats.get(clip["video_id"]) or {}).get("views") or 0)
            if e and e.get("eingereicht_at"):
                state = "eingereicht"
            elif e and e.get("skip"):
                state = "nicht"
            elif e is None and (clip.get("posted_at") or "") < start:
                state = "alt"   # vor der Einreich-Station gepostet: nicht mitzählen
            else:
                state = "offen"
            age = _age_min(clip.get("posted_at"), now)
            items.append({"id": c["id"], "n": clip["n"], "title": clip.get("title") or "Clip", "video_id": clip["video_id"],
                          "link": "https://youtube.com/shorts/" + clip["video_id"], "program": w["id"],
                          "campaign": w.get("title") or "Kampagne", "url": w.get("url"), "posted_at": clip.get("posted_at"),
                          "minutes": age, "views": views, "state": state,
                          "eingereicht_at": (e or {}).get("eingereicht_at"),
                          "late": state == "offen" and age is not None and age > LATE_MIN})
            p = per.setdefault(w["id"], {"id": w["id"], "title": w.get("title") or "Kampagne", "url": w.get("url"),
                                         "submitted": 0, "open": 0, "skipped": 0, "views": 0, "earned": 0.0, "rate": None})
            p["rate"] = next((r["rate"] for r in w.get("rates") or [] if r["platform"] == "YouTube"), None)
            if state == "eingereicht":
                p["submitted"] += 1
                p["views"] += views
                money = whop.estimate(w, views)
                if money is None:
                    p["earned"] = None
                elif p["earned"] is not None:
                    p["earned"] = round(p["earned"] + money, 2)
            elif state == "offen":
                p["open"] += 1
            elif state == "nicht":
                p["skipped"] += 1
    # offene: älteste zuerst (die eilen), danach eingereicht / nicht einreichen / alt, jeweils neueste zuerst
    order = {"offen": 0, "eingereicht": 1, "nicht": 2, "alt": 3}
    open_ = sorted([x for x in items if x["state"] == "offen"], key=lambda x: x["posted_at"] or "")
    rest = sorted([x for x in items if x["state"] != "offen"], key=lambda x: x["posted_at"] or "", reverse=True)
    rest.sort(key=lambda x: order[x["state"]])
    for p in per.values():
        if p["rate"] is None:
            p["earned"] = None
    return {"open": len(open_), "late": sum(1 for x in open_ if x["late"]), "late_min": LATE_MIN,
            "items": (open_ + rest)[:200], "campaigns": list(per.values()),
            "submitted": sum(p["submitted"] for p in per.values())}
