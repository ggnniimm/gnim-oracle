# 2026-04-29 — Drive ID remap deploy: 4 gotchas

Deploying the Drive ID remap to prod surfaced four issues that didn't appear in the audit. All recoverable with the snapshot, but worth remembering for the next big prod deploy.

## 1. macOS `openrsync` cannot stat long-Thai filenames

`openrsync` (the macOS default `/usr/bin/rsync`, "protocol 29") escapes non-ASCII bytes as `\#NNN` octal sequences. Long Thai filenames blow past internal buffers and fail with `File name too long (36)`. Fix: install GNU rsync (`brew install rsync` → `/opt/homebrew/bin/rsync` 3.4.2). Not interchangeable.

## 2. ext4 NAME_MAX=255 bytes silently caps Thai filenames

Mac filesystem (APFS) allows ~765 UTF-8 bytes per filename. ext4 caps at 255 bytes. Thai is 3 bytes/char, so a 90-char Thai title easily exceeds 255 bytes and physically cannot be created on prod. 5 files in `data/md_backup/` were affected; they had been "local-only" since indexing started. Mitigation: rename to <250B locally before deploy. Detection script:

```bash
find . -maxdepth 1 -name '*.md' -print0 | while IFS= read -r -d '' f; do
  n=$(basename "$f"); b=$(echo -n "$n" | wc -c)
  [ "$b" -gt 255 ] && echo "$b  $n"
done
```

## 3. Gemini API keys expire silently; new keys may have different model access

The "working" key swapped in last session (`AIzaSyCE5T...`) was dead by the time we deployed (~12h later). New key (`AIzaSyAw...`) authenticated fine but only allowed `gemini-embedding-001/2/2-preview` — NOT `text-embedding-004`. Code already used `gemini-embedding-2-preview` (3072-dim) so it worked. Moral: `client.models.list()` to verify model access on every new key, don't assume parity.

## 4. Hostinger SSH flakes during deploys

SSH to `31.97.188.155:22` repeatedly dropped during the deploy session. TCP port was reachable (`nc -zv` succeeded) but SSH handshake timed out / ICMP blocked. Ming's fix: switch to phone hotspot, sometimes have to toggle. Already in `learnings_hostinger_vps_deploy.md`. Recurring enough that a long deploy should pre-confirm hotspot is ready.

## Net result

Deploy completed. Prod: 1,228 MD files, 27,713 Qdrant points (3072-dim). 5 too-long files documented as follow-up. `learnings_hostinger_vps_deploy.md` and `feedback_listmodels-before-guess` already covered some of this — extending here with the openrsync + ext4 NAME_MAX failure modes.
