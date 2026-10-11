#!/usr/bin/env bash
# Checks, on the running stack, that the sovereignty guarantees hold. Exit 0 = all good.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0; ok() { echo "OK   $*"; }; ko() { echo "FAIL $*"; fail=1; }
NET=$(docker network ls --format '{{.Name}}' | grep -E '_core$' | head -1)
[ "$(docker network inspect -f '{{.Internal}}' "$NET" 2>/dev/null)" = "true" ] && ok "network $NET is internal (no route to the Internet)" || ko "network core is not internal"
for svc in backend frekcore mongo engine test-engine; do
  cid=$(docker compose ps -q "$svc" 2>/dev/null); [ -z "$cid" ] && continue
  nets=$(docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$cid")
  [ "$(echo $nets)" = "$NET" ] && ok "$svc is only on $NET" || ko "$svc networks: $nets"
done
# Active probe from the backend: a public address must be unreachable.
if docker compose exec -T backend python3 -c "import socket; s=socket.create_connection(('1.1.1.1', 443), timeout=5)" 2>/dev/null; then
  ko "backend reached 1.1.1.1:443"; else ok "backend cannot reach the Internet (probe to 1.1.1.1:443 refused)"; fi
H=$(docker compose exec -T backend curl -s http://127.0.0.1:8001/api/health)
echo "$H" | grep -q '"engine":"sovereign"' && ok "engine: $(echo "$H" | grep -o '"model":"[^"]*"')" || ko "health: $H"
docker compose exec -T backend sh -c 'test -z "$EMERGENT_LLM_KEY$OPENAI_API_KEY$ANTHROPIC_API_KEY"' && ok "no external provider key in the backend" || ko "an external provider key is set"
exit $fail
