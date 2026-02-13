"""
Thai-aware text chunker.
Uses PyThaiNLP sentence tokenization to avoid cutting mid-sentence.
Produces chunks with metadata for downstream indexing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pythainlp.tokenize import sent_tokenize

from src.config import CHUNK_OVERLAP, CHUNK_SIZE

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    # metadata keys used downstream:
    #   source_drive_id, source_name, category, page_range, chunk_index


class ThaiTextSplitter:
    """
    Split Thai text into overlapping chunks using sentence boundaries.
    """

    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str, base_metadata: dict | None = None) -> list[Chunk]:
        """
        Split text into chunks.
        base_metadata is copied into each chunk's metadata.
        """
        if base_metadata is None:
            base_metadata = {}

        # Tokenize into sentences
        sentences = sent_tokenize(text, engine="crfcut")
        if not sentences:
            return []

        chunks: list[Chunk] = []
        current_sentences: list[str] = []
        current_len = 0
        chunk_index = 0

        for sent in sentences:
            sent_len = len(sent)

            if current_len + sent_len > self.chunk_size and current_sentences:
                # Emit current chunk
                chunk_text = "".join(current_sentences).strip()
                if chunk_text:
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            metadata={**base_metadata, "chunk_index": chunk_index},
                        )
                    )
                    chunk_index += 1

                # Keep overlap: retain last N chars worth of sentences
                overlap_sentences: list[str] = []
                overlap_len = 0
                for s in reversed(current_sentences):
                    if overlap_len + len(s) > self.overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s)

                current_sentences = overlap_sentences
                current_len = overlap_len

            current_sentences.append(sent)
            current_len += sent_len

        # Emit final chunk
        if current_sentences:
            chunk_text = "".join(current_sentences).strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        metadata={**base_metadata, "chunk_index": chunk_index},
                    )
                )

        logger.debug(f"Chunked into {len(chunks)} chunks (size={self.chunk_size}, overlap={self.overlap})")
        return chunks


def chunk_document(
    text: str,
    source_drive_id: str,
    source_name: str,
    category: str,
) -> list[Chunk]:
    """Convenience wrapper: chunk a full document with standard metadata."""
    splitter = ThaiTextSplitter()
    base_meta = {
        "source_drive_id": source_drive_id,
        "source_name": source_name,
        "category": category,
    }
    return splitter.split(text, base_metadata=base_meta)
