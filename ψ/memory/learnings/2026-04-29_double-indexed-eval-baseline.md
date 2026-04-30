# 2026-04-29 — Eval baseline ที่เคยเชื่อ อาจหลอก: local Qdrant ถูก double-indexed

ผลที่นึกว่าเป็น regression อาจเป็น discovery ว่า baseline เก่าหลอก. ก่อน trust eval pass rate ให้ตรวจ index integrity ก่อน — โดยเฉพาะถ้า index นั้นสะสมหลาย pipeline runs.

## สิ่งที่เกิด

วันนี้ deploy Drive ID remap → wipe + reindex prod Qdrant ใหม่. ผลลัพธ์: chunks ลดจาก 56,902 → 27,713 (~½). Eval บน prod ใหม่: 65/80 (was 77/78). ดูเหมือนเป็น regression 17%.

ก่อนจะ rollback, เช็คตัวเลขให้ละเอียด:
- Sample 1 file (`กวจ_ว196`):
  - Local Qdrant: 792 chunks, 396 unique chunk_index, distribution `Counter({2: 396})` → **ทุก chunk มี 2 copies**
  - Prod Qdrant: 396 chunks, 396 unique chunk_index, distribution `Counter({1: 396})` → สะอาด

Local ถูก double-indexed. ทุก chunk มี clone อยู่ใน collection. dedup.db ไม่ catch (อาจเพราะ chunk hash schema เปลี่ยนระหว่าง pipeline versions, runs ใหม่ index ซ้ำกับของเก่า).

## ผลกระทบต่อ eval

Retrieval = top-K nearest neighbors via cosine sim. ถ้าทุก chunk มี clone, **top-K ดึงเอาทั้ง original + clone ของ chunks เดียวกัน** → effective surface area ของแต่ละ doc เพิ่มเป็น 2x → ranker มีโอกาส boost canonical sources ขึ้น top → answers ถูกต้องบ่อยขึ้น.

ดังนั้น eval pass rate `77/78` บน local **ไม่ใช่ทักษะของ pipeline** แต่เป็น **side-effect ของ Qdrant ที่มี dupes**. Pure noise ที่ดันคะแนนขึ้นโดยบังเอิญ.

Prod 65/80 = **baseline จริง** ของ pipeline ปัจจุบันบน clean index.

## วิธีตรวจ double-indexing

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from collections import Counter

c = QdrantClient(url="http://localhost:6333")
flt = Filter(must=[FieldCondition(key="source_name",
    match=MatchValue(value="<some_doc.pdf>"))])
res, _ = c.scroll("thai_legal_rag", scroll_filter=flt,
    limit=1000, with_payload=["chunk_index"], with_vectors=False)
ci = [p.payload.get("chunk_index", -1) for p in res]
dist = Counter(Counter(ci).values())
print(dist)  # {1: N} = clean. {2: N} = double. {3+: N} = triple-indexed.
```

## How to apply

- ก่อน trust eval pass rate ที่สูงผิดปกติ ให้ตรวจ index integrity ก่อน (chunk_index distribution per source_name)
- ถ้า refactor pipeline แล้ว reindex บน collection เดิม โดยไม่ wipe → มีความเสี่ยงสะสม dupes (dedup จับเฉพาะถ้า chunk hash function ไม่เปลี่ยน)
- "Apparent regression" หลัง wipe + clean reindex อาจเป็น "normalization to true baseline" — separate test ก่อน rollback
- Production deploys ที่ wipe + reindex = chance ที่ดีจะรู้ว่า dev baseline หลอกแค่ไหน

## Related

- `project_drive_id_remapping.md` — full deploy notes
- `feedback_qdrant-no-concurrent` — no concurrent rebuilds (related concern about dedup integrity)
- 2026-04-29 retrospective — full session timeline
