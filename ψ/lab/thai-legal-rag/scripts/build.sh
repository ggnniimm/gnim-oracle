#!/usr/bin/env bash
# Build the thai-legal-rag app image with a version tag.
# Also tags :latest (local) and optionally pushes to ghcr.io.
#
# Usage: ./scripts/build.sh [--push] [extra docker build args]
#   --push   push to ghcr.io after build (requires docker login ghcr.io)
# Output: prints the full version tag

set -euo pipefail

REGISTRY="ghcr.io/ggnniimm"
APP_NAME="thai-legal-rag-app"
GIT_SHA=$(git rev-parse --short HEAD)
TIMESTAMP=$(date +%Y%m%d-%H%M)
LOCAL_TAG="${APP_NAME}:local-${TIMESTAMP}-${GIT_SHA}"
REMOTE_TAG="${REGISTRY}/${APP_NAME}:local-${TIMESTAMP}-${GIT_SHA}"

PUSH=false
EXTRA_ARGS=()
for arg in "$@"; do
  if [ "$arg" = "--push" ]; then
    PUSH=true
  else
    EXTRA_ARGS+=("$arg")
  fi
done

echo "==> Building image: $LOCAL_TAG"
docker build --platform linux/amd64 \
  -t "$LOCAL_TAG" \
  -t "${APP_NAME}:latest" \
  -t "$REMOTE_TAG" \
  "${EXTRA_ARGS[@]}" .

echo ""
echo "==> Build complete."
echo "    Local tag:  $LOCAL_TAG"
echo "    Remote tag: $REMOTE_TAG"
echo ""

if [ "$PUSH" = true ]; then
  echo "==> Pushing to ghcr.io ..."
  docker push "$REMOTE_TAG"
  echo "    Pushed: $REMOTE_TAG"
fi

echo "VERSION_TAG=$LOCAL_TAG"
echo "REMOTE_TAG=$REMOTE_TAG"
