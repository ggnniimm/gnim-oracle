#!/usr/bin/env bash
# Deploy a tagged app image to production.
#
# Two modes:
#   registry (default): pull from ghcr.io (fast, recommended)
#   local:              docker save → scp → docker load (fallback, slow ~3GB transfer)
#
# Usage:
#   ./scripts/deploy_image.sh <remote_tag>          # pull from ghcr.io
#   ./scripts/deploy_image.sh --local <local_tag>   # scp local image
#
# Examples:
#   ./scripts/deploy_image.sh ghcr.io/ggnniimm/thai-legal-rag-app:latest
#   ./scripts/deploy_image.sh ghcr.io/ggnniimm/thai-legal-rag-app:sha-abc1234
#   ./scripts/deploy_image.sh --local thai-legal-rag-app:local-20260517-1220-9c05786

set -euo pipefail

PROD_HOST="root@31.97.188.155"
PROD_COMPOSE_DIR="/app/thai-legal-rag"
APP_NAME="thai-legal-rag-app"

MODE="registry"
if [ "${1:-}" = "--local" ]; then
  MODE="local"
  shift
fi

VERSION_TAG="${1:-}"

if [ -z "$VERSION_TAG" ]; then
  echo "Usage: $0 [--local] <image_tag>"
  echo ""
  echo "Registry mode (default, pull from ghcr.io):"
  echo "  $0 ghcr.io/ggnniimm/thai-legal-rag-app:latest"
  echo ""
  echo "Local mode (scp, slow):"
  echo "  $0 --local thai-legal-rag-app:local-20260517-1220-9c05786"
  exit 1
fi

if [ "$MODE" = "registry" ]; then
  echo "==> Pulling $VERSION_TAG on prod ..."
  ssh "$PROD_HOST" "
    docker pull '$VERSION_TAG'
    docker tag '$VERSION_TAG' '${APP_NAME}:latest'
    echo 'Image pulled and tagged as ${APP_NAME}:latest'
  "
else
  # Local mode: verify image exists, save, scp, load
  if ! docker image inspect "$VERSION_TAG" &>/dev/null; then
    echo "ERROR: Image not found locally: $VERSION_TAG"
    echo "       Run scripts/build.sh first."
    exit 1
  fi

  echo "==> Saving image: $VERSION_TAG"
  TMP_TAR="/tmp/${APP_NAME}-$(date +%Y%m%d-%H%M%S).tar"
  docker save "$VERSION_TAG" -o "$TMP_TAR"
  TAR_SIZE=$(du -sh "$TMP_TAR" | cut -f1)
  echo "    Saved: $TMP_TAR ($TAR_SIZE)"

  echo "==> Transferring to prod ($PROD_HOST) ..."
  scp "$TMP_TAR" "${PROD_HOST}:/tmp/$(basename $TMP_TAR)"

  echo "==> Loading image on prod ..."
  REMOTE_TAR="/tmp/$(basename $TMP_TAR)"
  ssh "$PROD_HOST" "
    docker load -i '$REMOTE_TAR'
    docker tag '$VERSION_TAG' '${APP_NAME}:latest'
    rm -f '$REMOTE_TAR'
    echo 'Image loaded and tagged as ${APP_NAME}:latest'
  "

  rm -f "$TMP_TAR"
fi

echo "==> Pushing docker-compose.prod.yml to prod ..."
scp "$(dirname "$0")/../docker-compose.prod.yml" "${PROD_HOST}:${PROD_COMPOSE_DIR}/docker-compose.yml"

echo "==> Restarting app on prod ..."
ssh "$PROD_HOST" "cd $PROD_COMPOSE_DIR && docker compose up -d app"

echo "==> Waiting for app to start ..."
sleep 10

echo "==> Smoke test ..."
HTTP_STATUS=$(ssh "$PROD_HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8501/healthz" 2>/dev/null || echo "000")
echo "    Health check: HTTP $HTTP_STATUS"

if [ "$HTTP_STATUS" = "200" ]; then
  echo "    PASS — app is responding"
else
  echo "    WARNING — unexpected status $HTTP_STATUS (check with: ssh $PROD_HOST 'docker logs thai-legal-rag-app-1 --tail 30')"
fi

echo ""
echo "==> Deploy complete: $VERSION_TAG → prod"
echo "    Prod URL: https://mwaprocure.gnim.cloud"
