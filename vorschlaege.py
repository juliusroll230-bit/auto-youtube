"""Kampagnen-Vorschläge aus der öffentlichen Content-Rewards-Übersicht (Phase F, seit 26.11.2026, Julius' Wunsch).

Gelesen wird nur, was jeder ohne Anmeldung sieht: die Übersicht der Clipping-Kampagnen
(contentrewards.com/c/discover/clipping) und die Seite einer Kampagne. Vor jedem Lauf prüft die Zentrale
robots.txt; verbietet sie die Seiten, wird nichts gelesen. Alle 6 Stunden, höchstens 8 Kampagnenseiten pro
Lauf, mit Pause dazwischen.

Ein Vorschlag muss passen:
- Shorts erlaubt (YouTube-Rate vorhanden) und mindestens 1 $ pro 1.000 Aufrufe auf YouTube,
- weniger als 50 % des Budgets verbraucht, Kampagne nimmt Clips an,
- Material gestellt (Kampagne stellt Dateien bereit),
- kein Pflicht-Anteil an US-Publikum (unser Publikum ist deutsch; SEGA ist daran gescheitert).
Deutsche Kampagnen und unsere Nischen (Gaming, Wissen, Mystery, Geschichten) stehen oben.

Nie automatisch beitreten oder einreichen: „Verknüpfen“ legt die Kampagne nur in der Zentrale an
(whop.add), beitreten macht Julius selbst auf Content Rewards.
"""
import html
import json
import re
import time
import urllib.robotparser

import store
import whop

BASE = "https://contentrewards.com"
OVERVIEW = BASE + "/c/discover/clipping"
FILE = "vorschlaege.json"
EVERY_HOURS = 6
MAX_DETAILS = 8
MIN_RATE = 1.0
MAX_USED = 0.5
PUSH_RATE = 2.0
GERMAN = re.compile(r"\b(german|germany|deutsch|deutschland|dach|austria|österreich|schweiz|switzerland)\b", re.I)
NICHES = re.compile(r"\b(gaming|game|games|minecraft|roblox|world of warcraft|wow|blizzard|science|facts?|wissen|mystery|horror|story|stories|"
                    r"history|space|nature|education|explainer)\b", re.I)
US_ONLY = re.compile(r"\b\d{2,3}\s?%\+?\s*(?:of\s+)?(?:us|u\.s\.|usa|united states|us/ca|us & ca)\b|\bus[- ]only\b|\bus audience\b", re.I)


def _money(s):
    """„$1.6K“ → 1600, „$12.4K“ → 12400, „$2.50“ → 2.5."""
    s = (s or "").replace("$", "").replace(",", "").replace("⁦", "").replace("⁩", "").strip()
    mult = 1
    if s[-1:].upper() in ("K", "M"):
        mult = 1000 if s[-1].upper() == "K" else 1_000_000
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def _text(page):
    t = re.sub(r"(?is)<(script|style|svg|noscript)\b.*?</\1>", " ", page)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = html.unescape(t).replace("⁦", "").replace("⁩", "")
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t)


def parse_overview(page):
    """Kampagnen aus der Übersicht: Name und Link aus den strukturierten Daten der Seite (JSON-LD),
    Budget und Rate aus der Karte darunter. Ohne JSON-LD gilt die Seite als nicht lesbar."""
    items = []
    for block in re.findall(r'(?is)<script type="application/ld\+json">(.*?)</script>', page):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for node in data.get("@graph", [data]) if isinstance(data, dict) else []:
            if node.get("@type") == "ItemList":
                for li in node.get("itemListElement") or []:
                    m = whop.URL_RE.search(li.get("url") or "")
                    if m and li.get("name"):
                        items.append({"id": m.group(1).lower(), "title": " ".join(html.unescape(li["name"]).split())[:120],
                                      "url": BASE + "/c/campaigns/" + m.group(1).lower()})
    if not items:
        raise ValueError("Die Übersicht ist nicht lesbar (keine Kampagnenliste gefunden).")
    text = _text(page)
    pos = 0
    for i, it in enumerate(items):
        at = text.find(it["title"], pos)
        if at < 0:
            continue
        nxt = text.find(items[i + 1]["title"], at + len(it["title"])) if i + 1 < len(items) else -1
        seg = text[at + len(it["title"]): nxt if nxt > 0 else at + 600]
        pos = at + len(it["title"])
        bud = re.search(r"(\$[\d.,]+[KM]?)\s*/\s*(\$[\d.,]+[KM]?)", seg)
        rate = re.search(r"\$([\d.,]+)(?:\s*[–-]\s*\$([\d.,]+))?\s*/1K", seg)
        if bud:
            it["used"], it["total"] = _money(bud.group(1)), _money(bud.group(2))
        if rate:
            it["rate_min"] = _money(rate.group(1))
            it["rate_max"] = _money(rate.group(2)) if rate.group(2) else it["rate_min"]
    return items


def parse_detail(page):
    """Angaben der Kampagnenseite (wie whop.parse) plus Material, US-Pflicht und Sprache/Nische."""
    info = whop.parse(page)
    text = whop._text(page)
    mat = re.search(r"Reference materials\s*(\d+)\s*files?", text, re.I)
    info["materials"] = int(mat.group(1)) if mat else 0
    info["us_only"] = bool(US_ONLY.search(text))
    info["german"] = bool(GERMAN.search(info.get("title", "") + " " + text[:3000]))
    info["niche"] = bool(NICHES.search(info.get("title", "") + " " + info.get("about", "") + " " + text[:3000]))
    return info


def youtube_rate(x):
    return next((r["rate"] for r in x.get("rates") or [] if r.get("platform") == "YouTube"), None)


def overview_ok(it):
    if (it.get("rate_max") or 0) < MIN_RATE:
        return False
    if it.get("total") and it.get("used") is not None and it["used"] / it["total"] >= MAX_USED:
        return False
    return True


def detail_problem(info):
    yr = youtube_rate(info)
    if yr is None:
        return "keine Shorts (YouTube nicht dabei)"
    if yr < MIN_RATE:
        return f"nur ${yr:.2f} pro 1.000 auf YouTube"
    if info.get("status") and info["status"] != "läuft":
        return "nimmt keine Clips an"
    if info.get("budget_total") and info.get("budget_used") is not None and info["budget_used"] / info["budget_total"] >= MAX_USED:
        return "über 50 % Budget verbraucht"
    if not info.get("materials"):
        return "kein Material gestellt"
    if info.get("us_only"):
        return "verlangt US-Publikum"
    return None


def allowed(get_robots=None):
    """robots.txt erlaubt Übersicht und Kampagnenseiten?"""
    rp = urllib.robotparser.RobotFileParser()
    rp.parse((get_robots or (lambda: whop.fetch(BASE + "/robots.txt")))().splitlines())
    return rp.can_fetch("*", OVERVIEW) and rp.can_fetch("*", BASE + "/c/campaigns/x")


def load():
    d = store.read(FILE, {}) or {}
    return {"items": [], "hidden": [], "notified": [], "checked_at": None, "error": None, **d}


def _save(d):
    with store.LOCK:
        store.write(FILE, d)


def refresh(get=None, get_robots=None, sleep=time.sleep, alert=None):
    """Holt neue Vorschläge. get(url) → HTML (Standard whop.fetch). Gibt die gespeicherten Daten zurück."""
    get = get or whop.fetch
    d = load()
    d["checked_at"] = store.now().isoformat(timespec="seconds")
    try:
        if not allowed(get_robots):
            d.update(error="robots.txt erlaubt das Lesen gerade nicht. Es werden keine Vorschläge geholt.", items=[])
            _save(d)
            return d
        over = parse_overview(get(OVERVIEW))
    except Exception as e:  # noqa: BLE001  (Netz weg oder Seite umgebaut: alte Vorschläge bleiben)
        d["error"] = str(e) if isinstance(e, ValueError) else "Content Rewards war gerade nicht erreichbar."
        _save(d)
        return d
    linked = {x["id"] for x in whop.load()}
    skip = linked | set(d["hidden"])
    pre = [it for it in over if it["id"] not in skip and overview_ok(it)]
    pre.sort(key=lambda it: (bool(GERMAN.search(it["title"])), bool(NICHES.search(it["title"])), it.get("rate_max") or 0), reverse=True)
    out, checked = [], 0
    for it in pre[:MAX_DETAILS]:
        if checked:
            sleep(2)   # höflich: eine Seite nach der anderen
        checked += 1
        try:
            info = parse_detail(get(it["url"]))
        except Exception:  # noqa: BLE001
            continue
        why = detail_problem(info)
        if why:
            continue
        used, total = info.get("budget_used"), info.get("budget_total")
        out.append({"id": it["id"], "url": it["url"], "title": info.get("title") or it["title"], "brand": info.get("brand", ""),
                    "about": info.get("about", "")[:240], "rate": youtube_rate(info), "currency": info.get("currency") or "$",
                    "budget_used": used, "budget_total": total, "left": (total - used) if total and used is not None else None,
                    "materials": info["materials"], "german": info["german"], "niche": info["niche"],
                    "found_at": next((x["found_at"] for x in d["items"] if x["id"] == it["id"]), d["checked_at"])})
    out.sort(key=lambda x: (x["german"], x["niche"], x["rate"] or 0, x["left"] or 0), reverse=True)
    for x in out:
        if (x["rate"] or 0) >= PUSH_RATE and x["id"] not in d["notified"]:
            d["notified"] = (d["notified"] + [x["id"]])[-300:]
            try:
                (alert or _push)(x)
            except Exception as e:  # noqa: BLE001
                print("Vorschlag-Push:", repr(e), flush=True)
    d.update(items=out, error=None)
    _save(d)
    return d


def _push(x):
    import push
    push.alert("camp:" + x["id"], f"Neue Kampagne: {x['title']} zahlt ${x['rate']:.2f} pro 1.000 Aufrufe auf YouTube. "
               "Ansehen unter Kampagnen > Vorschläge.", "moneybag")


def hide(pid):
    d = load()
    if pid not in d["hidden"]:
        d["hidden"] = (d["hidden"] + [pid])[-500:]
    d["items"] = [x for x in d["items"] if x["id"] != pid]
    _save(d)


def link(pid):
    """„Verknüpfen“: legt die Kampagne in der Zentrale an (whop.add). Beitreten macht Julius selbst."""
    x = next((i for i in load()["items"] if i["id"] == pid), None)
    if not x:
        raise ValueError("Diesen Vorschlag gibt es nicht mehr.")
    item = whop.add(x["url"])
    d = load()
    d["items"] = [i for i in d["items"] if i["id"] != pid]
    _save(d)
    return item


def overview():
    d = load()
    linked = {x["id"] for x in whop.load()}
    return {"items": [x for x in d["items"] if x["id"] not in linked][:12], "checked_at": d["checked_at"], "error": d["error"],
            "every_hours": EVERY_HOURS}
