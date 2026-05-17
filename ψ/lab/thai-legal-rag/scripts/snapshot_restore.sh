#!/usr/bin/env bash
# Restore a Qdrant snapshot into the local (or remote) Qdrant instance.
# Deletes the existing collection first, then restores from snapshot file.
#
# Usage:
#   ./scripts/snapshot_restore.sh <snapshot_file>        # restore to local
#   ./scripts/snapshot_restore.sh <snapshot_file> prod   # restore to prod (via SSH)
#
# The snapshot file must be accessible from the Qdrant container.

set -euo pipefail

SNAPSHOT_FILE="${1:-}"
TARGET="${2:-local}"
COLLECTION="thai_legal_rag"

if [ -z "$SNAPSHOT_FILE" ]; then
  echo "Usage: $0 <snapshot_file> [local|prod]"
  exit 1
fi

if [ ! -f "$SNAPSHOT_FILE" ]; then
  echo "ERROR: Snapshot file not found: $SNAPSHOT_FILE"
  exit 1
fi

SNAPSHOT_NAME=$(basename "$SNAPSHOT_FILE")

if [ "$TARGET" = "prod" ]; then
  PROD_HOST="root@31.97.188.155"
  QDRANT_URL="http://localhost:6333"
  QDRANT_CONTAINER="thai-legal-rag-qdrant-1"
  REMOTE_SNAPSHOT="/tmp/$SNAPSHOT_NAME"

  echo "==> Copying snapshot to prod ($PROD_HOST) ..."
  scp "$SNAPSHOT_FILE" "${PROD_HOST}:${REMOTE_SNAPSHOT}"

  echo "==> Uploading snapshot to prod Qdrant ..."
  ssh "$PROD_HOST" "
    curl -sf -X PUT '${QDRANT_URL}/collections/${COLLECTION}/snapshots/upload?priority=snapshot' \
      -H 'Content-Type: multipart/form-data' \
      -F 'snapshot=@${REMOTE_SNAPSHOT}' | python3 -c \"import json,sys; r=json.load(sys.stdin); print('Upload result:', r.get('result', r))\"
    rm -f '${REMOTE_SNAPSHOT}'
  "

  echo "==> Verifying chunk count on prod ..."
  sleep 10
  ssh "$PROD_HOST" "curl -s 'http://localhost:6333/collections/${COLLECTION}'" | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print('Prod chunks:', d['result']['points_count'])"

else
  QDRANT_URL="http://localhost:6333"
  QDRANT_CONTAINER="thai-legal-rag-qdrant-1"
  CONTAINER_SNAPSHOT="/tmp/$SNAPSHOT_NAME"

  echo "==> Copying snapshot into container ..."
  docker cp "$SNAPSHOT_FILE" "${QDRANT_CONTAINER}:${CONTAINER_SNAPSHOT}"

  echo "==> Uploading snapshot to local Qdrant ..."
  curl -sf -X PUT "${QDRANT_URL}/collections/${COLLECTION}/snapshots/upload?priority=snapshot" \
    -H 'Content-Type: multipart/form-data' \
    -F "snapshot=@${SNAPSHOT_FILE}" | \
    python3 -c "import json,sys; r=json.load(sys.stdin); print('Upload result:', r.get('result', r))"

  echo "==> Verifying chunk count ..."
  sleep 5
  curl -s "${QDRANT_URL}/collections/${COLLECTION}" | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print('Local chunks:', d['result']['points_count'])"
fi

echo ""
echo "==> Snapshot restore complete."
