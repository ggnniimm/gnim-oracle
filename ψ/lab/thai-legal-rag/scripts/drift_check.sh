#!/usr/bin/env bash
# Check if prod source files have drifted from local git.
# Compares key src/ files between local and prod container.
#
# Exit code: 0 = no drift, 1 = drift detected, 2 = error
#
# Usage: ./scripts/drift_check.sh [--quiet]
#   --quiet   only print drifted files (no details), useful for pre-deploy check

set -euo pipefail

PROD_HOST="root@31.97.188.155"
APP_CONTAINER="thai-legal-rag-app-1"
QUIET=false
for arg in "$@"; do [ "$arg" = "--quiet" ] && QUIET=true; done

# Key files to check — the ones most likely to drift
WATCH_FILES=(
  "src/config.py"
  "src/ingestion/md_loader.py"
  "src/retrieval/reranker.py"
  "src/retrieval/retriever.py"
  "src/retrieval/glossary.py"
  "src/generation/generator.py"
  "src/gemini_client.py"
  "app/streamlit_app.py"
)

echo "==> Drift Check: local vs prod ($APP_CONTAINER)"
echo "    $(date '+%Y-%m-%d %H:%M %Z')"
echo ""

DRIFT_COUNT=0
ERROR_COUNT=0

for FILE in "${WATCH_FILES[@]}"; do
  # Get prod version via docker exec
  PROD_CONTENT=$(ssh "$PROD_HOST" "docker exec $APP_CONTAINER cat /app/$FILE" 2>/dev/null || echo "__ERROR__")

  if [ "$PROD_CONTENT" = "__ERROR__" ]; then
    echo "  ⚠️  ERROR: could not read prod/$FILE"
    (( ERROR_COUNT++ )) || true
    continue
  fi

  LOCAL_CONTENT=$(cat "$FILE" 2>/dev/null || echo "__MISSING__")

  if [ "$LOCAL_CONTENT" = "__MISSING__" ]; then
    echo "  ⚠️  MISSING locally: $FILE"
    (( ERROR_COUNT++ )) || true
    continue
  fi

  if [ "$PROD_CONTENT" != "$LOCAL_CONTENT" ]; then
    (( DRIFT_COUNT++ )) || true
    if [ "$QUIET" = true ]; then
      echo "  ❌ DRIFT: $FILE"
    else
      echo "  ❌ DRIFT: $FILE"
      diff <(echo "$LOCAL_CONTENT") <(echo "$PROD_CONTENT") \
        | head -30 \
        | sed 's/^/      /'
      echo ""
    fi
  else
    [ "$QUIET" = false ] && echo "  ✓  OK:    $FILE"
  fi
done

echo ""
if [ $DRIFT_COUNT -eq 0 ] && [ $ERROR_COUNT -eq 0 ]; then
  echo "==> PASS — no drift detected (${#WATCH_FILES[@]} files checked)"
  exit 0
elif [ $DRIFT_COUNT -gt 0 ]; then
  echo "==> DRIFT DETECTED — $DRIFT_COUNT file(s) differ from local"
  echo ""
  echo "    Options:"
  echo "    1. Deploy new image:  bash scripts/build.sh && bash scripts/deploy_image.sh <tag>"
  echo "    2. Emergency patch:   see EMERGENCY.md"
  exit 1
else
  echo "==> ERROR — $ERROR_COUNT file(s) could not be read (check SSH / container)"
  exit 2
fi
