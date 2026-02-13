"""
Tests for Thai-aware chunker.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.chunker import ThaiTextSplitter, chunk_document


SAMPLE_THAI_TEXT = """
ระเบียบกระทรวงการคลัง ว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560
กำหนดให้หน่วยงานของรัฐต้องดำเนินการจัดซื้อจัดจ้างตามหลักเกณฑ์ที่กำหนด
ผู้มีอำนาจอนุมัติต้องพิจารณาอย่างรอบคอบ โดยคำนึงถึงประโยชน์สูงสุดของทางราชการ

มาตรา 10 กำหนดให้คณะกรรมการจัดซื้อจัดจ้างมีหน้าที่จัดทำแผนการจัดซื้อจัดจ้าง
และประกาศให้สาธารณชนทราบทางระบบเครือข่ายสารสนเทศของกรมบัญชีกลาง

ค่าปรับในกรณีผิดสัญญาให้คิดตามอัตราที่กำหนดในสัญญา
โดยทั่วไปอัตราค่าปรับอยู่ที่ร้อยละ 0.01 ถึงร้อยละ 0.1 ของมูลค่าสัญญาต่อวัน
ขึ้นอยู่กับประเภทของสัญญาและระยะเวลาที่ผิดนัด
""".strip()


def test_chunker_basic():
    """Should produce at least one chunk from Thai text."""
    splitter = ThaiTextSplitter(chunk_size=200, overlap=50)
    chunks = splitter.split(SAMPLE_THAI_TEXT)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.text.strip()


def test_chunker_respects_size():
    """Chunks should not be massively over chunk_size."""
    splitter = ThaiTextSplitter(chunk_size=100, overlap=20)
    chunks = splitter.split(SAMPLE_THAI_TEXT)
    for chunk in chunks:
        # Allow some overflow due to sentence boundary respect
        assert len(chunk.text) <= 100 * 3, f"Chunk too large: {len(chunk.text)}"


def test_chunker_metadata():
    """chunk_document should attach metadata to each chunk."""
    chunks = chunk_document(
        SAMPLE_THAI_TEXT,
        source_drive_id="drive123",
        source_name="test_doc.pdf",
        category="กรมบัญชีกลาง",
    )
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.metadata["source_drive_id"] == "drive123"
        assert chunk.metadata["source_name"] == "test_doc.pdf"
        assert chunk.metadata["category"] == "กรมบัญชีกลาง"
        assert "chunk_index" in chunk.metadata


def test_chunker_empty_input():
    """Empty text should return empty list."""
    splitter = ThaiTextSplitter()
    assert splitter.split("") == []
    assert splitter.split("   ") == []


def test_chunk_index_sequential():
    """chunk_index should be 0, 1, 2, ..."""
    splitter = ThaiTextSplitter(chunk_size=50, overlap=10)
    chunks = splitter.split(SAMPLE_THAI_TEXT)
    for i, chunk in enumerate(chunks):
        assert chunk.metadata["chunk_index"] == i
