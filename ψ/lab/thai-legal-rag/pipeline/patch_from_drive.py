"""Patch MD file_ids + Qdrant payloads using real Drive file listing.

Usage:
    cd ψ/lab/thai-legal-rag
    python3 pipeline/patch_from_drive.py
    QDRANT_URL=http://localhost:6333 python3 pipeline/patch_from_drive.py --qdrant
"""
import argparse
import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path

import requests

MAPPING_PATH = Path(os.environ.get("MAPPING_PATH", "/tmp/drive_mapping.json"))
MD_DIR = Path("data/md_backup")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = "thai_legal_rag"


def load_mapping():
    with open(MAPPING_PATH) as f:
        return json.load(f)


def _normalize(stem: str) -> str:
    """Normalize stem for fuzzy matching: remove corruption chars, unify separators."""
    s = re.sub(r"[\ufffd\x00-\x1f]", "", stem)  # remove replacement + control chars
    s = s.replace("+", "_")                        # Drive uses + where MD uses _
    return s


def _build_fuzzy_index(mapping: dict) -> dict:
    """Build normalized_stem -> entry lookup."""
    return {_normalize(stem): entry for stem, entry in mapping.items()}


def patch_md_files(mapping: dict) -> tuple[int, int, int]:
    fuzzy = _build_fuzzy_index(mapping)
    changed = skipped = not_found = 0
    for md_path in sorted(MD_DIR.glob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        m = re.search(r"^original_filename:\s*[\"']?(.+?)[\"']?\s*$", text, re.MULTILINE)
        stem = Path(m.group(1).strip()).stem if m else md_path.stem
        # Exact match first, then fuzzy
        entry = mapping.get(stem) or fuzzy.get(_normalize(stem))
        if not entry:
            not_found += 1
            continue
        new_id, new_url = entry["file_id"], entry["file_url"]
        original = text
        text = re.sub(r'^file_id:\s*["\']?.*?["\']?\s*$', f'file_id: "{new_id}"', text, flags=re.MULTILINE)
        text = re.sub(r'^file_url:\s*["\']?.*?["\']?\s*$', f'file_url: "{new_url}"', text, flags=re.MULTILINE)
        if text != original:
            md_path.write_text(text, encoding="utf-8")
            changed += 1
        else:
            skipped += 1
    return changed, skipped, not_found


def get_key(payload):
    for f in ("original_filename", "source_name", "source"):
        v = payload.get(f)
        if v:
            return Path(str(v)).stem
    return None


def set_payload_batch(ids, payload, retries=5):
    body = {"payload": payload, "points": ids}
    for attempt in range(retries):
        try:
            r = requests.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/payload", json=body, timeout=60)
            r.raise_for_status()
            return
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def patch_qdrant(mapping: dict):
    fuzzy = _build_fuzzy_index(mapping)
    changed = skipped = not_found = 0
    offset = None
    batch_num = 0
    while True:
        body = {"limit": 200, "with_payload": True, "with_vector": False}
        if offset:
            body["offset"] = offset
        resp = requests.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll", json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()["result"]
        points = data["points"]
        if not points:
            break
        batch_num += 1
        groups: dict[tuple, list] = defaultdict(list)
        for p in points:
            payload = p.get("payload") or {}
            key = get_key(payload)
            if not key:
                not_found += 1
                continue
            entry = mapping.get(key) or fuzzy.get(_normalize(key))
            if not entry:
                not_found += 1
                continue
            if payload.get("file_url") == entry["file_url"]:
                skipped += 1
                continue
            groups[(entry["file_id"], entry["file_url"])].append(p["id"])
        total = sum(len(v) for v in groups.values())
        changed += total
        print(f"  Batch {batch_num}: {len(points)} pts → {total} update", flush=True)
        for (fid, furl), ids in groups.items():
            for i in range(0, len(ids), 10):
                set_payload_batch(ids[i:i+10], {"file_id": fid, "file_url": furl})
                time.sleep(0.05)
        offset = data.get("next_page_offset")
        if not offset:
            break
    print(f"Qdrant: {changed} patched, {skipped} already correct, {not_found} not in mapping")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qdrant", action="store_true", help="Also patch Qdrant")
    args = parser.parse_args()

    mapping = load_mapping()
    print(f"Loaded {len(mapping)} Drive entries")

    print("Patching MD files...")
    changed, skipped, not_found = patch_md_files(mapping)
    print(f"MD: {changed} changed, {skipped} already correct, {not_found} not in Drive")

    if args.qdrant:
        print("Patching Qdrant...")
        patch_qdrant(mapping)


if __name__ == "__main__":
    main()
