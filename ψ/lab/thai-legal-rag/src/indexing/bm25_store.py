"""BM25 lexical search store — complements FAISS semantic search."""
import pickle
import logging
from pathlib import Path
from pythainlp.tokenize import word_tokenize
from rank_bm25 import BM25Okapi
from src.config import BM25_DIR, BM25_TOP_K

logger = logging.getLogger(__name__)
_INDEX_FILE = BM25_DIR / "bm25.pkl"


def _tokenize(text: str) -> list[str]:
    return word_tokenize(text, engine="newmm", keep_whitespace=False)


class BM25Store:
    def __init__(self):
        self._corpus: list[list[str]] = []
        self._metadata: list[dict] = []
        self._bm25: BM25Okapi | None = None
        self._dirty = False
        self._load()

    def _load(self):
        if _INDEX_FILE.exists():
            with open(_INDEX_FILE, "rb") as f:
                data = pickle.load(f)
            self._corpus = data["corpus"]
            self._metadata = data["metadata"]
            if self._corpus:
                self._bm25 = BM25Okapi(self._corpus)
            logger.info(f"Loaded BM25 index: {len(self._corpus)} docs")
        else:
            logger.info("Created new BM25 index")

    def _rebuild(self):
        if self._corpus:
            self._bm25 = BM25Okapi(self._corpus)
        self._dirty = False

    def add_batch(self, texts: list[str], metadatas: list[dict]) -> None:
        for text, meta in zip(texts, metadatas):
            self._corpus.append(_tokenize(text))
            self._metadata.append({"text": text, **meta})
        self._dirty = True

    def search(self, query: str, k: int = BM25_TOP_K) -> list[dict]:
        if not self._corpus:
            return []
        if self._dirty:
            self._rebuild()
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                break
            item = dict(self._metadata[idx])
            item["score"] = float(scores[idx])
            item["source"] = "bm25"
            results.append(item)
        return results

    def save(self):
        BM25_DIR.mkdir(parents=True, exist_ok=True)
        with open(_INDEX_FILE, "wb") as f:
            pickle.dump({"corpus": self._corpus, "metadata": self._metadata}, f)
        logger.info(f"Saved BM25 index: {len(self._corpus)} docs")

    @property
    def count(self) -> int:
        return len(self._corpus)
