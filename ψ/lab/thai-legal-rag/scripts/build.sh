#!/usr/bin/env bash
# Build the thai-legal-rag app image with a version tag.
# Also tags as :latest so docker compose up picks it up.
#
# Usage: ./scripts/build.sh [extra docker build args]
# Output: prints the full version tag

set -euo pipefail

APP_NAME="thai-legal-rag-app"
GIT_SHA=$(git rev-parse --short HEAD)
TIMESTAMP=$(date +%Y%m%d-%H%M)
VERSION_TAG="${APP_NAME}:v${TIMESTAMP}-${GIT_SHA}"

echo "==> Building image: $VERSION_TAG"
docker build --platform linux/amd64 -t "$VERSION_TAG" -t "${APP_NAME}:latest" "$@" .
echo ""
echo "==> Build complete."
echo "    Version tag: $VERSION_TAG"
echo "    Latest tag:  ${APP_NAME}:latest"
echo ""
echo "VERSION_TAG=$VERSION_TAG"
