#!/usr/bin/env bash
# Sync data/md_backup/ between local and prod.
#
# Usage:
#   ./scripts/sync_md.sh push   # local → prod  (after editing MDs locally)
#   ./scripts/sync_md.sh pull   # prod → local  (if prod was edited directly)
#   ./scripts/sync_md.sh diff   # show what differs (dry-run)

set -euo pipefail

PROD_HOST="root@31.97.188.155"
PROD_DIR="/app/thai-legal-rag/data/md_backup/"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)/data/md_backup/"
MODE="${1:-}"

if [[ -z "$MODE" ]]; then
  echo "Usage: $0 push|pull|diff"
  exit 1
fi

echo "Local : $LOCAL_DIR"
echo "Prod  : ${PROD_HOST}:${PROD_DIR}"
echo ""

case "$MODE" in
  push)
    echo "==> push: local → prod"
    rsync -avz --delete --itemize-changes \
      "$LOCAL_DIR" "${PROD_HOST}:${PROD_DIR}"
    ;;
  pull)
    echo "==> pull: prod → local"
    rsync -avz --delete --itemize-changes \
      "${PROD_HOST}:${PROD_DIR}" "$LOCAL_DIR"
    ;;
  diff)
    echo "==> diff (dry-run)"
    rsync -avz --delete --dry-run --itemize-changes \
      "$LOCAL_DIR" "${PROD_HOST}:${PROD_DIR}"
    ;;
  *)
    echo "Unknown mode: $MODE  (use push|pull|diff)"
    exit 1
    ;;
esac

echo ""
echo "Done."
