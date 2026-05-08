---
name: คำวินิจฉัยอนุมัติยกเว้นไทยใช้ได้เฉพาะเคส (non-transferable)
description: Thai legal rulings that grant exemption from regulations apply only to the requesting agency — even identical facts at another agency require fresh case-by-case approval
type: learning
concepts: ["thai-legal", "procurement-law", "exemption-rulings", "non-transferable", "legal-precedent"]
source: "rrr: gnim-oracle (2026-05-07 session — Ming corrected my overgeneralization from กวจ 30307)"
date: 2026-05-07
---

# คำวินิจฉัยอนุมัติยกเว้นไทย (Thai Exemption Rulings) — Non-Transferable

## หลักการ

ในกฎหมายไทย คำวินิจฉัยจาก **คณะกรรมการวินิจฉัยปัญหาการจัดซื้อจัดจ้างฯ** (กวจ.) หรือหน่วยงานทำนองนั้นที่ "**อนุมัติให้ยกเว้นการปฏิบัติตามระเบียบ**" หรือ "ใช้ดุลพินิจตาม ม.97" เป็น **case-specific precedent**:

- ผูกพันเฉพาะ**หน่วยงานที่ขอ**ในเคสนั้น ๆ
- หน่วยงานอื่นแม้**ข้อเท็จจริงจะเหมือนกันทุกประการ** ก็ใช้ไม่ได้
- ต้อง**ยื่นคำขอเป็นเคส ๆ ไป** เพื่อขออนุมัติยกเว้นของตัวเอง

## ทำไม

แตกต่างจาก common law jurisdictions (US/UK) ที่คำพิพากษามี binding precedent (stare decisis) — กฎหมายไทยใช้ระบบ civil law ที่:

- **ระเบียบ/กฎหมายเป็น primary source** — ไม่ใช่คำวินิจฉัย
- **คำวินิจฉัยเป็นเพียง interpretation** ของหน่วยงานที่มีอำนาจในเคสนั้น
- **การ "ยกเว้นระเบียบ"** เป็นการใช้ดุลพินิจของผู้มีอำนาจ ไม่ใช่กฎใหม่

## ตัวอย่าง — กวจ 30307 (2021-07-08)

- กรมหนึ่งขอ "ไม่รับเงินค่าจ้างล่วงหน้า" ทั้งที่สัญญากำหนดไว้
- กวจ. อนุมัติให้แก้ไขเอกสารประกวดราคาก่อนลงนามได้ (ตามข้อยกเว้น ม.97)
- **ใช้ได้เฉพาะกรมนั้น เคสนั้น** — กรมอื่นข้อเท็จจริงเดียวกัน ก็ต้องขอเอง

## ที่ผมพลาด (2026-05-06)

Learning เมื่อวาน `2026-05-06_thai-procurement-temporal-split.md` พยายามสร้าง rule:

> **BEFORE Signing**: ✅ Flexible — เปลี่ยนเอกสารประกวดราคาได้  
> **AFTER Signing**: ❌ Locked — ต้อง ม.97 exception

**ผิดตรงไหน:** กวจ 30307 ที่ผมยกเป็นตัวอย่าง "before signing = ง่าย" จริง ๆ เป็น **exemption case** ที่ต้องขออนุมัติเฉพาะเคส **ไม่ใช่ทางลัดทั่วไป** ที่หน่วยงานอื่น copy ได้

**Pattern ที่ถูกกว่า:**
- หลัก: คู่สัญญาผูกพันตามสัญญา (มาตรา 97 วรรค 1)
- ข้อยกเว้น 4 ประการ ตาม ม.97 — แต่ละครั้งต้องใช้ "ดุลพินิจของผู้มีอำนาจ" → case-by-case
- กวจ 2610 (ที่เพิ่มเข้า RAG วันนี้) ระบุชัด: "**อาจ**ใช้ดุลพินิจ" (not "ต้อง")

## How to Apply

เมื่อตอบคำถามกฎหมายไทยที่อ้าง precedent:

1. **อย่าสร้าง general rule** จากคำวินิจฉัยเดียว — โดยเฉพาะคำที่ "อนุมัติยกเว้น"
2. **ระบุ scope ของคำวินิจฉัย** — เป็นการ interpret ระเบียบ หรือเป็น exemption case
3. **ถ้าเป็น exemption** → บอกว่าใช้ได้เฉพาะเคสที่อ้างเท่านั้น แม้ข้อเท็จจริงเหมือนก็ต้องขอเอง
4. **คำตอบควรชี้กลับไปที่ primary source** (มาตรา/ข้อในระเบียบ) ไม่ใช่ "ดูตามที่ กวจ. เคยตอบ"

## Related

- กวจ 30307 (exemption case — กรมเรือนจำ ขอไม่รับเงินล่วงหน้า)
- กวจ 2610 (general guidance — ระบุ "อาจใช้ดุลพินิจ" ตาม ม.97)
- กวจ 3061 (post-signing amendment — discretion ของผู้มีอำนาจ)
- พ.ร.บ.จัดซื้อจัดจ้างฯ พ.ศ. 2560 มาตรา 97 (primary source)

## Tags

`#thai-legal` `#exemption-rulings` `#non-transferable` `#procurement-law` `#ม.97` `#civil-law` `#feedback-from-ming`
