#!/usr/bin/env bash
# Reproducible protocol (S0, kept in S1): fresh database -> local API under the
# network guard -> full suite -> stop API. Usage: run_suite.sh <out_dir>
# Needs MongoDB on 127.0.0.1:27017 and $PYTHON (defaults to python3) with
# requirements.txt (minus emergentintegrations) + requirements-test.txt.
# Inference: the deterministic local engine (tests/_harness/fake_engine.py) unless
# BRAIN_ENGINE_URL is already set (e.g. a real llama.cpp server in CI).
set -u
BACKEND=$(cd "$(dirname "$0")/../.." && pwd)
H=$BACKEND/tests/_harness
OUT=${1:?out dir}; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
PY=${PYTHON:-python3}
for v in HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy; do unset $v; done
export APP_ENV=test
export MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=suite_$(date +%s)_$$
export LAURENTIA_ENCRYPTION_KEY=test-only-encryption-key LAURENTIA_SECRET_SALT=test-only-salt
export LAURENTIA_CVLN_SERVICE_API_KEY=test-only-service-key
export CHANTIER7_SCHEDULERS_DISABLED=1 CHANTIER10_REPORTS_DISABLED=1 ORCHESTRATOR_DISABLED=1
export REACT_APP_BACKEND_URL=http://localhost:8001 CORS_ORIGINS=http://localhost
export LAURENTIA_EGRESS_LOG=$OUT/egress.jsonl; : > "$LAURENTIA_EGRESS_LOG"
cd "$BACKEND"
ENGINE_PID=""
if [ -z "${BRAIN_ENGINE_URL:-}" ]; then
  "$PY" "$H/fake_engine.py" --port 8090 --log "$OUT/engine.jsonl" & ENGINE_PID=$!
  export BRAIN_ENGINE_URL=http://127.0.0.1:8090 BRAIN_ENGINE_MODEL=fake-deterministic
  for _ in $(seq 1 20); do curl -s -m 1 "$BRAIN_ENGINE_URL/health" >/dev/null && break; sleep 0.5; done
fi
PYTHONPATH=$H/sitecustomize "$PY" -m uvicorn server:app --host 127.0.0.1 --port 8001 > "$OUT/server.log" 2>&1 &
PID=$!
for _ in $(seq 1 40); do curl -s -m 2 http://127.0.0.1:8001/api/health >/dev/null && break; sleep 1; done
"$PY" -m pytest tests -p no:cacheprovider -q -rA --junitxml="$OUT/junit.xml" > "$OUT/pytest.log" 2>&1
RC=$?
kill $PID 2>/dev/null; wait $PID 2>/dev/null
[ -n "$ENGINE_PID" ] && kill $ENGINE_PID 2>/dev/null
echo "pytest_exit=$RC" >> "$OUT/pytest.log"
# The API process is guarded too: any recorded egress fails the run.
if [ -s "$LAURENTIA_EGRESS_LOG" ]; then
  echo "egress_attempts=$(wc -l < "$LAURENTIA_EGRESS_LOG")" | tee -a "$OUT/pytest.log"
  [ $RC -eq 0 ] && RC=3
fi
tail -2 "$OUT/pytest.log"
exit $RC
