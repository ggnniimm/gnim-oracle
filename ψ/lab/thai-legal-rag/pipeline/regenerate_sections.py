"""
Regenerate per-section MD files from existing OCR cache.

Uses cached JSON (no re-OCR, no API calls) to write
  {MD_BACKUP_DIR}/{stem}/มาตรา_XXX.md  for every cached law.

Usage:
    python pipeline/regenerate_sections.py            # all cached laws
    python pipeline/regenerate_sections.py --dry-run  # list only, no write
    python pipeline/regenerate_sections.py --resplit   # re-run Gemini วรรค splitting + update cache
    python pipeline/regenerate_sections.py --re-ref    # re-extract cross-references + update cache
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure src/ is importable when run from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import OCR_CACHE_DIR
from src.ingestion.law_extractor import (
    LawDocument,
    LawSection,
    _extract_references,
    _save_section_files,
    _split_paragraphs,
)


def _load_doc_from_cache(cache_file: Path) -> LawDocument:
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    sections = []
    for s in data["sections"]:
        s.setdefault("references", [])
        sections.append(LawSection(**s))
    return LawDocument(
        filename=data["filename"],
        file_id=data["file_id"],
        law_name=data["law_name"],
        law_short_name=data["law_short_name"],
        law_type=data["law_type"],
        law_year_be=data["law_year_be"],
        sections=sections,
        full_text=data.get("full_text", ""),
        ocr_engine=data.get("ocr_engine", ""),
        total_sections=data.get("total_sections", len(sections)),
    )


def _resplit_and_update_cache(cache_file: Path, doc: LawDocument) -> int:
    """Re-run _split_paragraphs on all sections and update the cache JSON.

    Returns number of sections whose paragraph count changed.
    """
    changed = 0
    for sec in doc.sections:
        old_count = len(sec.paragraphs)
        sec.paragraphs = _split_paragraphs(sec.text)
        if len(sec.paragraphs) != old_count:
            changed += 1

    # Write back to cache
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    for i, sec in enumerate(doc.sections):
        data["sections"][i]["paragraphs"] = sec.paragraphs
    cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def _reref_and_update_cache(cache_file: Path, doc: LawDocument) -> int:
    """Re-extract cross-references on all sections and update the cache JSON.

    Returns number of sections whose references changed.
    """
    changed = 0
    for sec in doc.sections:
        old_refs = sec.references
        sec.references = _extract_references(sec.text, sec.number)
        if sec.references != old_refs:
            changed += 1

    # Write back to cache
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    for i, sec in enumerate(doc.sections):
        data["sections"][i]["references"] = sec.references
    cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate per-section MD files from cache")
    parser.add_argument("--dry-run", action="store_true", help="List files only, no write")
    parser.add_argument("--resplit", action="store_true",
                        help="Re-run Gemini วรรค splitting and update cache JSON")
    parser.add_argument("--re-ref", action="store_true",
                        help="Re-extract cross-references and update cache JSON")
    args = parser.parse_args()

    cache_files = sorted(OCR_CACHE_DIR.glob("law_*.json"))
    if not cache_files:
        print(f"No law cache files found in {OCR_CACHE_DIR}")
        return

    print(f"Found {len(cache_files)} cached law(s)\n")

    for cf in cache_files:
        doc = _load_doc_from_cache(cf)
        section_count = len(doc.sections)
        print(f"  {doc.law_short_name or doc.law_name}  ({section_count} sections)")

        if args.resplit and not args.dry_run:
            changed = _resplit_and_update_cache(cf, doc)
            print(f"    resplit: {changed} sections changed paragraph count")

        if args.re_ref and not args.dry_run:
            changed = _reref_and_update_cache(cf, doc)
            print(f"    re-ref: {changed} sections changed references")

        if not args.dry_run:
            out_dir = _save_section_files(doc)
            print(f"    → {out_dir}")

    if args.dry_run:
        print("\n[dry-run] no files written")
    else:
        print("\nDone.")


if __name__ == "__main__":
    main()
