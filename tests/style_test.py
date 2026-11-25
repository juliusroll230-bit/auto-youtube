import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import entspannung as e
import numpy as np

today = datetime.date(2026, 11, 25)
st = e.choose_style([], today, 0)
assert set(st) == set(e.STYLE_KEYS), st
for k, v in st.items():
    assert v in e.STYLE_KEYS[k]
for t in e.TITLE_STYLES:
    for idea in e.IDEAS[:5]:
        m = e.meta(idea["id"], 3, 1, t)
        title = m["title"] if isinstance(m, dict) else m[0]
        assert 0 < len(title) <= 100, (t, title)
sig = np.random.randn(48000)
out = e.soften(sig)
assert len(out) == len(sig)
assert e.learned_hour([], today, 0) in e.LEARN_HOURS
print("style_test ok")
