"""
Patch file_id + file_url in MD frontmatter using document_list.xlsx as source of truth.

Usage:
    cd ψ/lab/thai-legal-rag
    python3 pipeline/patch_file_ids.py --dry-run     # preview only
    python3 pipeline/patch_file_ids.py               # apply changes
"""
import argparse
import re
import sys
from pathlib import Path

import openpyxl

MD_DIR = Path("data/md_backup")
XLSX_PATH = Path("data/document_list.xlsx")


def build_mapping(xlsx_path: Path) -> dict[str, tuple[str, str]]:
    """Return {original_filename_stem: (file_id, file_url)}."""
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    mapping: dict[str, tuple[str, str]] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        filename = row[0]
        drive_id = row[7]
        if not filename or not drive_id:
            continue
        # Strip .pdf extension → use as key
        stem = Path(str(filename)).stem
        url = f"https://drive.google.com/file/d/{drive_id}/view"
        mapping[stem] = (str(drive_id), url)
    return mapping


def get_original_filename(md_path: Path) -> str | None:
    """Extract original_filename from MD frontmatter."""
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r'^original_filename:\s*["\']?(.+?)["\']?\s*$', text, re.MULTILINE)
    if not m:
        return None
    return Path(m.group(1).strip()).stem


def patch_md(md_path: Path, new_id: str, new_url: str, dry_run: bool) -> bool:
    """Update file_id and file_url in MD frontmatter. Returns True if changed."""
    text = md_path.read_text(encoding="utf-8")
    original = text

    text = re.sub(
        r'^(file_id:\s*)["\']?.*?["\']?\s*$',
        f'file_id: "{new_id}"',
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r'^(file_url:\s*)["\']?.*?["\']?\s*$',
        f'file_url: "{new_url}"',
        text,
        flags=re.MULTILINE,
    )

    if text == original:
        return False

    if not dry_run:
        md_path.write_text(text, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write")
    parser.add_argument("--dir", default=str(MD_DIR), help="MD directory")
    args = parser.parse_args()

    md_dir = Path(args.dir)
    mapping = build_mapping(XLSX_PATH)
    print(f"Loaded {len(mapping)} entries from {XLSX_PATH}")

    changed = 0
    skipped = 0
    not_found = 0

    for md_path in sorted(md_dir.glob("*.md")):
        stem = get_original_filename(md_path)
        if not stem:
            stem = md_path.stem  # fallback: use MD filename as stem

        if stem not in mapping:
            not_found += 1
            continue

        new_id, new_url = mapping[stem]
        did_change = patch_md(md_path, new_id, new_url, dry_run=args.dry_run)

        if did_change:
            changed += 1
            print(f"{'[DRY]' if args.dry_run else '[FIX]'} {md_path.name} → {new_id}")
        else:
            skipped += 1

    print(f"\nDone: {changed} {'would be ' if args.dry_run else ''}changed, {skipped} already correct, {not_found} not in xlsx")


if __name__ == "__main__":
    main()
