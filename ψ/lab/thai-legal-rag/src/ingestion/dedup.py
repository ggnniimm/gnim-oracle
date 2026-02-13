"""
Content-hash deduplication using SQLite.
SHA256(text) → check if already indexed → skip if yes → record after indexing.
Prevents re-indexing on repeated runs.
"""
import hashlib
import sqlite3
from pathlib import Path

from src.config import DEDUP_DB


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DEDUP_DB)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS indexed_chunks (
            hash      TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            added_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    con.commit()
    return con


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_indexed(text: str) -> bool:
    h = content_hash(text)
    con = _conn()
    row = con.execute("SELECT 1 FROM indexed_chunks WHERE hash = ?", (h,)).fetchone()
    con.close()
    return row is not None


def mark_indexed(text: str, source_id: str) -> None:
    h = content_hash(text)
    con = _conn()
    con.execute(
        "INSERT OR IGNORE INTO indexed_chunks (hash, source_id) VALUES (?, ?)",
        (h, source_id),
    )
    con.commit()
    con.close()


def stats() -> dict:
    con = _conn()
    total = con.execute("SELECT COUNT(*) FROM indexed_chunks").fetchone()[0]
    con.close()
    return {"total_indexed_chunks": total}
