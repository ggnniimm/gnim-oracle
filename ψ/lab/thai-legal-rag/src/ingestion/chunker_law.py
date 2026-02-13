"""
Law-aware chunker — groups consecutive มาตรา/ข้อ within the same หมวด.

Strategy:
- One chunk = N consecutive sections within the same chapter (หมวด)
- Chunk boundary: chapter change OR exceeds MAX_CHARS
- Each chunk is prefixed with law context header for embedding quality:
    "<<law_short_name>> | <<chapter>>\n\n"

Metadata per chunk:
    doc_type, law_name, law_short_name, law_type, law_year_be,
    part, chapter, section_numbers, first_section, last_section,
    source_drive_id, source_name, source_url, chunk_index
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.ingestion.chunker import Chunk
from src.ingestion.law_extractor import LawDocument, LawSection

logger = logging.getLogger(__name__)

# Max characters per law chunk (larger than normal chunks — law text is dense)
LAW_CHUNK_MAX_CHARS = 800


def chunk_law_document(
    doc: LawDocument,
    max_chars: int = LAW_CHUNK_MAX_CHARS,
) -> list[Chunk]:
    """
    Chunk a parsed LawDocument into Chunks suitable for embedding.

    Groups consecutive sections within the same chapter until max_chars.
    Adds a context header to each chunk.
    """
    if not doc.sections:
        logger.warning(f"No sections parsed for '{doc.filename}' — skipping")
        return []

    chunks: list[Chunk] = []
    chunk_index = 0

    current_sections: list[LawSection] = []
    current_chars = 0
    current_chapter = None

    def _emit(secs: list[LawSection]) -> None:
        nonlocal chunk_index
        if not secs:
            return

        part = secs[0].part
        chapter = secs[0].chapter
        section_numbers = [s.number for s in secs]

        # Context header makes the chunk self-contained for embedding
        header_parts = [doc.law_short_name or doc.law_name]
        if part:
            header_parts.append(part)
        if chapter:
            header_parts.append(chapter)
        header = " | ".join(header_parts)

        body = "\n\n".join(s.text for s in secs)
        chunk_text = f"{header}\n\n{body}"

        meta = {
            "doc_type": "กฎหมาย",
            "law_name": doc.law_name,
            "law_short_name": doc.law_short_name,
            "law_type": doc.law_type,
            "law_year_be": doc.law_year_be,
            "part": part,
            "chapter": chapter,
            "section_numbers": section_numbers,
            "first_section": section_numbers[0] if section_numbers else "",
            "last_section": section_numbers[-1] if section_numbers else "",
            "source_drive_id": doc.file_id,
            "source_name": doc.filename,
            "source_url": f"https://drive.google.com/file/d/{doc.file_id}/view",
            "chunk_index": chunk_index,
            "category": "กฎหมาย",
        }
        chunks.append(Chunk(text=chunk_text, metadata=meta))
        chunk_index += 1

    for sec in doc.sections:
        chapter_changed = (current_chapter is not None and sec.chapter != current_chapter)
        would_exceed = (current_chars + len(sec.text) > max_chars) and current_sections

        if chapter_changed or would_exceed:
            _emit(current_sections)
            current_sections = []
            current_chars = 0

        current_sections.append(sec)
        current_chars += len(sec.text)
        current_chapter = sec.chapter

    # Emit remaining
    _emit(current_sections)

    logger.info(
        f"Chunked '{doc.filename}' → {len(chunks)} chunks "
        f"({doc.total_sections} sections, max_chars={max_chars})"
    )
    return chunks
