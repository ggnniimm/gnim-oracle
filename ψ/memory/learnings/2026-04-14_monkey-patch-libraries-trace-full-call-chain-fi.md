---
title: # Monkey-Patch Libraries: Trace Full Call Chain First
tags: [monkey-patch, call-chain, session-files, qdrant, comprehensive-fix]
created: 2026-04-14
source: Oracle Learn
---

# # Monkey-Patch Libraries: Trace Full Call Chain First

# Monkey-Patch Libraries: Trace Full Call Chain First

## Rule
When monkey-patching a library to bypass validation, read the controller source code first.
Patch EVERY gate in the call chain — not just the function that appears in the error message.

```python
# ❌ Only patched what the error showed
_stauth_validator.Validator.diagnose_password = lambda self, p: ""

# ✅ Traced controller → found validate_password is called BEFORE diagnose_password
_stauth_validator.Validator.validate_password = lambda self, p: True   # gate
_stauth_validator.Validator.diagnose_password = lambda self, p: ""     # message
```

## After Patching Qdrant: Always Scan Session Files
Qdrant payloads and chat session JSON files store `file_url` independently.
When Qdrant is patched, session files are NOT updated retroactively.

After any Qdrant URL patch, immediately run:
```python
for fname in Path('/app/thai-legal-rag/data').glob('chat_sessions*.json'):
    data = json.loads(fname.read_text())
    changed = 0
    for session in data.values():
        for msg in session.get('messages', []):
            for src in msg.get('sources', []):
                stem = Path(src.get('name', '')).stem
                if stem in mapping and src.get('url') != mapping[stem]:
                    src['url'] = mapping[stem]
                    changed += 1
    if changed:
        fname.write_text(json.dumps(data, ensure_ascii=False, indent=2))
```

## Do Full Scan in One Pass
Use glob pattern `chat_sessions*.json` to catch ALL session files in one script run.
Do NOT patch file by file — you'll always miss one and need a second pass.

## Lesson: Fix Related State Together
Ask: "What other storage also holds this data?"
- Qdrant payloads → session JSON files both store source URLs
- xlsx Drive ID → URL column both derived from same source

From: `ψ/memory/retrospectives/2026-04/14/20.45_web-app-fixes.md`

---
*Added via Oracle Learn*
