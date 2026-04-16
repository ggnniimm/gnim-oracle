# Verify ผลลัพธ์ก่อนรายงานว่าเสร็จ

**Date**: 2026-04-14

## กฎ

ก่อนบอก Ming ว่า "เสร็จแล้ว" หรือ "อัปเดตแล้ว" ต้อง query ผลลัพธ์จริงก่อนเสมอ

- Spreadsheet: print headers ก่อน, แล้ว SELECT sample rows หลัง update
- Database: count rows ที่ยังผิด หลัง patch
- File: อ่านไฟล์กลับมาตรวจ ไม่ assume จาก exit code

## ตัวอย่างที่ผิด

```python
# ❌ update แล้วบอกว่าเสร็จทันที
ws[row][7].value = new_id
wb.save(path)
print("Updated!")  # ← ไม่รู้ว่ามี URL column ด้วย
```

## ตัวอย่างที่ถูก

```python
# ✅ ดู schema ก่อน แล้ว update ให้ครบ
headers = [c.value for c in ws[1]]
print("Columns:", headers)  # ← รู้ก่อนว่ามีกี่ column
# จากนั้นค่อย update ทุก derived field พร้อมกัน
```

## เกิดขึ้นสองครั้งในวันเดียว (2026-04-14)

1. Patch Qdrant ด้วย xlsx (ไม่ verify ว่า xlsx ถูกต้องก่อน)
2. Update xlsx Drive ID แต่ไม่ update URL column (ไม่ดู schema ก่อน)
