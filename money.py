"""Geld-Konto der Zentrale: echte Auszahlungen, die Julius selbst einträgt.

YouTube und Content Rewards geben Clippern keine Schnittstelle für das echte Geld auf dem Konto.
Darum trägt man eine Auszahlung von Hand ein, sobald sie da ist. Die Website zeigt daneben die
Schätzungen (Content Rewards aus Aufrufen mal Rate, YouTube-Werbegeld aus den Aufrufen).
"""
import datetime as dt
import secrets

import store

FILE = "money.json"
SOURCES = ("Content Rewards", "YouTube", "TikTok", "Instagram", "Sonstiges")
CURRENCIES = ("€", "$")


def load():
    data = store.read(FILE, {})
    pay = data.get("payouts") if isinstance(data, dict) else None
    return {"payouts": pay if isinstance(pay, list) else []}


def add(amount, currency="€", source="Content Rewards", date=None, note=""):
    try:
        amount = round(float(str(amount).replace(",", ".")), 2)
    except ValueError:
        raise ValueError("Bitte einen Betrag eingeben, zum Beispiel 12,50.")
    if not 0 < amount < 1_000_000:
        raise ValueError("Der Betrag muss größer als 0 sein.")
    if currency not in CURRENCIES:
        currency = "€"
    if source not in SOURCES:
        source = "Sonstiges"
    try:
        day = dt.date.fromisoformat(str(date)[:10]) if date else store.now().date()
    except ValueError:
        raise ValueError("Das Datum stimmt nicht.")
    item = {"id": secrets.token_hex(4), "amount": amount, "currency": currency, "source": source,
            "date": day.isoformat(), "note": str(note or "").strip()[:80]}
    with store.LOCK:
        data = load()
        data["payouts"].append(item)
        data["payouts"].sort(key=lambda x: x.get("date") or "", reverse=True)
        store.write(FILE, data)
    return item


def remove(pid):
    with store.LOCK:
        data = load()
        before = len(data["payouts"])
        data["payouts"] = [x for x in data["payouts"] if x.get("id") != pid]
        store.write(FILE, data)
    return len(data["payouts"]) < before
