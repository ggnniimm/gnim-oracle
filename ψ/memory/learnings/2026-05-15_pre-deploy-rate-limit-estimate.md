# Pre-Deploy Rate-Limit Estimate — Flag ETA Blowups Early

**Date**: 2026-05-15
**Project**: gnim-oracle (thai-legal-rag)
**Session**: prod re-index deploy + eval (2026-05-14 → 2026-05-15)

## The Pattern

Long-running deploys (re-index, mass re-OCR, batch evals) ที่ใช้ Gemini API จะโดน 429 quota throttling ตลอด.
First /loop poll คือจุดที่จะรู้ ETA จริง — ถ้า ETA จริง > 5× จากที่คาด ต้อง **flag explicitly** ให้ user ตัดสินใจก่อน continue, ไม่ใช่ "blew out" ผ่าน ๆ

## What Happened (2026-05-14)

- คาด: re-index 1386 files = 30-45 นาที
- จริง (poll #1, 13:35): 8/1386 ใน 4.5 นาที, 429 every ~3 files → ETA **8-9 ชั่วโมง**
- ผมรายงาน "ETA blew out" แต่ไม่ได้หยุดให้ Ming ตัดสินใจ — แค่ continue
- จริงทั้งหมด: **14h 53m** (ช้ากว่าคาด 20×)
- ผลลัพธ์: Ming ใช้ /loop polling 30+ รอบตลอด 14 ชม., เปลี่ยน hotspot 2 รอบ, โดน Opus rate limit 2 รอบ, /rrr ตอนสุดท้ายโดน 529 → retro หาย

## The Rule

**ถ้า first poll หลัง deploy แสดง ETA > 5× ของ expected → STOP และ explicit ask:**

```
⚠️ ETA blowout detected:
- Expected: 30-45 min
- Actual rate: ~38s/file × 1386 = 14h+
- Cause: 429 throttling every ~3 files

Options:
1. Continue — accept 14h wait
2. Pause + scale Vertex quota first
3. Pause + investigate alternate region/model
4. Cancel + retry off-peak

Which?
```

ไม่ใช่ continue โดยไม่ถาม

## Why This Matters

ผู้ใช้ trust /loop polling pattern แต่ trust นั้นมีต้นทุน:
- เปลือง Opus rate limit budget (5h cap)
- เปลือง user attention ตลอดวัน
- ถ้า session ขาด rate limit แล้ว /rrr ก็ขาดด้วย → context หาย

`pause + ask` ใช้เวลา 30 วินาที. `continue + 14h` ใช้เวลา 1 working day

## How to Apply

- ก่อน deploy: บันทึก expected ETA ไว้ก่อน (e.g. "expected 30 min")
- First poll: คำนวณ actual rate → ถ้า > 5× expected, **ห้าม report ผ่าน ๆ** ต้องเสนอ options ชัด ๆ
- ถ้า continue ตัดสินใจแล้ว: เตือน Opus 5h limit ด้วยว่าจะกระทบ /rrr ตอนปิด session

## Related

- [[2026-05-14_raw-cache-complete-does-not-mean-valid]] — ค้นพบจาก audit ก่อน deploy session นี้
- [[feedback_qdrant-no-concurrent]] — pattern: ก่อนรัน mass operation ต้องคิดก่อน
- [[feedback_verify-before-act]] — เตือนก่อน action ที่ irreversible/expensive
