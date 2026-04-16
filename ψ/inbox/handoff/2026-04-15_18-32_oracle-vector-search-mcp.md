# Handoff: Oracle KB Vector Search + MCP Debug

**Date**: 2026-04-15 10:30
**Branch**: feat/admin-court-judgments

## What We Did
- ทดสอบ vector search บน Oracle knowledge base ผ่าน arra-oracle-v2 MCP tools
- Confirmed: Qdrant server connected, 1,788 docs (944 learning, 804 retro, 40 principle), 8,272 FTS indexed
- ทดสอบ 3 modes: vector ✅ (6 matches), fts ❌ (Not connected), hybrid ✅ (fallback to vector)
- พบว่า FTS server ไม่ connected — hybrid ยังทำงานได้โดย fallback
- MCP server (arra-oracle-v2) disconnect ระหว่าง session — process ยังรันอยู่ (PID 86462)
- Kill stale process แล้ว — ต้อง restart Claude Code เพื่อ reconnect

## Pending
- [ ] ตรวจสอบว่า FTS "Not connected" เป็น bug หรือ expected behavior
- [ ] ยืนยันว่า arra-oracle-v2 reconnect สำเร็จหลัง restart
- [ ] Open PRs: #13 TC-051, #12 TC-011, #11 Eval regression

## Next Session
- [ ] `/recap` เพื่อ orient session ใหม่
- [ ] ตรวจสอบ FTS status หลัง restart: `arra_stats` แล้วดู `fts_status`
- [ ] พิจารณา merge หรือ close PR #11 (Eval regression — อาจ stale)

## Key Files
- arra-oracle-v2 server: `~/.arra-oracle/node_modules/arra-oracle-v2/src/index.ts`
- MCP config: `.claude/settings.local.json`
