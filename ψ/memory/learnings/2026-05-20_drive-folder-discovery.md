---
name: drive-folder-discovery
description: list_drive_files.py hardcode folder list — ต้อง scan root folders ด้วยเพื่อ detect folders ใหม่ที่ Ming สร้างบน Drive
metadata:
  type: project
---

`list_drive_files.py` hardcode เฉพาะ known folders (CGD, CGD_W, CGD3, CGD_OLD, OAG, AC, LAW, ETC) — ถ้า Ming สร้าง folder ใหม่บน Drive จะไม่ถูก scan

**Why:** วันนี้พบ CGD_PRICE folder ใหม่ที่ไม่เคยอยู่ใน list — รู้จาก Ming บอกตรงๆ ถ้าไม่บอกก็จะ miss ไปตลอด Drive structure ไม่ static ต้อง discover ด้วย

**How to apply:** ก่อน scan หา new files ทุกครั้ง ให้ list all root folders ด้วย:
```python
service.files().list(q="mimeType='application/vnd.google-apps.folder' and trashed=false").execute()
```
เปรียบเทียบกับ KNOWN_FOLDERS — folder ใหม่จะ surface ขึ้นมาเอง ให้ถาม user ว่าจะ add เข้า scan list ไหม
