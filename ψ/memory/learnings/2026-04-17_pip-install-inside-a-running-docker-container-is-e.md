---
title: pip install inside a running Docker container is ephemeral — always update requi
tags: [docker, dependencies, pip, requirements, production, deploy, ephemeral, ssh-tunnel]
created: 2026-04-17
source: rrr: gnim-oracle
---

# pip install inside a running Docker container is ephemeral — always update requi

pip install inside a running Docker container is ephemeral — always update requirements.txt immediately.

When you `pip install X` inside a running container as a hotfix:
- Works now (writable container layer)
- Gone on next `docker compose build app` (layer discarded)
- Future containers from same Dockerfile won't have it

Correct fix sequence:
1. pip install X (immediate hotfix)
2. Add X to requirements.txt
3. docker compose build app && docker compose up -d app (bake into image)

Always flag to user: "This fix is ephemeral — next container rebuild will lose it. Need to add to requirements.txt."

Bonus: pycrfsuite vs python-crfsuite — same library, different PyPI names. When `pip install pycrfsuite` fails ("no matching distribution"), try `python-crfsuite` instead (pure wheel, wider platform support).

Also: before SSH tunnel to a container port, always check `docker inspect <container> --format "{{json .HostConfig.PortBindings}}"` — empty {} means not exposed on host, tunnel will fail with connection reset.

---
*Added via Oracle Learn*
