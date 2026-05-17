#!/usr/bin/env bash
# Deploy local Qdrant data to production via snapshot.
# Exports snapshot from local → scp → restore on prod.
#
# Usage: ./scripts/deploy_data.sh [snapshot_file]
#   If no snapshot_file given, creates a fresh export first.
#
# Prerequisites:
#   - Local Qdrant running at localhost:6333
#   - SSH access to root@31.97.188.155
#   - Prod Qdrant accessible at localhost:6333 on prod host (via docker network)

set -euo pipefail

PROD_HOST="root@31.97.188.155"
COLLECTION="thai_legal_rag"

SNAPSHOT_FILE="${1:-}"

if [ -z "$SNAPSHOT_FILE" ]; then
  echo "==> No snapshot file specified — creating fresh export ..."
  SNAPSHOT_OUTPUT=$(bash "$(dirname "$0")/snapshot_export.sh")
  SNAPSHOT_FILE=$(echo "$SNAPSHOT_OUTPUT" | grep "^SNAPSHOT_PATH=" | cut -d= -f2)
  echo "    Using: $SNAPSHOT_FILE"
fi

if [ ! -f "$SNAPSHOT_FILE" ]; then
  echo "ERROR: Snapshot file not found: $SNAPSHOT_FILE"
  exit 1
fi

SNAPSHOT_NAME=$(basename "$SNAPSHOT_FILE")
SNAPSHOT_SIZE=$(du -sh "$SNAPSHOT_FILE" | cut -f1)
echo "==> Snapshot: $SNAPSHOT_NAME ($SNAPSHOT_SIZE)"

# Get local chunk count for verification
LOCAL_CHUNKS=$(curl -s "http://localhost:6333/collections/$COLLECTION" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['result']['points_count'])")
echo "    Local chunks: $LOCAL_CHUNKS"

echo "==> Copying snapshot to prod ..."
scp "$SNAPSHOT_FILE" "${PROD_HOST}:/tmp/$SNAPSHOT_NAME"

echo "==> Uploading snapshot to prod Qdrant ..."
ssh "$PROD_HOST" "
  curl -sf -X PUT 'http://localhost:6333/collections/${COLLECTION}/snapshots/upload?priority=snapshot' \
    -H 'Content-Type: multipart/form-data' \
    -F 'snapshot=@/tmp/${SNAPSHOT_NAME}' | \
    python3 -c \"import json,sys; r=json.load(sys.stdin); print('Upload result:', r.get('result', r))\"
  rm -f '/tmp/${SNAPSHOT_NAME}'
"

echo "==> Waiting for restore to complete ..."
sleep 15

echo "==> Verifying chunk count on prod ..."
PROD_CHUNKS=$(ssh "$PROD_HOST" "curl -s 'http://localhost:6333/collections/${COLLECTION}'" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null || echo "ERROR")

echo "    Prod chunks:  $PROD_CHUNKS"
echo "    Local chunks: $LOCAL_CHUNKS"

if [ "$PROD_CHUNKS" = "$LOCAL_CHUNKS" ]; then
  echo "    PASS — chunk counts match"
else
  echo "    WARNING — counts differ (prod may still be indexing, or restore failed)"
  echo "    Check: ssh $PROD_HOST 'curl -s http://localhost:6333/collections/${COLLECTION}'"
fi

echo ""
echo "==> Data deploy complete."
