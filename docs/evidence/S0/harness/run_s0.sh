#!/usr/bin/env bash
# S0 protocol: fresh DB -> start API under guard -> run suite -> stop API.
set -u
S=$(cd "$(dirname "$0")" && pwd); RUN=$1; OUT=$S/proto/$RUN; mkdir -p "$OUT"
. "$S/envB.sh"; export DB_NAME=s0_$RUN S0_EGRESS_LOG=$OUT/egress.jsonl
cd /home/user/lia-s0/backend
"$S/venv/bin/python" -m uvicorn server:app --host 127.0.0.1 --port 8001 > "$OUT/server.log" 2>&1 & PID=$!
for i in $(seq 1 30); do curl -s -m 2 http://127.0.0.1:8001/api/health >/dev/null && break; sleep 1; done
"$S/venv/bin/python" -m pytest tests -p no:cacheprovider -q -rA --junitxml="$OUT/junit.xml" > "$OUT/pytest.log" 2>&1; echo "pytest_exit=$?" >> "$OUT/pytest.log"
kill $PID; wait $PID 2>/dev/null
