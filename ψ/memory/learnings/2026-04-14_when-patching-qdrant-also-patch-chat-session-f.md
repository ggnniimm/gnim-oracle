---
title: ## When Patching Qdrant, Also Patch Chat Session Files
tags: [qdrant, sessions, patch, file-url, streamlit, monkey-patch, thai-legal-rag]
created: 2026-04-14
source: 2026-04-14 learning
---

# ## When Patching Qdrant, Also Patch Chat Session Files

## When Patching Qdrant, Also Patch Chat Session Files

Qdrant payloads and chat session JSON files store `file_url` identically. Patching Qdrant doesn't retroactively update saved sessions.

**Rule**: After every Qdrant file_url patch, immediately scan all session files:

```bash
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

**Why**: Session files store a snapshot of source links at query time. If Qdrant had old URLs when the session was indexed, the session has old URLs too. Qdrant patch doesn't retroactively update sessions.

**Also**: When monkey-patching a library function, trace the full call chain in the controller first — not just the function that appears in the error. Both `validate_password` (gate) AND `diagnose_password` (error message) must be patched for streamlit_authenticator.

---
*Added via Oracle Learn*
