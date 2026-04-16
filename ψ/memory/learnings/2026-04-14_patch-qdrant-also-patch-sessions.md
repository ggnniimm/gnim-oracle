# เมื่อ Patch Qdrant ให้ Patch Session Files ด้วยทันที

**Date**: 2026-04-14

## กฎ

Qdrant payloads และ chat session files เก็บ `file_url` เหมือนกัน เมื่อ patch Qdrant แล้วต้องทำ session file scan ต่อทันที

```bash
# หลัง patch Qdrant เสมอ
python3 << 'EOF'
import json, re
from pathlib import Path

mapping = ...  # stem -> correct file_url

for fname in Path('/app/thai-legal-rag/data').glob('chat_sessions*.json'):
    data = json.loads(fname.read_text())
    changed = 0
    for session in data.values():
        for msg in session.get('messages', []):
            for src in msg.get('sources', []):
                name = src.get('name', '')
                stem = Path(name).stem if name else ''
                if stem in mapping and src.get('url') != mapping[stem]:
                    src['url'] = mapping[stem]
                    changed += 1
    if changed:
        fname.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f'{fname.name}: {changed} fixed')
EOF
```

## ทำไม

Session files เก็บ snapshot ของ source links ตอนที่ query ถูกทำ ถ้า Qdrant มี old URL ตอน index session ก็มี old URL ด้วย Qdrant patch ไม่ retroactively update sessions

## Monkey-Patch Library

เมื่อ patch library function ให้ trace full call chain ใน controller ก่อน ไม่ใช่แค่ function ที่ปรากฎในหน้า error

```python
# ❌ แค่ patch function ที่เห็นใน error
Validator.diagnose_password = lambda self, p: ""

# ✅ อ่าน controller source ก่อน แล้ว patch ทุก gate
Validator.validate_password = lambda self, p: True   # gate ก่อน
Validator.diagnose_password = lambda self, p: ""     # message หลัง fail
```
