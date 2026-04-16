"""
Patch file_id + file_url in Qdrant payloads using document_list.xlsx.
Uses REST API directly (avoids qdrant_client version issues).

Usage:
    cd ψ/lab/thai-legal-rag
    QDRANT_URL=http://localhost:6333 python3 pipeline/patch_qdrant_file_urls.py --dry-run
    QDRANT_URL=http://localhost:6333 python3 pipeline/patch_qdrant_file_urls.py
"""
import argparse
import os
import sys
import time
from pathlib import Path
from collections import defaultdict

import requests
import openpyxl

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = "thai_legal_rag"
XLSX_PATH = Path("data/document_list.xlsx")


def build_mapping(xlsx_path: Path) -> dict[str, tuple[str, str]]:
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    mapping: dict[str, tuple[str, str]] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        filename = row[0]
        drive_id = row[7]
        if not filename or not drive_id:
            continue
        stem = Path(str(filename)).stem
        url = f"https://drive.google.com/file/d/{drive_id}/view"
        mapping[stem] = (str(drive_id), url)
    return mapping


def get_lookup_key(payload: dict) -> str | None:
    for field in ("original_filename", "source_name", "source"):
        val = payload.get(field)
        if val:
            return Path(str(val)).stem
    return None


def scroll_all(url: str, collection: str, batch_size: int = 200):
    """Yield all points via REST scroll API."""
    next_offset = None
    while True:
        body: dict = {"limit": batch_size, "with_payload": True, "with_vector": False}
        if next_offset is not None:
            body["offset"] = next_offset
        resp = requests.post(f"{url}/collections/{collection}/points/scroll", json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()["result"]
        points = data["points"]
        yield points
        next_offset = data.get("next_page_offset")
        if not next_offset or not points:
            break


def set_payload_batch(url: str, collection: str, point_ids: list, payload: dict, retries: int = 5):
    body = {"payload": payload, "points": point_ids}
    for attempt in range(retries):
        try:
            resp = requests.post(f"{url}/collections/{collection}/points/payload", json=body, timeout=60)
            resp.raise_for_status()
            return
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"    Retry {attempt+1}/{retries} after {wait}s: {e}")
            time.sleep(wait)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()

    mapping = build_mapping(XLSX_PATH)
    print(f"Loaded {len(mapping)} entries from xlsx")
    print(f"Qdrant: {QDRANT_URL}/{COLLECTION}")

    changed = 0
    skipped = 0
    not_found = 0
    batch_num = 0

    for points in scroll_all(QDRANT_URL, COLLECTION, batch_size=args.batch_size):
        batch_num += 1

        # Collect updates grouped by (new_id, new_url)
        groups: dict[tuple, list] = defaultdict(list)
        for point in points:
            payload = point.get("payload") or {}
            key = get_lookup_key(payload)
            if not key or key not in mapping:
                not_found += 1
                continue
            new_id, new_url = mapping[key]
            old_url = payload.get("file_url", "")
            if old_url == new_url:
                skipped += 1
                continue
            groups[(new_id, new_url)].append(point["id"])

        total_in_batch = sum(len(v) for v in groups.values())
        changed += total_in_batch
        print(f"  Batch {batch_num}: {len(points)} points → {total_in_batch} to update")

        if not args.dry_run:
            for (new_id, new_url), ids in groups.items():
                # Split into sub-batches of 10
                for i in range(0, len(ids), 10):
                    chunk = ids[i:i+10]
                    set_payload_batch(QDRANT_URL, COLLECTION, chunk, {"file_id": new_id, "file_url": new_url})
                    time.sleep(0.05)

    print(f"\nDone: {changed} {'would be ' if args.dry_run else ''}patched, {skipped} already correct, {not_found} not in xlsx")


if __name__ == "__main__":
    main()
