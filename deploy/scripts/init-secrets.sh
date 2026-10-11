#!/usr/bin/env bash
# Generates deploy/.env with strong random secrets, on THIS machine only.
# Nothing is sent anywhere; the file is readable by you alone (chmod 600).
# Usage: scripts/init-secrets.sh [public_origin] [site_addresses]
#   public_origin   URL you type in the browser   (default https://localhost:8443)
#   site_addresses  host names served by HTTPS    (default "localhost")
set -euo pipefail
cd "$(dirname "$0")/.."
[ -e .env ] && { echo ".env exists: refusing to overwrite secrets (delete it yourself if you mean it)"; exit 1; }
rnd() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-48; }
ORIGIN=${1:-https://localhost:8443}
SITES=${2:-localhost}
umask 077
cat > .env <<ENV
# Generated $(date -u +%Y-%m-%dT%H:%M:%SZ) by scripts/init-secrets.sh — never commit, never send.
PUBLIC_ORIGIN=$ORIGIN
SITE_ADDRESSES="$SITES"
BIND_ADDRESS=127.0.0.1
# Start the inference engine with the stack.
COMPOSE_PROFILES=engine
HTTPS_PORT=8443

MONGO_ROOT_PASSWORD=$(rnd)
LAURENTIA_DB_PASSWORD=$(rnd)
FREKCORE_DB_PASSWORD=$(rnd)

LAURENTIA_ENCRYPTION_KEY=$(rnd)
LAURENTIA_SECRET_SALT=$(rnd)
LAURENTIA_CVLN_SERVICE_API_KEY=$(rnd)

FREK_SECRET_KEY=$(rnd)
FREK_EMAIL_SALT=$(rnd)
FREK_CLIENT_CVLBRAIN_SECRET=$(rnd)
FREK_CLIENT_KILTIKONET_SECRET=$(rnd)

# Model (set by scripts/fetch-model.sh)
MODEL_FILE=
MODEL_ALIAS=local
MODEL_CONTEXT=8192
ENGINE_THREADS=4
ENV
chmod 600 .env
echo "deploy/.env created (600). Keep a copy of LAURENTIA_ENCRYPTION_KEY offline: without it the memory cannot be decrypted."
