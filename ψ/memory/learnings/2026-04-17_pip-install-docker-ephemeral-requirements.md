# pip install Inside Docker Container is Ephemeral — Always Update requirements.txt

**Date**: 2026-04-17
**Context**: Fixed missing `pycrfsuite` in production container by running `pip install python-crfsuite`. Fix worked but won't survive container rebuild.
**Tags**: #docker #dependencies #requirements #pipeline #production

## Problem

`pip install` inside a running Docker container installs the package into the container's writable layer. This layer is:
- **Alive** as long as the container runs
- **Gone** when the container is rebuilt (`docker compose build app`)
- **Not in the image** — future containers from the same Dockerfile won't have it

So `pip install X` as a hotfix works once, but breaks silently on next rebuild.

## Specific Case

Production app container was missing `pycrfsuite` (needed by pythainlp crfcut tokenizer in `pipeline/index_md_folder.py`). Fix:
```bash
docker exec thai-legal-rag-app-1 pip install python-crfsuite
```
This worked for the immediate reindex. But `requirements.txt` still doesn't have `python-crfsuite` → next `docker compose build app` will lose it.

## Correct Fix

1. Add to `requirements.txt`:
   ```
   python-crfsuite
   ```
2. Rebuild image:
   ```bash
   docker compose build app
   docker compose up -d app
   ```

## Bonus: pycrfsuite vs python-crfsuite

`pycrfsuite` (C extension, fails on some platforms) and `python-crfsuite` (pure wheel, wider compatibility) are the same library with different PyPI distribution names. When `pip install pycrfsuite` fails with "no matching distribution found," try `python-crfsuite` instead.

## Rule

**Whenever you do `pip install X` as a container hotfix, immediately flag to the user:** "This fix is ephemeral — container rebuild will lose it. Need to add to requirements.txt."

Don't complete the task and stay silent about the fragility. The user may not know Docker image vs container layer semantics.
