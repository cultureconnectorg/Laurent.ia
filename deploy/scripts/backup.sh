#!/usr/bin/env bash
# Encrypted backup of every database (Laurent.ia + FREKCORE), for the laptop.
# The archive is encrypted with age for the laptop's public key: only the laptop can
# read it. Usage: scripts/backup.sh <age public key of the laptop> [ssh target dir]
#   e.g. scripts/backup.sh age1... laurent@10.77.0.2:~/laurentia-backups
set -euo pipefail
cd "$(dirname "$0")/.."
RECIPIENT=${1:?age public key (age1...) of the laptop}
TARGET=${2:-}
command -v age >/dev/null || { echo "install age first (https://age-encryption.org)"; exit 1; }
set -a; . ./.env; set +a
mkdir -p backups
OUT="backups/laurentia-$(date -u +%Y%m%dT%H%M%SZ).archive.gz.age"
docker compose exec -T mongo mongodump --quiet --archive --gzip \
  -u root -p "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin \
  | age -r "$RECIPIENT" -o "$OUT"
sha256sum "$OUT" | tee "$OUT.sha256"
[ -n "$TARGET" ] && scp "$OUT" "$OUT.sha256" "$TARGET"/ && echo "copied to $TARGET"
echo "backup: $OUT"
