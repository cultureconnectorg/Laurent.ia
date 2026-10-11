"""No-regression check: every failing test must be listed in known_failures.txt.

Exit 1 if a test fails that is not in the baseline (a regression). Tests of the
baseline that now pass are reported so the list can be shortened.
Usage: python compare_baseline.py junit.xml known_failures.txt
"""
import sys
import xml.etree.ElementTree as ET

junit, baseline = sys.argv[1], sys.argv[2]
known = {l.strip() for l in open(baseline, encoding="utf-8") if l.strip() and not l.startswith("#")}
failing, total = set(), 0
for tc in ET.parse(junit).iter("testcase"):
    total += 1
    if tc.find("failure") is not None or tc.find("error") is not None:
        failing.add(f"{tc.get('classname')}::{tc.get('name')}")
regressions = sorted(failing - known)
fixed = sorted(known - failing)
print(f"tests={total} failing={len(failing)} baseline={len(known)}")
for t in fixed:
    print(f"NOW PASSING (remove from baseline): {t}")
for t in regressions:
    print(f"REGRESSION: {t}")
sys.exit(1 if regressions else 0)
