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

import re
from pathlib import Path

import yaml

from src.ingestion.chunker import ThaiTextSplitter, Chunk, CHUNK_SIZE, CHUNK_OVERLAP


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (meta, body)."""
    m = _FRONTMATTER_RE.match(text)
    if m:
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        body = text[m.end():]
    else:
        meta = {}
        body = text
    return meta, body


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


def load_md_file(path: Path | str) -> list[Chunk]:
    """
    Load a single MD file with frontmatter → list of Chunks.
    Metadata from frontmatter is attached to every chunk.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    # Normalize metadata keys to what the pipeline expects
    base_meta = {
        "source_drive_id": meta.get("file_id", ""),
        "source_name": meta.get("source_file", path.name),
        "source_url": meta.get("file_url", ""),
        "category": meta.get("type", "ข้อหารือ กวจ."),
        "date": str(meta.get("date", "")),
        "ref_number": meta.get("ref_number", ""),
        "topic": meta.get("topic", ""),
        "tags": meta.get("tags", []),
        "law_section": meta.get("law_section", []),
    }

    return _section_chunks(body, base_meta)


def load_md_directory(directory: Path | str) -> list[Chunk]:
    """Load all .md files in a directory."""
    directory = Path(directory)
    all_chunks: list[Chunk] = []
    for md_file in sorted(directory.glob("*.md")):
        chunks = load_md_file(md_file)
        all_chunks.extend(chunks)
    return all_chunks
