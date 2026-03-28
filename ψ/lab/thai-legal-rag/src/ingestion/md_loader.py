"""
Load pre-processed MD files (with YAML frontmatter) into chunks.
Used when MD files already exist (e.g. from existing thai-rag-poc OCR output).

MD format expected:
---
source_file: xxx.pdf
type: ข้อหารือ กวจ.
date: "2023-10-03"
ref_number: "ที่ กค (กวจ) 0405.4/35985"
topic: "..."
tags: [...]
law_section: [...]
file_id: "..."
file_url: "..."
---

# Title
## Section
...
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

import yaml

from src.ingestion.chunker import ThaiTextSplitter, Chunk, CHUNK_SIZE, CHUNK_OVERLAP
from src.ingestion.law_extractor import LawDocument, _parse_sections, _detect_law_meta
from src.ingestion.chunker_law import chunk_law_document


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Remove ASCII control characters (except tab \x09, newline \x0a, carriage return \x0d)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Old format: YAML keys directly (no --- delimiters), blank line, then # heading
_OLD_FRONTMATTER_RE = re.compile(r"^((?:[^\n]+\n)+)\n(#)", re.DOTALL)
# Hybrid format: YAML keys with no opening ---, only a closing --- line
_HYBRID_FRONTMATTER_RE = re.compile(r"^((?:[^\n]+\n)+)---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (meta, body).

    Supports two formats:
      1. Standard: ---\\nkey: val\\n---\\n body
      2. Legacy:   key: val\\n\\n# Title body (no --- delimiters)
    """
    # Format 1: standard ---...--- frontmatter
    m = _FRONTMATTER_RE.match(text)
    if m:
        try:
            yaml_block = _CONTROL_CHARS_RE.sub("", m.group(1))
            meta = yaml.safe_load(yaml_block) or {}
        except yaml.YAMLError:
            meta = {}
        body = text[m.end():]
        return meta, body

    # Format 2: hybrid — YAML lines then closing --- (no opening ---)
    m2 = _HYBRID_FRONTMATTER_RE.match(text)
    if m2:
        try:
            yaml_block = _CONTROL_CHARS_RE.sub("", m2.group(1))
            meta = yaml.safe_load(yaml_block) or {}
        except yaml.YAMLError:
            meta = {}
        body = text[m2.end():]
        return meta, body

    # Format 3: legacy — YAML lines followed by blank line + # heading
    m3 = _OLD_FRONTMATTER_RE.match(text)
    if m3:
        try:
            yaml_block = _CONTROL_CHARS_RE.sub("", m3.group(1))
            meta = yaml.safe_load(yaml_block) or {}
        except yaml.YAMLError:
            meta = {}
        # body starts at the # character
        body = text[m3.start(2):]
        return meta, body

    return {}, text


def _section_chunks(body: str, base_meta: dict) -> list[Chunk]:
    """
    Split body by ## sections first, then chunk each section.
    This keeps legal sections (ข้อเท็จจริง, ข้อวินิจฉัย, etc.) coherent.
    """
    splitter = ThaiTextSplitter(chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    chunks: list[Chunk] = []
    chunk_index = 0

    # Split by ## headers
    sections = re.split(r"\n(##[^#].*?)\n", body)
    current_section = "เนื้อหา"

    for part in sections:
        part = part.strip()
        if not part:
            continue

        if part.startswith("##"):
            # Strip markdown and emoji
            current_section = re.sub(r"^#+\s*", "", part)
            current_section = re.sub(r"[^\u0e00-\u0e7f\w\s\./\-()]", "", current_section).strip()
            continue

        # Chunk this section's text
        section_meta = {**base_meta, "section": current_section}
        section_chunks = splitter.split(part, base_metadata=section_meta)

        # Re-index sequentially
        for chunk in section_chunks:
            chunk.metadata["chunk_index"] = chunk_index
            chunks.append(chunk)
            chunk_index += 1

    return chunks


def _is_law_file(meta: dict, filename: str) -> bool:
    """Detect if this file is a law/regulation (พ.ร.บ. or ระเบียบ) that should use section-aware chunking.

    Avoids false positives from ข้อหารือ files that merely reference laws in their filename
    (e.g. "ข้อหารือตามระเบียบกระทรวงการคลังฯ").
    """
    cat = (meta.get("type") or meta.get("doc_type") or "").strip()
    if cat == "กฎหมาย":
        return True
    # Exclude ข้อหารือ/กวจ files that reference laws
    stem = filename.lower()
    if "ข้อหารือ" in stem or "_กวจ_" in stem or "_กวพ_" in stem:
        return False
    return stem.startswith("พรบ") or stem.startswith("ระเบียบกระทรวง") or "กฎกระทรวง" in stem


def load_md_file(path: Path | str) -> list[Chunk]:
    """
    Load a single MD file with frontmatter → list of Chunks.
    Law files (พ.ร.บ./ระเบียบ) are chunked per มาตรา/ข้อ with วรรค headers.
    Other files use standard ThaiTextSplitter.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    # Normalize metadata keys to what the pipeline expects.
    base_meta = {
        "source_drive_id": meta.get("file_id", ""),
        "source_name": meta.get("source_file") or meta.get("original_filename") or path.name,
        "source_url": meta.get("file_url", ""),
        "category": meta.get("type") or meta.get("doc_type") or "ข้อหารือ กวจ.",
        "issued_by": meta.get("issued_by", ""),
        "date": str(meta.get("date", "")),
        "ref_number": meta.get("ref_number") or meta.get("doc_number") or "",
        "topic": meta.get("topic", ""),
        "subtopic": meta.get("subtopic", ""),
        "tags": meta.get("tags", []),
        "law_section": meta.get("law_section") or meta.get("laws_referenced") or [],
    }

    if _is_law_file(meta, path.name):
        chunks = _load_law_chunks(body, meta, base_meta, path)
        if chunks:
            return chunks
        # Fallback to generic chunks if law parser found no sections
        logger.warning(f"Law chunking found no sections for '{path.name}', falling back to generic chunks")

    return _section_chunks(body, base_meta)


def _load_law_chunks(body: str, meta: dict, base_meta: dict, path: Path) -> list[Chunk]:
    """Parse law body into LawDocument and chunk per section/paragraph."""
    law_name, law_short_name, law_type, law_year_be = _detect_law_meta(body, path.name)

    # Override from frontmatter if available
    law_name = meta.get("law_name") or law_name
    law_short_name = meta.get("law_short_name") or law_short_name
    law_type = meta.get("law_type") or law_type
    law_year_be = meta.get("law_year_be") or law_year_be

    # Strip [context headers] that were added by law_extractor's MD generation
    # e.g. "[พ.ร.บ.จัดซื้อจัดจ้างฯ 2560]" before each มาตรา
    clean_body = re.sub(r"^\[.*?\]\s*$", "", body, flags=re.MULTILINE)

    sections = _parse_sections(clean_body, use_gemini=False)

    doc = LawDocument(
        filename=path.name,
        file_id=base_meta.get("source_drive_id", ""),
        law_name=law_name,
        law_short_name=law_short_name,
        law_type=law_type,
        law_year_be=law_year_be,
        sections=sections,
        full_text=body,
        total_sections=len(sections),
    )

    return chunk_law_document(doc)


def load_md_directory(directory: Path | str) -> list[Chunk]:
    """Load all .md files in a directory."""
    directory = Path(directory)
    all_chunks: list[Chunk] = []
    for md_file in sorted(directory.glob("*.md")):
        chunks = load_md_file(md_file)
        all_chunks.extend(chunks)
    return all_chunks
