"""Entspannungskanal: Planung (einmal pro Tag ab Uhrzeit), Reihenfolge der Arten, Upload-Felder."""
import datetime as dt
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import entspannung

cfg = {"relax_token": "t", "relax_on": True, "relax_hour": 17}
at = lambda h, d=20: dt.datetime(2026, 11, d, h, 30)
assert not entspannung.is_due(cfg, None, at(16))                      # zu früh
assert entspannung.is_due(cfg, None, at(17))                          # ab der Uhrzeit
assert entspannung.is_due(cfg, "2026-11-19", at(18))                  # gestern war das letzte
assert not entspannung.is_due(cfg, "2026-11-20", at(18))              # heute schon eins
assert not entspannung.is_due({**cfg, "relax_token": ""}, None, at(18))
assert not entspannung.is_due({**cfg, "relax_on": False}, None, at(18))
tried = at(18).replace(minute=0).isoformat()
assert not entspannung.is_due(cfg, None, at(18), tried)               # Versuch vor weniger als 1 Stunde
assert entspannung.is_due(cfg, None, at(19), tried)
assert [entspannung.next_kind(i) for i in range(4)] == ["feuer", "regen", "pendel", "feuer"]
assert 60 in entspannung.MINUTES and 480 in entspannung.MINUTES

import yt
src = open(os.path.join(os.path.dirname(yt.__file__), "yt.py")).read()
assert 'spec.get("footer", FOOTER)' in src and 'spec.get("chunksize", -1)' in src
print("ok")
