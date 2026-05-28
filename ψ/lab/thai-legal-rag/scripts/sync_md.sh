#!/usr/bin/env bash
# Sync data/md_backup/ between local and prod.
#
# Default: copy only (safe — never deletes destination files)
# Add `--delete` flag for true mirror (DANGEROUS: removes files missing on source)
#
# Usage:
#   ./scripts/sync_md.sh push            # local → prod (copy only, no deletion)
#   ./scripts/sync_md.sh pull            # prod → local (copy only, no deletion)
#   ./scripts/sync_md.sh diff            # show what would copy (no deletion in dry-run)
#   ./scripts/sync_md.sh diff --delete   # show what would copy AND delete
#   ./scripts/sync_md.sh push --delete   # local → prod (TRUE MIRROR, deletes orphans)

set -euo pipefail

PROD_HOST="root@31.97.188.155"
PROD_DIR="/app/thai-legal-rag/data/md_backup/"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)/data/md_backup/"
MODE="${1:-}"
DELETE_FLAG=""

if [[ -z "$MODE" ]]; then
  echo "Usage: $0 push|pull|diff [--delete]"
  exit 1
fi

if [[ "${2:-}" == "--delete" ]]; then
  DELETE_FLAG="--delete"
  echo "⚠️  --delete enabled: files missing on source will be REMOVED from destination"
fi

echo "Local : $LOCAL_DIR"
echo "Prod  : ${PROD_HOST}:${PROD_DIR}"
echo ""

case "$MODE" in
  push)
    echo "==> push: local → prod ${DELETE_FLAG}"
    rsync -avz ${DELETE_FLAG} --itemize-changes \
      "$LOCAL_DIR" "${PROD_HOST}:${PROD_DIR}"
    ;;
  pull)
    echo "==> pull: prod → local ${DELETE_FLAG}"
    rsync -avz ${DELETE_FLAG} --itemize-changes \
      "${PROD_HOST}:${PROD_DIR}" "$LOCAL_DIR"
    ;;
  diff)
    echo "==> diff (dry-run) ${DELETE_FLAG}"
    rsync -avz ${DELETE_FLAG} --dry-run --itemize-changes \
      "$LOCAL_DIR" "${PROD_HOST}:${PROD_DIR}"
    ;;
  *)
    echo "Unknown mode: $MODE  (use push|pull|diff)"
    exit 1
    ;;
esac

echo ""
echo "Done."
