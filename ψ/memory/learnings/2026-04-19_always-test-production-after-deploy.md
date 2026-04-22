---
name: Always test production after deploying a fix
description: Ming's explicit instruction — after deploying any fix, run eval on production server, not just local
type: feedback
date: 2026-04-19
---

After deploying any bug fix to production, always run the relevant TC eval on the production server.

**Why:** Ming explicitly said "อยากให้ทำเป็นนิสัยเลย หลังแก้ก็ test ให้ด้วยเลย" after a session where local tests passed but production hadn't been verified. Local and production aren't the same environment — reindex may not have applied, docker image may be stale, paths may differ.

**How to apply:**
```bash
# After rsync + reindex, always verify with:
docker exec thai-legal-rag-app-1 python3 /app/pipeline/run_eval.py --id TC-XXX -v

# Production server: root@31.97.188.155
# Eval script path inside container: /app/pipeline/run_eval.py
# MD files path inside container: /app/thai-legal-rag/data/md_backup/
# rsync target: root@31.97.188.155:/app/thai-legal-rag/data/md_backup/
```

Never report "fix สำเร็จ" after local test only. Always deploy → reindex → eval on production as a complete unit.
