"""Push-Nachrichten aufs Handy über ntfy.sh (Phase E, seit 26.11.2026, Julius' Wunsch).

ntfy.sh ist kostenlos und braucht kein Konto: Die App „ntfy“ abonniert ein Thema (einen langen Zufallsnamen),
die Zentrale schickt Nachrichten an dieses Thema. Das Thema entsteht beim ersten Start (store.init) und steht
nur in der Zentrale (Kanäle verbinden > Erweitert > Nachrichten aufs Handy, mit QR-Code). Wer das Thema kennt,
kann mitlesen, darum ist es lang und zufällig, und die Nachrichten enthalten nur Zahlen, keine Zugangsdaten.

- Tagesbericht um 19 Uhr (einstellbar), mit Link auf Kampagnen.
- Sofort-Meldungen, höchstens 1 pro Stunde (mehrere werden gesammelt): Upload fehlgeschlagen,
  Clip seit über 2 Stunden nicht eingereicht, Kampagnen-Budget über 80 % verbraucht oder Kampagne beendet,
  ein Short läuft deutlich besser als die anderen (Gewinner).
- Wochenbericht sonntags 18 Uhr: Fortschritt zum YouTube-Partnerprogramm.
- Ohne Thema oder mit „Nachrichten aus“ wird nichts gesendet.
"""
import datetime as dt
import json
import re
import secrets
import statistics
import urllib.request

import store

SERVER = "https://ntfy.sh"
INSTANT_GAP = 3600          # Sofort-Meldungen höchstens 1 pro Stunde
WEEKLY = (6, 18)            # Sonntag (weekday 6), 18 Uhr
BUDGET_WARN = 0.80
CLIP_OPEN_MIN = 120
WIN_MIN_VIEWS = 1500
# YouTube-Partnerprogramm (volle Monetarisierung). Ab 01.02.2027 verdoppelt YouTube die Schwellen für neue Kanäle
# (blog.youtube, „YouTube Partner Program updates 2027“). Abos bleiben 1.000.
YPP = [("2027-02-01", {"subs": 1000, "hours": 4000, "shorts": 10_000_000}),
       ("9999-12-31", {"subs": 1000, "hours": 8000, "shorts": 20_000_000})]
SENT = []                   # nur für Tests: was zuletzt gesendet wurde
_send_impl = None           # Tests können das HTTP ersetzen


def new_topic():
    return "zentrale-" + re.sub(r"[^A-Za-z0-9]", "", secrets.token_urlsafe(24))[:24].lower()


def settings(cfg=None):
    cfg = cfg or store.config()
    return {"topic": cfg.get("ntfy_topic") or "", "on": cfg.get("ntfy_on", True) is not False,
            "hour": int(cfg.get("ntfy_hour") if cfg.get("ntfy_hour") is not None else 19),
            "base": (cfg.get("base_url") or "").rstrip("/")}


def subscribe_url(topic):
    return f"{SERVER}/{topic}"


def link(base, hash_):
    return f"{base}/{hash_}" if base else ""


def _http(payload):
    req = urllib.request.Request(SERVER + "/", data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "shorts-zentrale"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status


def send(title, message, tags=None, click="", priority=3, cfg=None, force=False):
    """Schickt eine Nachricht an das Thema. Ohne Thema oder ausgeschaltet: nichts (False)."""
    s = settings(cfg)
    if not s["topic"] or (not s["on"] and not force):
        return False
    payload = {"topic": s["topic"], "title": title[:120], "message": message[:3500], "priority": priority}
    if tags:
        payload["tags"] = list(tags)
    if click:
        payload["click"] = click
    (_send_impl or _http)(payload)
    SENT.append(payload)
    del SENT[:-50]
    return True


# --- Sofort-Meldungen: sammeln, höchstens eine pro Stunde senden ---------------------------------

def _st():
    return store.state().get("push") or {}


def _save(p):
    with store.LOCK:
        st = store.state()
        st["push"] = p
        store.write("state.json", st)


def alert(key, text, tag="warning"):
    """Merkt eine Sofort-Meldung vor (jede Sache nur einmal, erkannt an key)."""
    s = settings()
    if not s["topic"] or not s["on"]:
        return False
    with store.LOCK:
        st = store.state()
        p = st.get("push") or {}
        seen = p.get("seen") or []
        if key in seen:
            return False
        p["seen"] = (seen + [key])[-400:]
        p["pending"] = (p.get("pending") or []) + [{"text": text, "tag": tag}]
        st["push"] = p
        store.write("state.json", st)
    return True


def flush(now=None, cfg=None):
    """Sendet gesammelte Sofort-Meldungen, wenn die letzte über eine Stunde her ist."""
    now = now or store.now()
    p = _st()
    pend = p.get("pending") or []
    if not pend:
        return False
    last = p.get("last_instant")
    if last and (now - dt.datetime.fromisoformat(last)).total_seconds() < INSTANT_GAP:
        return False
    s = settings(cfg)
    title = pend[0]["text"].split(":")[0] if len(pend) == 1 else f"{len(pend)} Dinge brauchen dich"
    msg = "\n".join("• " + x["text"] for x in pend[:8]) + (f"\n… und {len(pend) - 8} weitere" if len(pend) > 8 else "")
    if send(title, msg, tags=[pend[0]["tag"]], click=link(s["base"], "#kampagnen"), priority=4, cfg=cfg):
        p = _st()
        p["pending"] = (p.get("pending") or [])[len(pend):]
        p["last_instant"] = now.isoformat(timespec="seconds")
        _save(p)
        return True
    return False


def on_log(entry):
    """store.LISTENERS: ein fehlgeschlagener Upload wird sofort gemeldet."""
    if entry.get("level") == "error" and entry.get("agent") == "publisher":
        alert("err:" + entry.get("at", "")[:13] + ":" + entry.get("text", "")[:40],
              _upload_text(entry.get("text", "")), "rotating_light")


def _upload_text(text):
    text = text[:200]
    return text if text.lower().startswith("upload fehlgeschlagen") else "Upload fehlgeschlagen: " + text


# --- Prüfungen (alle paar Minuten) ------------------------------------------------------------

def check_clips(now=None):
    import einreichen
    for x in einreichen.overview(now=now)["items"]:
        if x["state"] == "offen" and (x.get("minutes") or 0) > CLIP_OPEN_MIN:
            alert(f"clip:{x['id']}:{x['n']}", f"Clip seit über 2 Stunden nicht eingereicht: „{x['title']}“ ({x['campaign']})", "hourglass")


def check_campaigns(now=None):
    import whop
    for x in whop.load():
        name = x.get("title") or "Kampagne"
        if x.get("status") == "beendet":
            alert("end:" + x["id"], f"Kampagne beendet: {name}. Neue Clips dafür bringen nichts mehr.", "checkered_flag")
            continue
        total, used = x.get("budget_total"), x.get("budget_used")
        if total and used is not None and used / total >= BUDGET_WARN:
            alert("bud:" + x["id"], f"Budget fast aufgebraucht: {name} ({round(used / total * 100)} % verbraucht). Schnell einreichen.", "money_with_wings")


def winners(uploads, stats, now=None):
    """Shorts der letzten 7 Tage, die mindestens doppelt so viele Aufrufe haben wie der Schnitt (Median) und ≥ 1.500."""
    now = now or store.now()
    main = [u for u in uploads if u.get("video_id") and u.get("kind") != "clip" and not u.get("lang") and u.get("channel") != "clips"]
    views = [int((stats.get(u["video_id"]) or {}).get("views") or 0) for u in main[-40:]]
    if len(views) < 5:
        return []
    med = statistics.median(views)
    out = []
    for u in main[-60:]:
        try:
            age = now - dt.datetime.fromisoformat(u["posted_at"])
        except (KeyError, ValueError, TypeError):
            continue
        v = int((stats.get(u["video_id"]) or {}).get("views") or 0)
        if age <= dt.timedelta(days=7) and v >= WIN_MIN_VIEWS and v >= 2 * max(med, 1):
            out.append((u, v, med))
    return out


def check_winners(now=None):
    st = store.state()
    stats = (store.read("stats.json", {}) or {}).get("videos") or {}
    for u, v, med in winners(st.get("uploads", []), stats, now):
        views = f"{v:,}".replace(",", ".")
        factor = f"{v / max(med, 1):.1f}".replace(".", ",")
        alert("win:" + u["video_id"], f"Gewinner erkannt: „{u.get('title')}“ hat {views} Aufrufe, {factor}× so viel wie üblich. "
              "Die Zentrale baut ähnliche Videos nach.", "trophy")


# --- Berichte ----------------------------------------------------------------------------------

def daily_text(now=None):
    now = now or store.now()
    today = now.date().isoformat()
    st = store.state()
    ups = [u for u in st.get("uploads", []) if str(u.get("posted_at") or "")[:10] == today]
    main = sum(1 for u in ups if u.get("kind") != "clip" and not u.get("lang") and u.get("channel") != "clips")
    clipi = sum(1 for u in ups if u.get("channel") == "clips")
    abg = sum(1 for u in ups if u.get("abgabe"))
    longv = sum(1 for u in ups if u.get("lang"))
    ch = store.read("channel.json", {}) or {}
    errs = sum(1 for e in st.get("events", []) if e.get("level") == "error" and str(e.get("at"))[:10] == today)
    lines = [f"Hauptkanal: {main} Shorts" + (f" + {longv} langes Video" if longv else ""),
             f"Clipi: {clipi} Clips" + (f" (davon {abg} Kampagnen-Clips auf späten Plätzen)" if abg else "")]
    if ch.get("subscribers") is not None:
        lines.append(f"Abonnenten: {ch['subscribers']:,}".replace(",", "."))
    try:
        import einreichen
        ov = einreichen.overview(now=now)
        lines.append(f"Offen zum Einreichen: {ov['open']}" + (" ⚠️" if ov["late"] else ""))
        earned = sum(p["earned"] or 0 for p in ov["campaigns"])
        if earned:
            lines.append(f"Kampagnen geschätzt: ${earned:.2f}")
    except Exception:  # noqa: BLE001  (Bericht kommt trotzdem)
        pass
    if errs:
        lines.append(f"Fehler heute: {errs} (Details in der Zentrale)")
    return f"Tagesbericht {now.strftime('%d.%m.')}", "\n".join(lines)


def ypp_rule(day):
    for until, rule in YPP:
        if day.isoformat() < until:
            return until, rule
    return YPP[-1]


def ypp_numbers(cfg, now=None):
    """Abos, Wiedergabestunden (12 Monate, ohne Shorts) und Shorts-Aufrufe (90 Tage). Aus YouTube Analytics,
    wenn verbunden, sonst Shorts-Aufrufe geschätzt aus den eigenen Uploads (Stunden dann unbekannt)."""
    now = now or store.now()
    ch = store.read("channel.json", {}) or {}
    out = {"subs": ch.get("subscribers"), "hours": None, "shorts": None, "exact": False}
    if cfg.get("analytics_token"):
        try:
            import yt
            out["hours"] = yt.watch_hours(cfg, str(now.date() - dt.timedelta(days=365)), str(now.date()))
            out["shorts"] = yt.shorts_views(cfg, str(now.date() - dt.timedelta(days=90)), str(now.date()))
            out["exact"] = True
            return out
        except Exception as e:  # noqa: BLE001
            print("YPP-Zahlen:", repr(e), flush=True)
    stats = (store.read("stats.json", {}) or {}).get("videos") or {}
    since = (now - dt.timedelta(days=90)).isoformat()
    out["shorts"] = sum(int((stats.get(u.get("video_id")) or {}).get("views") or 0) for u in store.state().get("uploads", [])
                        if str(u.get("posted_at") or "") >= since and not u.get("lang") and u.get("channel") != "clips")
    return out


def weekly_text(cfg=None, now=None):
    cfg = cfg or store.config()
    now = now or store.now()
    until, rule = ypp_rule(now.date())
    n = ypp_numbers(cfg, now)
    de = lambda x: f"{x:,.0f}".replace(",", ".")
    pct = lambda a, b: f"{min(100, a / b * 100):.0f} %" if a is not None else "unbekannt"
    lines = [f"Abos: {de(n['subs'] or 0)} von {de(rule['subs'])} ({pct(n['subs'] or 0, rule['subs'])})",
             (f"Wiedergabezeit: {de(n['hours'])} von {de(rule['hours'])} Std. in 12 Monaten ({pct(n['hours'], rule['hours'])})"
              if n["hours"] is not None else f"Wiedergabezeit: unbekannt (Zuschauer-Daten verbinden), Ziel {de(rule['hours'])} Std."),
             f"oder Shorts-Aufrufe: {de(n['shorts'] or 0)} von {de(rule['shorts'])} in 90 Tagen ({pct(n['shorts'] or 0, rule['shorts'])})"
             + ("" if n["exact"] else " (geschätzt)")]
    if until != "9999-12-31":
        days = (dt.date.fromisoformat(until) - now.date()).days
        lines.append(f"Ab 01.02.2027 gelten für neue Kanäle doppelte Werte (8.000 Std. oder 20 Mio.). Noch {days} Tage.")
    lines.append("Geld zahlt YouTube über das AdSense-Konto deiner Eltern aus.")
    return f"Wochenbericht {now.strftime('%d.%m.')}: Weg zum Partnerprogramm", "\n".join(lines)


def tick(now=None, cfg=None):
    """Läuft jede Minute (server.push_worker): Prüfungen, Sofort-Meldungen, Tages- und Wochenbericht."""
    cfg = cfg or store.config()
    s = settings(cfg)
    if not s["topic"] or not s["on"]:
        return
    now = now or store.now()
    for fn in (check_clips, check_campaigns, check_winners):
        try:
            fn(now)
        except Exception as e:  # noqa: BLE001
            print("Push-Prüfung:", repr(e), flush=True)
    flush(now, cfg)
    p = _st()
    today = now.date().isoformat()
    if now.hour >= s["hour"] and p.get("daily") != today:
        title, msg = daily_text(now)
        if send(title, msg, tags=["bar_chart"], click=link(s["base"], "#kampagnen"), cfg=cfg):
            p = _st(); p["daily"] = today; _save(p)
    week = now.strftime("%G-%V")
    if now.weekday() == WEEKLY[0] and now.hour >= WEEKLY[1] and p.get("weekly") != week:
        title, msg = weekly_text(cfg, now)
        if send(title, msg, tags=["chart_with_upwards_trend"], click=link(s["base"], "#uebersicht"), cfg=cfg):
            p = _st(); p["weekly"] = week; _save(p)


def qr_svg(text):
    """QR-Code als SVG (segno, läuft ohne Netz)."""
    import io
    import segno
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="svg", scale=6, border=2, dark="#0B0B0C", light="#ffffff")
    return buf.getvalue()


def overview(cfg):
    s = settings(cfg)
    p = (store.state().get("push") or {})
    return {"topic": s["topic"], "on": s["on"], "hour": s["hour"], "url": subscribe_url(s["topic"]) if s["topic"] else "",
            "pending": len(p.get("pending") or []), "daily": p.get("daily"), "weekly": p.get("weekly"),
            "last_instant": p.get("last_instant"), "base": s["base"]}
