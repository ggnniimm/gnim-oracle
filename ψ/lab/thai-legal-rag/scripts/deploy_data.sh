#!/usr/bin/env bash
# Deploy local Qdrant data to production via snapshot.
# Exports snapshot from local → scp → restore on prod.
#
# Qdrant on prod is on internal Docker network (not exposed to host).
# Upload goes through the app container (docker exec), which can reach
# http://qdrant:6333 on the internal network.
#
# Usage: ./scripts/deploy_data.sh [snapshot_file]
#   If no snapshot_file given, creates a fresh export first.

set -euo pipefail

PROD_HOST="root@31.97.188.155"
COLLECTION="thai_legal_rag"
APP_CONTAINER="thai-legal-rag-app-1"
QDRANT_CONTAINER="thai-legal-rag-qdrant-1"

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

echo "==> Copying snapshot into Qdrant container ..."
ssh "$PROD_HOST" "
  docker exec ${QDRANT_CONTAINER} mkdir -p /qdrant/snapshots/${COLLECTION}
  docker cp /tmp/$SNAPSHOT_NAME ${QDRANT_CONTAINER}:/qdrant/snapshots/${COLLECTION}/${SNAPSHOT_NAME}
  rm -f /tmp/${SNAPSHOT_NAME}
  echo 'Snapshot copied into container'
"

echo "==> Triggering restore via app container ..."
ssh "$PROD_HOST" "
  docker exec $APP_CONTAINER python3 -c \"
import urllib.request, json, time

QDRANT = 'http://qdrant:6333'
COLLECTION = '${COLLECTION}'
SNAPSHOT = '${SNAPSHOT_NAME}'

# Trigger recovery using file:// path (Qdrant container's filesystem)
location = f'file:///qdrant/snapshots/{COLLECTION}/{SNAPSHOT}'
url = f'{QDRANT}/collections/{COLLECTION}/snapshots/recover'
payload = json.dumps({'location': location, 'priority': 'snapshot'}).encode()
req = urllib.request.Request(url, data=payload, method='PUT',
  headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.load(resp)
print('Restore triggered:', result.get('result', result))
\"
"

echo "==> Waiting for restore to complete ..."
sleep 20

echo "==> Verifying chunk count on prod ..."
PROD_CHUNKS=$(ssh "$PROD_HOST" "
  docker exec $APP_CONTAINER python3 -c \"
import urllib.request, json
r = urllib.request.urlopen('http://qdrant:6333/collections/thai_legal_rag')
d = json.load(r)
print(d['result']['points_count'])
\"" 2>/dev/null || echo "ERROR")

echo "    Prod chunks:  $PROD_CHUNKS"
echo "    Local chunks: $LOCAL_CHUNKS"

if [ "$PROD_CHUNKS" = "$LOCAL_CHUNKS" ]; then
  echo "    PASS — chunk counts match ✓"
else
  echo "    WARNING — counts differ (prod may still restoring, check in 30s)"
fi

echo ""
echo "==> Data deploy complete."
