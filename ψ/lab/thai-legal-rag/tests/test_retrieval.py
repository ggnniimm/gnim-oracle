"""
Smoke tests for retrieval pipeline.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_reranker_merge():
    """Reranker should merge and deduplicate results from both sources."""
    from src.retrieval.reranker import rerank

    results = {
        "vector": [
            {"text": "ระเบียบค่าปรับผิดสัญญา", "score": 0.9, "source": "vector", "source_name": "doc1.pdf"},
            {"text": "มาตรา 10 กำหนดหน้าที่คณะกรรมการ", "score": 0.7, "source": "vector", "source_name": "doc2.pdf"},
        ],
        "bm25": [
            {"text": "ระเบียบค่าปรับผิดสัญญา", "score": 0.85, "source": "bm25", "source_name": "doc1.pdf"},
            {"text": "การบริหารพัสดุภาครัฐ พ.ศ. 2560", "score": 0.6, "source": "bm25", "source_name": "doc3.pdf"},
        ],
    }

    ranked = rerank(results, top_k=5)

    assert len(ranked) >= 1
    assert len(ranked) <= 5
    # All items should have weighted_score
    for item in ranked:
        assert "weighted_score" in item

    # Top item should have highest weighted_score
    scores = [item["weighted_score"] for item in ranked]
    assert scores == sorted(scores, reverse=True)


def test_reranker_dedup():
    """Identical texts from different sources should be deduplicated."""
    from src.retrieval.reranker import rerank

    duplicate_text = "ค่าปรับกรณีผิดสัญญา" * 10

    results = {
        "vector": [{"text": duplicate_text, "score": 0.9, "source": "vector"}],
        "bm25": [{"text": duplicate_text, "score": 0.8, "source": "bm25"}],
    }

    ranked = rerank(results, top_k=5)
    # Should only have 1 result after dedup
    assert len(ranked) == 1


def test_reranker_empty():
    """Empty results should return empty list."""
    from src.retrieval.reranker import rerank

    assert rerank({}, top_k=5) == []
    assert rerank({"vector": [], "bm25": []}, top_k=5) == []


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEYS") and not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEYS not set",
)
def test_query_expand_returns_list():
    """Query expansion should return a list with the original query."""
    from src.retrieval.query_expand import expand_query

    result = expand_query("ค่าปรับผิดสัญญามีขั้นตอนยังไง")

    assert isinstance(result, list)
    assert len(result) >= 1
    # Original query should be first
    assert result[0] == "ค่าปรับผิดสัญญามีขั้นตอนยังไง"
