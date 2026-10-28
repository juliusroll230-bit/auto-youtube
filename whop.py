"""Whop-Kampagnen (Content Rewards) in der Zentrale.

Whop und Content Rewards bieten Clippern keine Schnittstelle, um das ganze Konto zu verknüpfen.
Darum liest die Zentrale die öffentliche Seite einer Kampagne (dieselbe, die jeder ohne Anmeldung sieht):
Name, Geld pro 1.000 Aufrufe je Plattform, Mindest- und Höchstauszahlung, Budget und Status.
Alle paar Stunden wird nachgeschaut. Videos der Kampagne kommen über den Link (Drive/Dropbox) und
werden der Kampagne zugeordnet (Feld "program" in der Clipper-Kampagne).
"""
import html
import re
import urllib.request

import clips
import store

FILE = "whop.json"
URL_RE = re.compile(r"https?://(?:www\.)?contentrewards\.com/(?:c/)?(?:campaigns|discover)/([0-9a-fA-F-]{36})")
PLATFORMS = ("TikTok", "Instagram", "YouTube", "Facebook", "Snapchat", "Twitter", "X")
STATUS = {"active": "läuft", "live": "läuft", "paused": "pausiert", "ended": "beendet", "completed": "beendet"}
MONEY = r"([$€£])\s?([\d][\d.,]*)"
REFRESH_HOURS = 3


def normalize(url):
    m = URL_RE.search(str(url or "").strip())
    if not m:
        raise ValueError("Das ist kein Kampagnen-Link. Bei Whop die Kampagne öffnen und den Link "
                         "„contentrewards.com/c/campaigns/…“ kopieren.")
    pid = m.group(1).lower()
    return pid, "https://contentrewards.com/c/campaigns/" + pid


def _meta(page, name):
    for pat in (r'<meta[^>]+(?:property|name)="%s"[^>]*\scontent="([^"]*)"',
                r'<meta[^>]+content="([^"]*)"[^>]*\s(?:property|name)="%s"'):
        m = re.search(pat.replace("%s", re.escape(name)), page)
        if m:
            return html.unescape(m.group(1)).strip()
    return ""


def _text(page):
    page = re.sub(r"(?is)<(script|style|svg|noscript)\b.*?</\1>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", "\n", page)
    page = html.unescape(page)
    page = re.sub("[⁦-⁩​]", "", page)
    return re.sub(r"\s+", " ", page)


def _num(s):
    s = s.strip().rstrip(".,")
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s) or re.fullmatch(r"\d+\.\d{1,2}", s):
        return float(s.replace(",", ""))
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s) or re.fullmatch(r"\d+,\d{1,2}", s):
        return float(s.replace(".", "").replace(",", "."))
    return float(re.sub(r"[^\d]", "", s) or 0)


def parse(page):
    """Liest die Angaben aus der öffentlichen Kampagnen-Seite."""
    title = _meta(page, "og:title")
    if not title:
        m = re.search(r"(?is)<title>(.*?)</title>", page)
        title = html.unescape(m.group(1)).split("|")[0].strip() if m else ""
    if not title or title.lower().startswith("content rewards"):
        raise ValueError("Die Kampagne wurde nicht gefunden. Ist der Link richtig?")
    brand = ""
    if " by " in title:
        title, brand = title.rsplit(" by ", 1)
    text = _text(page)
    plat = "|".join(PLATFORMS)
    rates, seen = [], set()
    for p, cur, val in re.findall(r"\b(%s)\s*Per 1K views\s*%s" % (plat, MONEY), text):
        if p not in seen:
            seen.add(p)
            rates.append({"platform": "X" if p == "Twitter" else p, "rate": _num(val), "currency": cur})
    one = lambda label: re.search(label + r"\s*" + MONEY, text)
    mn, mx = one("Min payout"), one("Max payout")
    bud = re.search(r"Budget\s*" + MONEY + r"\s*/\s*" + MONEY, text)
    st = re.search(r"\b(Active|Live|Paused|Ended|Completed)\b", text)
    return {
        "title": title.strip()[:120],
        "brand": brand.strip()[:60],
        "about": _meta(page, "og:description")[:400],
        "rates": rates,
        "currency": (rates[0]["currency"] if rates else (mn.group(1) if mn else "$")),
        "min_payout": _num(mn.group(2)) if mn else None,
        "max_payout": _num(mx.group(2)) if mx else None,
        "budget_used": _num(bud.group(2)) if bud else None,
        "budget_total": _num(bud.group(4)) if bud else None,
        "status": STATUS.get(st.group(1).lower(), "") if st else "",
        "image": _meta(page, "og:image"),
    }


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36 shorts-zentrale",
        "Accept": "text/html", "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(4_000_000).decode("utf-8", "replace")


def load():
    items = store.read(FILE, [])
    return items if isinstance(items, list) else []


def _save(items):
    with store.LOCK:
        store.write(FILE, items)


def find(pid):
    return next((x for x in load() if x["id"] == pid), None)


def add(url, page=None):
    pid, url = normalize(url)
    info = parse(page if page is not None else fetch(url))
    with store.LOCK:
        items = [x for x in load() if x["id"] != pid]
        old = find(pid) or {}
        item = {"id": pid, "url": url, "added_at": old.get("added_at") or store.now().isoformat(timespec="seconds"),
                **info, "checked_at": store.now().isoformat(timespec="seconds"), "error": None}
        items.insert(0, item)
        _save(items)
    return item


def refresh(pid=None, get=fetch):
    """Holt die Angaben neu. Fehler werden am Eintrag gemerkt, die alten Werte bleiben."""
    changed = []
    for x in load():
        if pid and x["id"] != pid:
            continue
        try:
            info, err = parse(get(x["url"])), None
        except Exception as e:  # Netz weg oder Seite geändert
            info, err = {}, (str(e) if isinstance(e, ValueError) else "Seite gerade nicht erreichbar")
        changed.append((x["id"], info, err))
    with store.LOCK:
        items = load()
        for pid_, info, err in changed:
            for x in items:
                if x["id"] == pid_:
                    old_status = x.get("status")
                    x.update(info)
                    x["error"] = err
                    x["checked_at"] = store.now().isoformat(timespec="seconds")
                    if info and old_status and info.get("status") != old_status:
                        store.log("info", f"Whop-Kampagne „{x['title']}“: {info.get('status') or 'Status unbekannt'}",
                                  agent="clipper", kind="input")
        _save(items)
    return items


def remove(pid):
    with store.LOCK:
        items = load()
        if not any(x["id"] == pid for x in items):
            raise ValueError("Unbekannte Whop-Kampagne.")
        _save([x for x in items if x["id"] != pid])


def summary():
    camps = clips.all_campaigns()
    out = []
    for x in load():
        mine = [c for c in camps if c.get("program") == x["id"]]
        cl = [k for c in mine for k in c.get("clips", [])]
        left = None
        if x.get("budget_total") is not None and x.get("budget_used") is not None:
            left = max(0.0, x["budget_total"] - x["budget_used"])
        out.append({**x, "budget_left": left, "videos": len(mine), "clips": len(cl),
                    "posted": sum(1 for k in cl if k.get("status") == "gepostet")})
    return out
