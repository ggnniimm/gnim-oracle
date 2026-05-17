# Reconciliation Log — 2026-05-17

Decision log for Phase 0 ของแผน `~/.claude/plans/compiled-dazzling-marshmallow.md` (Local-first model).

**Method**: Snapshot prod `/app/` (src/, pipeline/, app/, requirements.txt) ผ่าน `ssh + docker exec + tar` ลง `prod-snapshot/` (gitignored), แล้ว diff กับ local.

**Result**: Drift ใหญ่กว่าที่คาดมาก. ทุก source-of-truth จะเป็น **local** (ตามหลัก Local-first); prod image จะถูก rebuild ใน Phase 1 จาก local code ที่ canonical แล้ว.

---

## A. Identical (no action)

ตรงกัน 100% หลัง patch md_loader 2026-05-16:
- `requirements.txt` (root)
- `src/generation/generator.py`
- `src/ingestion/md_loader.py` (เพิ่งตรงกันหลัง surgical patch 2026-05-16)

---

## B. Differs — local canonical (Phase 1 rebuild image จาก local)

| File | Local | Prod | หมายเหตุ |
|------|-------|------|---------|
| `src/config.py` | 99 | 90 | local +9 (น่าจะเรื่อง Vertex AI config) |
| `src/gemini_client.py` | 149 | 123 | local +26 (retry, fallback, Vertex routing) |
| `src/indexing/qdrant_store.py` | 227 | 201 | local +26 (Vertex embed batch fix commit 55ae882) |
| `src/ingestion/ocr.py` | 1246 | 651 | local **+595** (OCR pipeline พัฒนา local มาก, prod ใช้ของเก่า) |
| `src/retrieval/reranker.py` | 216 | 215 | local +1 (minor) |
| `pipeline/index_md_folder.py` | 177 | 171 | local +6 (inactive file handling) |
| `pipeline/batch_index.py` | 220 | 225 | prod +5 (`--no-lightrag` deprecated flag) |
| `pipeline/batch_index_law.py` | 144 | 145 | prod +1 (same flag) |

**Decision**: ใช้ local เป็น canonical ทั้งหมด. `--no-lightrag` flag ที่ prod เพิ่ม → unused (lightrag ถูกถอนแล้ว) → ปล่อยหายไป.

**Phase 1 implication**: เมื่อ rebuild image จาก local repo, prod จะได้ทุก feature ที่ local ทำมา (ที่หายไป 5+ สัปดาห์).

---

## C. Prod-only files — เพิ่มเข้า git as-is

stranded code ที่ใช้งานจริง:

| File | สาเหตุที่ commit |
|------|-----------------|
| `pipeline/run_eval.py` | runner ที่ prod ใช้รัน eval มาตลอด — Ming เลือกเก็บเข้า git ก่อน, ค่อยตัดสินใจรวมกับ `eval/run_eval.py` (414 บรรทัด, local-only ที่ใหม่กว่า) ภายหลัง |
| `pipeline/build_bm25_index.py` | build BM25 index — prod คงใช้ |
| `pipeline/rebuild_faiss_index.py` | rebuild FAISS — น่าจะ deprecated แล้ว (no FAISS) แต่เก็บไว้ก่อน |
| `pipeline/patch_metadata.py` | metadata patching utility |
| `pipeline/golden_test_cases.json.bak.2026-04-30` | backup ก่อน corpus resync — เก็บเป็น historical reference |
| `pipeline/golden_test_cases.json.bak.2026-04-30-tc044` | backup ก่อน TC-044 fix — เก็บเป็น historical reference |

**Note**: `pipeline/golden_test_cases.json` (prod) ตรงกับ `eval/golden_test_cases.json` (local) ทุกบรรทัด (1467 บรรทัดเท่ากัน, `diff` empty) → ไม่ commit duplicate. Phase 1 จะให้ prod ใช้ `eval/golden_test_cases.json` (canonical) — pipeline/run_eval.py อ้างถึง `pipeline/golden_test_cases.json` ปัจจุบัน, จะต้องแก้ path หรือ symlink ใน Phase 1.

---

## D. Prod-only files — NOT committing (dead/orphan/wrong path)

ไม่ commit เข้า git, จะหายไปเองตอน Phase 1 rebuild image:

| File | เหตุผล |
|------|-------|
| `src/generator.py` | orphan — code จริงคือ `src/generation/generator.py`, ไม่มีไฟล์ไหน import (verified via grep) |
| `src/indexing/faiss_store.py` | dead code — FAISS ถอนแล้ว, ไม่มี imports |
| `src/indexing/lightrag_store.py` | dead code — LightRAG ถอนแล้ว, ไม่มี imports |
| `app/requirements.txt` | duplicate ของ root `requirements.txt` (เนื้อหาเดียวกัน) — root canonical |
| `app/auth_config.yaml` | wrong path — memory `mwaprocure-auth-config` ยืนยัน live config คือ `data/auth_config.yaml` |
| `src/config.py.backup_2026-05-08` | backup ก่อน Vertex pivot |
| `src/config.py.bak.pre-pro-routing` | backup ก่อน hybrid Pro routing |
| `src/gemini_client.py.bak.pre-pro-experiment` | backup ก่อน Pro experiment |
| `app/streamlit_app.py.backup_2026-05-08` | backup |
| `app/streamlit_app.py.bak` | backup |
| `app/streamlit_app_single_qa.py.backup_2026-05-08` | backup |

**Decision**: ไม่ commit. Phase 1 rebuild image จะได้ image สะอาดไม่มี backups + dead code.

---

## E. Local-only files — keep as-is (ship เข้า image Phase 1)

OCR pipeline ที่ทำงาน local เท่านั้น:

| File | Purpose |
|------|---------|
| `pipeline/batch5_reocr_quality.py` | OCR re-quality batch 5 |
| `pipeline/batch_ocr.py` | bulk OCR runner |
| `pipeline/reocr_circulars_pro.py` | Gemini Pro re-OCR (recent, hybrid routing arc) |
| `pipeline/retry_failed_pages.py` | retry failed OCR pages |

**Phase 1 implication**: COPY pipeline/ เข้า image เพื่อ symmetry — prod จะมีไฟล์เหล่านี้ด้วย (ไม่ได้ใช้รัน เพราะ workflow คือ local รัน — แต่มีไว้สำหรับ debugging/recovery)

---

## F. Commit plan

Single commit:
```
reconcile: snapshot prod /app/ — bring stranded files into canonical git

Phase 0 ของ Local-first plan. Snapshot prod via docker exec tar,
diff vs local. Add prod-only useful files (pipeline/run_eval.py,
build_bm25_index.py, rebuild_faiss_index.py, patch_metadata.py,
golden_test_cases.json + 2 backups). Do not commit prod-only dead
code (src/generator.py, faiss_store.py, lightrag_store.py) or
backup files — Phase 1 rebuild image will drop them. Document all
decisions in RECONCILE_2026-05-17.md.
```

**Files to git add** (group C, ไม่รวม golden_test_cases.json เพราะตรงกับ local):
- `pipeline/run_eval.py`
- `pipeline/build_bm25_index.py`
- `pipeline/rebuild_faiss_index.py`
- `pipeline/patch_metadata.py`
- `pipeline/golden_test_cases.json.bak.2026-04-30`
- `pipeline/golden_test_cases.json.bak.2026-04-30-tc044`
- `RECONCILE_2026-05-17.md` (this doc)
- `.gitignore` (เพิ่ม prod-snapshot/)
