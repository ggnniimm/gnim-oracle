#!/usr/bin/env bash
# Export a Qdrant snapshot of thai_legal_rag collection from local Qdrant.
# Run this before any Qdrant version upgrade or data-destructive operation.
#
# Usage: ./scripts/snapshot_export.sh
# Output: prints path to the .snapshot file in qdrant_data volume

set -euo pipefail

COLLECTION="thai_legal_rag"
QDRANT_URL="http://localhost:6333"
COMPOSE_PROJECT="thai-legal-rag"

echo "==> Creating snapshot for collection: $COLLECTION"
RESPONSE=$(curl -sf -X POST "$QDRANT_URL/collections/$COLLECTION/snapshots")
SNAPSHOT_NAME=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['name'])")
echo "    Snapshot created: $SNAPSHOT_NAME"

# Find Qdrant container name
QDRANT_CONTAINER=$(docker ps --filter "name=${COMPOSE_PROJECT}-qdrant" --format "{{.Names}}" | head -1)
if [ -z "$QDRANT_CONTAINER" ]; then
  echo "ERROR: Qdrant container not found (looking for ${COMPOSE_PROJECT}-qdrant-*)"
  exit 1
fi

CONTAINER_SNAPSHOT="/qdrant/snapshots/$COLLECTION/$SNAPSHOT_NAME"
EXPORT_DIR="$(pwd)/data/snapshots"
mkdir -p "$EXPORT_DIR"
LOCAL_PATH="$EXPORT_DIR/$SNAPSHOT_NAME"

echo "    Copying from container $QDRANT_CONTAINER ..."
docker cp "$QDRANT_CONTAINER:$CONTAINER_SNAPSHOT" "$LOCAL_PATH"

SNAPSHOT_SIZE=$(du -sh "$LOCAL_PATH" | cut -f1)
echo "    Size: $SNAPSHOT_SIZE"
echo "    Saved: $LOCAL_PATH"
echo ""
echo "==> Snapshot export complete."
echo "SNAPSHOT_PATH=$LOCAL_PATH"
