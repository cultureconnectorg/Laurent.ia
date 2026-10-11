import sys, xml.etree.ElementTree as ET, collections, re
t = ET.parse(sys.argv[1]); rows = []
for tc in t.iter("testcase"):
    name = f"{tc.get('classname')}::{tc.get('name')}"
    st, msg = "passed", ""
    for tag in ("failure", "error", "skipped"):
        e = tc.find(tag)
        if e is not None:
            st = tag; msg = (e.get("message") or "").splitlines()[0][:160] if e.get("message") else (e.text or "")[:160]
    rows.append((name, st, msg))
c = collections.Counter(r[1] for r in rows); print(dict(c), "total", len(rows))
for n, s, m in rows:
    if s != "passed": print(f"{s:8} {n} :: {m}")
