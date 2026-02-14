"""
Law-aware chunker — section-first, paragraph-split for long sections.

Strategy:
- Short section (≤ SECTION_SPLIT_CHARS): group consecutive sections in same chapter
- Long section (> SECTION_SPLIT_CHARS) with multiple วรรค: 1 chunk per วรรค
- Long section with single วรรค: 1 chunk = 1 section

Metadata per chunk:
    doc_type, law_name, law_short_name, law_type, law_year_be,
    part, chapter, section, paragraph, total_paragraphs,
    section_numbers (for grouped chunks),
    source_drive_id, source_name, source_url, chunk_index
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.ingestion.chunker import Chunk
from src.ingestion.law_extractor import LawDocument, LawSection

logger = logging.getLogger(__name__)

# Section longer than this threshold will be split at paragraph level
SECTION_SPLIT_CHARS = 400

# Max chars for grouped (short) chunks
LAW_CHUNK_MAX_CHARS = 800


def _base_meta(doc: LawDocument, sec: LawSection, chunk_index: int) -> dict:
    """Base metadata shared by all chunk types."""
    return {
        "doc_type": "กฎหมาย",
        "law_name": doc.law_name,
        "law_short_name": doc.law_short_name,
        "law_type": doc.law_type,
        "law_year_be": doc.law_year_be,
        "part": sec.part,
        "chapter": sec.chapter,
        "source_drive_id": doc.file_id,
        "source_name": doc.filename,
        "source_url": f"https://drive.google.com/file/d/{doc.file_id}/view",
        "file_url": f"https://drive.google.com/file/d/{doc.file_id}/view",
        "chunk_index": chunk_index,
        "category": "กฎหมาย",
    }


def _context_header(doc: LawDocument, sec: LawSection, paragraph: int | None = None) -> str:
    """Build context header: [กฎหมาย | ภาค | หมวด | มาตรา X | วรรค Y]"""
    parts = [doc.law_short_name or doc.law_name]
    if sec.part:
        parts.append(sec.part)
    if sec.chapter:
        parts.append(sec.chapter)
    parts.append(f"มาตรา {sec.number}" if doc.law_type == "พระราชบัญญัติ" else f"ข้อ {sec.number}")
    if paragraph is not None:
        parts.append(f"วรรค {paragraph}")
    return "[" + " | ".join(parts) + "]"


def _emit_paragraph_chunks(
    doc: LawDocument,
    sec: LawSection,
    chunks: list[Chunk],
    chunk_index: int,
) -> int:
    """Emit one chunk per วรรค for a long section."""
    paras = sec.paragraphs
    total = len(paras)
    for i, para_text in enumerate(paras, start=1):
        header = _context_header(doc, sec, paragraph=i)
        chunk_text = f"{header}\n\n{sec.label}\n{para_text}"
        meta = _base_meta(doc, sec, chunk_index)
        meta.update({
            "section": sec.number,
            "paragraph": i,
            "total_paragraphs": total,
            "section_numbers": [sec.number],
            "first_section": sec.number,
            "last_section": sec.number,
        })
        chunks.append(Chunk(text=chunk_text, metadata=meta))
        chunk_index += 1
    return chunk_index


def _emit_grouped_chunks(
    doc: LawDocument,
    secs: list[LawSection],
    chunks: list[Chunk],
    chunk_index: int,
) -> int:
    """Emit one chunk for a group of short sections."""
    if not secs:
        return chunk_index

    sec0 = secs[0]
    section_numbers = [s.number for s in secs]
    header = _context_header(doc, sec0)  # header uses first section's chapter

    body = "\n\n".join(s.text for s in secs)
    chunk_text = f"{header}\n\n{body}"

    meta = _base_meta(doc, sec0, chunk_index)
    meta.update({
        "section": section_numbers[0] if len(section_numbers) == 1 else None,
        "paragraph": None,
        "total_paragraphs": None,
        "section_numbers": section_numbers,
        "first_section": section_numbers[0],
        "last_section": section_numbers[-1],
    })
    chunks.append(Chunk(text=chunk_text, metadata=meta))
    return chunk_index + 1


def chunk_law_document(
    doc: LawDocument,
    max_chars: int = LAW_CHUNK_MAX_CHARS,
    split_chars: int = SECTION_SPLIT_CHARS,
) -> list[Chunk]:
    """
    Chunk a parsed LawDocument into Chunks suitable for embedding.

    Short sections (≤ split_chars): grouped within same chapter.
    Long sections (> split_chars): split at วรรค boundaries.
    """
    if not doc.sections:
        logger.warning(f"No sections parsed for '{doc.filename}' — skipping")
        return []

    chunks: list[Chunk] = []
    chunk_index = 0

    pending: list[LawSection] = []
    pending_chars = 0
    pending_chapter = None

    def flush_pending() -> None:
        nonlocal chunk_index, pending, pending_chars, pending_chapter
        if pending:
            chunk_index = _emit_grouped_chunks(doc, pending, chunks, chunk_index)
        pending = []
        pending_chars = 0
        pending_chapter = None

    for sec in doc.sections:
        sec_len = len(sec.text)
        is_long = sec_len > split_chars and len(sec.paragraphs) > 1

        if is_long:
            # Flush any pending short sections first
            flush_pending()
            # Emit one chunk per วรรค
            chunk_index = _emit_paragraph_chunks(doc, sec, chunks, chunk_index)

        else:
            # Group with pending if same chapter and won't exceed max
            chapter_changed = (pending_chapter is not None and sec.chapter != pending_chapter)
            would_exceed = (pending_chars + sec_len > max_chars) and pending

            if chapter_changed or would_exceed:
                flush_pending()

            pending.append(sec)
            pending_chars += sec_len
            pending_chapter = sec.chapter

    flush_pending()

    logger.info(
        f"Chunked '{doc.filename}' → {len(chunks)} chunks "
        f"({doc.total_sections} sections, split_chars={split_chars})"
    )
    return chunks
