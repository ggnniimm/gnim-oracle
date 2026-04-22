---
title: Always test on production after deploying a fix — not just local. Ming's explici
tags: [production-testing, deploy-habit, thai-legal-rag, eval, docker]
created: 2026-04-19
source: rrr: gnim-oracle-qdrant
---

# Always test on production after deploying a fix — not just local. Ming's explici

Always test on production after deploying a fix — not just local. Ming's explicit instruction: "ทำเป็นนิสัยเลย หลังแก้ก็ test ให้ด้วยเลย". Deploy → reindex → eval on production as one complete unit. Command: `docker exec thai-legal-rag-app-1 python3 /app/pipeline/run_eval.py --id TC-XXX -v`. Never report fix success after local test only.

---
*Added via Oracle Learn*
