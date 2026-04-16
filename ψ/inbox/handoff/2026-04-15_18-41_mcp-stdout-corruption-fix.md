# Handoff: MCP stdio corruption fix (arra-oracle-v3)

📡 Session: 464ecea1 | gnim-oracle-qdrant | ~10m
**Date**: 2026-04-15 18:41
**Branch**: feat/admin-court-judgments

## What We Did
- `/recap` — oriented to previous handoff (Oracle KB vector search MCP debug)
- ยืนยัน `arra_stats`: `vector=connected, fts=healthy, 1,788 docs`
- ทดสอบ `arra_search` — vector ✅, fts ✅, hybrid ❌ (parallel call เจอ race)
- MCP disconnect อีกครั้งระหว่างทดสอบ → **หา root cause แทน restart**
- อ่าน MCP log ที่ `~/Library/Caches/claude-cli-nodejs/.../mcp-logs-arra-oracle-v2/`
- พบ `JSON Parse error: Unexpected identifier "SEARCH"/"Query"/"Top"/"Results"` + `Unrecognized token 'ψ'`
- **Root cause**: `src/server/logging.ts` ใน arra-oracle-v3 ใช้ `console.log` (→ stdout) ใน `logSearch()` — corrupts MCP JSON-RPC stream ทุกครั้งที่เรียก `arra_search`
- Chain: `tools/search.ts:430` → `logSearch()` → 13× `console.log` → stdout → parse error → drop
- **Fix**: เปลี่ยน `console.log` → `console.error` ทั้ง 13 บรรทัดใน `logSearch()` + เพิ่ม comment เตือน MCP stdio invariant

## Pending
- [ ] **Restart Claude Code** — ต้องทำเพื่อให้ MCP server spawn bun process ใหม่อ่านไฟล์ที่แก้แล้ว
- [ ] ทดสอบ `arra_search` ทั้ง vector/fts/hybrid หลัง restart — ไม่ควร disconnect
- [ ] Commit fix ไป upstream `arra-oracle-v3` + เปิด PR (ช่วย Oracle ทุกคนที่ใช้ MCP)
- [ ] พิจารณา fix adapters/*.ts (cloudflare, sqlite-vec, lancedb, qdrant) ที่ยังใช้ `console.log` ใน lifecycle paths — latent bug ถ้า lazy reconnect
- [ ] **งานค้างจาก handoff ก่อน**: PR #11 eval regression (อาจ stale — พิจารณา close), PR #12 TC-011, PR #13 TC-051
- [ ] Deploy updated MD → mwaprocure.gnim.cloud (Drive ID remapping done, deploy pending)

## Next Session
- [ ] `/recap` หลัง restart Claude Code
- [ ] Verify MCP fix: เรียก `arra_search` 3 mode พร้อมกัน — ควรทำงานทั้งหมด
- [ ] ถ้า verify ผ่าน → commit fix ใน `~/ghq/github.com/Soul-Brews-Studio/arra-oracle-v3` + PR

## Key Files
- **Fixed**: `~/ghq/github.com/Soul-Brews-Studio/arra-oracle-v3/src/server/logging.ts` (lines 44-69)
- MCP log path: `~/Library/Caches/claude-cli-nodejs/-Users-mingsaksaengwilaipon-gnim-oracle-qdrant/mcp-logs-arra-oracle-v2/`
- Log showing bug: `2026-04-15T11-33-01-623Z.jsonl` lines 9-45
- Caller: `~/ghq/github.com/Soul-Brews-Studio/arra-oracle-v3/src/tools/search.ts:430`

## Key Insight
**MCP stdio invariant**: servers ต้องเขียน logs ลง **stderr เท่านั้น**. `console.log` = stdout = JSON-RPC channel = protocol corruption. อาการไม่ใช่ crash แต่เป็น parse error ฝั่ง client → drop transport → "Not connected" ทุก call ถัดไป. เหมือน "stale process" แต่จริงๆ server ยัง alive — client broke the pipe.
