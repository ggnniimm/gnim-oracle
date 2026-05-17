#!/usr/bin/env bash
# Smoke test production — health check + Qdrant chunk count.
# Run before and after any deploy to verify prod is healthy.
#
# Usage: ./scripts/prod_smoke.sh [--full]
#   --full   also run a test search query (requires PROD_HOST reachable)

set -euo pipefail

PROD_HOST="root@31.97.188.155"
APP_CONTAINER="thai-legal-rag-app-1"
PROD_URL="https://mwaprocure.gnim.cloud"
FULL=false
for arg in "$@"; do [ "$arg" = "--full" ] && FULL=true; done

PASS=0
FAIL=0

check() {
  local label="$1"
  local result="$2"
  local expected="$3"
  if [ "$result" = "$expected" ]; then
    echo "  ✓  $label: $result"
    (( PASS++ )) || true
  else
    echo "  ❌ $label: got '$result' (expected '$expected')"
    (( FAIL++ )) || true
  fi
}

echo "==> Prod Smoke Test: $PROD_URL"
echo "    $(date '+%Y-%m-%d %H:%M %Z')"
echo ""

# 1. External HTTP check
HTTP_STATUS=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$PROD_URL/healthz" 2>/dev/null || echo "000")
check "HTTP /healthz (external)" "$HTTP_STATUS" "200"

# 2. Internal health check via SSH
INTERNAL_STATUS=$(ssh "$PROD_HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8501/healthz" 2>/dev/null || echo "000")
check "HTTP /healthz (internal)" "$INTERNAL_STATUS" "200"

# 3. App container running
CONTAINER_STATUS=$(ssh "$PROD_HOST" "docker inspect -f '{{.State.Status}}' $APP_CONTAINER" 2>/dev/null || echo "unknown")
check "Container status" "$CONTAINER_STATUS" "running"

# 4. Qdrant chunk count via app container
CHUNK_COUNT=$(ssh "$PROD_HOST" "
  docker exec $APP_CONTAINER python3 -c \"
import urllib.request, json
r = urllib.request.urlopen('http://qdrant:6333/collections/thai_legal_rag')
print(json.load(r)['result']['points_count'])
\"" 2>/dev/null || echo "ERROR")

if [ "$CHUNK_COUNT" = "ERROR" ]; then
  echo "  ❌ Qdrant chunk count: ERROR (could not reach Qdrant)"
  (( FAIL++ )) || true
elif [ "$CHUNK_COUNT" -gt 30000 ] 2>/dev/null; then
  echo "  ✓  Qdrant chunks: $CHUNK_COUNT (expected ~31,927)"
  (( PASS++ )) || true
else
  echo "  ❌ Qdrant chunks: $CHUNK_COUNT (expected >30,000)"
  (( FAIL++ )) || true
fi

# 5. Full mode: test query
if [ "$FULL" = true ]; then
  echo ""
  echo "  [Full mode] Running test query ..."
  QUERY_STATUS=$(ssh "$PROD_HOST" "
    docker exec $APP_CONTAINER python3 -c \"
import urllib.request, json
data = json.dumps({'query': 'ค่าปรับ', 'top_k': 1}).encode()
req = urllib.request.Request(
  'http://localhost:8501/api/search',
  data=data, method='POST',
  headers={'Content-Type': 'application/json'}
)
try:
  r = urllib.request.urlopen(req, timeout=10)
  print('OK')
except Exception as e:
  print(f'FAIL: {e}')
\"" 2>/dev/null || echo "SKIP")
  echo "  ℹ️  Test query: $QUERY_STATUS"
fi

echo ""
echo "==> Result: $PASS passed, $FAIL failed"

if [ $FAIL -eq 0 ]; then
  echo "    PASS — prod is healthy"
  exit 0
else
  echo "    FAIL — check logs: ssh $PROD_HOST 'docker logs $APP_CONTAINER --tail 50'"
  exit 1
fi
