# Lesson: RAG Tooling Patterns

**Date**: 2026-02-13
**Source**: Thai Legal RAG session — tooling layer

---

## Pattern: Plan paths drift from reality

Plans are written from memory. Always verify paths against the filesystem before implementing. When a mismatch is found, create a bridge (wrapper/redirect) rather than moving files — moving breaks other things.

**Applied**: Plan said `pipeline/streamlit_app.py`, app lived at `app/streamlit_app.py`. Created a thin wrapper at the expected path using `exec()` for the Streamlit import case.

---

## Pattern: exec() redirect for Streamlit

When you need Streamlit to run a file at path A but the canonical app is at path B:

```python
if __name__ == "__main__":
    subprocess.run(["streamlit", "run", str(app_path)] + sys.argv[1:])
else:
    exec(app_path.read_text(encoding="utf-8"), {"__file__": str(app_path)})
```

The `__name__ != "__main__"` branch handles `streamlit run pipeline/wrapper.py` (Streamlit imports the module). The `__file__` override is critical — without it, relative path resolution inside the app breaks.

---

## Pattern: Query CLI for RAG testing

Before a UI is ready (or as a complement to it), a CLI query tool is more useful than running the full Streamlit app. Key features:
- `--no-generate` for pure retrieval testing (no LLM cost)
- `--mode global/local/hybrid/naive` for LightRAG graph modes
- `--no-expand` to test raw query vs expanded
- Show scores, sources, and Drive links

---

## Rule: Never `git add .` in lab directories

Lab directories often have credentials, tokens, and large files. Always use explicit `git add <file>` and scan `git status` first. Untracked secrets are a constant risk in working dirs that mix code + data.

---

## Pattern: clear_cache for re-OCR

OCR cache keyed by `SHA256(file_id)`. When a file is re-uploaded to Drive, the file_id changes but the old cache may still be around for the old ID. The `clear_cache(file_id)` helper is mainly useful for:
- Dev iteration (re-extract with improved prompt)
- Corrupted/incomplete cached OCR
- Force-refresh after document correction

The `--force` flag in `batch_index_law.py` bypasses the cache at extraction time, but `clear_cache()` removes it permanently.
