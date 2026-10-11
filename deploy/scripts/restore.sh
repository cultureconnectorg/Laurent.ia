#!/usr/bin/env bash
# Restores an encrypted backup (scripts/backup.sh) on this machine — e.g. a new computer
# after the old one was lost. Needs: the SAME deploy/.env as the lost machine (keep an
# offline copy!), the backup file, and the age private key that can decrypt it.
# Usage: scripts/restore.sh <backup .archive.gz.age> <age private key file> [--force]
set -euo pipefail
cd "$(dirname "$0")/.."
BACKUP=${1:?backup file}; KEY=${2:?age private key file}; FORCE=${3:-}
[ -f .env ] || { echo "deploy/.env missing: restore it from your offline copy first"; exit 1; }
set -a; . ./.env; set +a
[ -f "$BACKUP.sha256" ] && sha256sum -c "$BACKUP.sha256"
docker compose up -d mongo
for _ in $(seq 1 60); do docker compose exec -T mongo mongosh --quiet --eval 'db.runCommand({ping:1}).ok' 2>/dev/null | grep -q 1 && break; sleep 2; done
count() { docker compose exec -T mongo mongosh --quiet -u root -p "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin \
  --eval "let n=0; ['laurentia','frekcore'].forEach(d=>db.getSiblingDB(d).getCollectionNames().forEach(c=>n+=db.getSiblingDB(d)[c].countDocuments())); print(n)" | tr -d '\r'; }
existing=$(count)
if [ "$existing" != "0" ] && [ "$FORCE" != "--force" ]; then
  echo "the databases already hold $existing documents: refusing to overwrite (add --force if you mean it)"; exit 1
fi
age -d -i "$KEY" "$BACKUP" | docker compose exec -T mongo mongorestore --quiet --archive --gzip --drop \
  -u root -p "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin --nsExclude 'admin.*'
echo "restored: $(count) documents"
docker compose up -d
