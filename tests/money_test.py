"""Geld-Konto: Auszahlungen eintragen, prüfen, löschen; Dashboard überlebt kaputte Teile."""
import os
import sys
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import money  # noqa: E402
import store  # noqa: E402

store.init()
a = money.add("12,50", "$", "Content Rewards", "2026-11-05", "WoW")
assert a["amount"] == 12.5 and a["currency"] == "$" and a["date"] == "2026-11-05"
b = money.add(3, "€", "Unbekannt")
assert b["source"] == "Sonstiges"
for bad in ("", "abc", "-4", "0"):
    try:
        money.add(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("ungültiger Betrag angenommen: %r" % bad)
assert len(money.load()["payouts"]) == 2
assert money.remove(a["id"]) and not money.remove("gibtsnicht")
assert [x["id"] for x in money.load()["payouts"]] == [b["id"]]

d = store.dashboard(repo=False)
assert d["money"]["payouts"][0]["amount"] == 3
store.write("money.json", ["kaputt"])
assert money.load() == {"payouts": []}
assert store._safe(lambda: 1 / 0, "ok") == "ok"
print("money_test ok")
