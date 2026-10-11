#!/usr/bin/env bash
# One-time identity setup on a running stack (C1). Two explicit, logged steps:
#  1. FREKCORE grants the Laurent.ia client (cvl-brain) the permissions it needs —
#     "emit" covers identity, passkeys and notarization in FREKCORE's model. This goes
#     through FREKCORE's admin API: Laurent.ia never touches FREKCORE's database.
#  2. FREKCORE issues your FREK-ID; it becomes the only principal of this instance.
# Usage: scripts/frekcore-setup.sh <your e-mail>    (the e-mail is stored hashed by FREKCORE)
set -euo pipefail
cd "$(dirname "$0")/.."
EMAIL=${1:?your e-mail}
set -a; . ./.env; set +a
echo "1/2 permissions of cvl-brain in FREKCORE:"
docker compose exec -T -e ADMIN_KEY="$FREK_SECRET_KEY" backend sh -c \
  'curl -sf -X PATCH http://frekcore:8001/api/v1/admin/clients/cvl-brain \
     -H "X-Admin-Key: $ADMIN_KEY" -H "Content-Type: application/json" \
     -d "{\"permissions\": [\"stats\", \"emit\"]}"'
echo
FREK_ID=$(docker compose exec -T -e EMAIL="$EMAIL" backend python -c \
  "import asyncio, os; from services import frekcore_client as f; print(asyncio.run(f.emit_identity(os.environ['EMAIL']))['frek_id'])" | tr -d '\r')
echo "2/2 FREK-ID issued by FREKCORE: $FREK_ID"
if grep -q '^LAURENTIA_PRINCIPAL_FREK_ID=' .env; then
  sed -i.bak "s|^LAURENTIA_PRINCIPAL_FREK_ID=.*|LAURENTIA_PRINCIPAL_FREK_ID=$FREK_ID|" .env && rm -f .env.bak
else
  echo "LAURENTIA_PRINCIPAL_FREK_ID=$FREK_ID" >> .env
fi
# The variable loaded from the old .env would otherwise win over the updated file.
export LAURENTIA_PRINCIPAL_FREK_ID="$FREK_ID"
docker compose up -d backend >/dev/null
echo "Done. Open Laurent.ia, menu > FREK-ID $FREK_ID > « créer ma passkey »."
