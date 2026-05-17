#!/usr/bin/env bash
# Deploy a tagged app image to production.
# Saves image locally → scp → load on prod → compose up.
#
# Usage: ./scripts/deploy_image.sh <version_tag>
# Example: ./scripts/deploy_image.sh thai-legal-rag-app:v20260517-1205-3c0f72a
#
# Prerequisites:
#   - Image must exist locally (run scripts/build.sh first)
#   - SSH access to root@31.97.188.155
#   - Prod docker-compose.yml must use `image: thai-legal-rag-app:latest`

set -euo pipefail

VERSION_TAG="${1:-}"
PROD_HOST="root@31.97.188.155"
PROD_COMPOSE_DIR="/app/thai-legal-rag"
APP_NAME="thai-legal-rag-app"

if [ -z "$VERSION_TAG" ]; then
  echo "Usage: $0 <version_tag>"
  echo "Example: $0 thai-legal-rag-app:v20260517-1205-3c0f72a"
  exit 1
fi

# Verify image exists locally
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

rm -f "$TMP_TAR"
echo ""
echo "==> Deploy complete: $VERSION_TAG → prod"
echo "    Prod URL: https://mwaprocure.gnim.cloud"
