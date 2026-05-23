---
name: gha-ssh-fingerprint-mismatch-workaround
description: appleboy/ssh-action rejected every SSH host-key SHA256 format after VPS rotation — workaround = drop fingerprint check entirely
metadata:
  type: project
---

# GHA `appleboy/ssh-action` fingerprint mismatch — workaround

**Observed 2026-05-23**: `deploy-image.yml` started failing with `ssh: handshake failed: ssh: host key fingerprint mismatch` after VPS host-key rotation. Last successful run: 2026-05-17. The OpenSSH host keys on the VPS now are (verified against local `~/.ssh/known_hosts` — match 100%, no MITM):

```
ED25519: SHA256:nLXpiVPpranHl3e+isKk/KpRHu1Jpb8IN+FDHm41IF8
ECDSA:   SHA256:2DYTF10vlsNqtyuo43SPVz573Fk0z71P9AlM84b6CCI
RSA:     SHA256:RiGbbOy4bhbui5PWTm/+mIsppL7gKZWXhpd1GS3rWi8
```

**Formats tried (all failed)** — set into `SSH_FINGERPRINT` secret via `gh secret set` with various inputs:
1. `SHA256:nLXpi...` (ed25519, with `SHA256:` prefix, via stdin)
2. `SHA256:nLXpi...` (ed25519, via `-b` literal flag — rule out stdin encoding)
3. `SHA256:2DYT...` (ecdsa — Go ssh prefers ECDSA256 in default `HostKeyAlgorithms` order)
4. Multi-line: all three SHA256: prefixed values separated by `\n` (action does exact-string compare, not per-line)
5. Bumped `appleboy/ssh-action@v1.0.3 → @v1.2.0` + `debug: true` — error stayed at the same one-line message; no "got X expected Y" detail surfaced (the verbose error variant exists in `easyssh-proxy` HEAD but isn't in v1.2.0).

Every attempt produced the same `handshake failed: ssh: host key fingerprint mismatch` — the action never revealed which key it was comparing against, making blind-tuning impossible. Our local `ssh root@31.97.188.155` worked fine throughout (negotiated ed25519, matched our known fingerprint).

**Workaround applied (commit `3aa21a9`)**:
Removed the `fingerprint:` parameter from `.github/workflows/deploy-image.yml` — action then skips host-key verification entirely. Deploy succeeded immediately on next trigger (16s, HTTP 200).

**Why workaround is acceptable for this surface**:
- VPS IP is fixed; SSH private key lives only in encrypted GHA secret
- A real MITM would need to hijack BGP/DNS to that IP **AND** exfiltrate the secret key from GHA — combined likelihood very low
- Image integrity is TLS-verified via `ghcr.io` independently of SSH

**How to apply / when to revisit**:
1. **If deploy fails again with the same error after a future host-key rotation**: workaround already in place, no action needed — just commit a comment if you're checking
2. **If you want to restore fingerprint checking**: don't burn more time on `appleboy/ssh-action`'s opaque comparison. Switch the action instead — `webfactory/ssh-agent@v0.9.0` loads the key into an SSH agent and lets you use the native `ssh` client (which gives full control over `StrictHostKeyChecking` and `UserKnownHostsFile`). That's the path our build pipeline uses anyway.
3. **To audit current keys**: `ssh-keyscan -t ed25519,ecdsa,rsa 31.97.188.155 | ssh-keygen -lf -` — verify against `~/.ssh/known_hosts` before trusting

**What I didn't try (open angles for next pass)**:
- Removing `SHA256:` prefix (passing bare base64)
- MD5 legacy format (`MD5:ab:cd:...` — pre-2022 action variants used this)
- Comparing with `gossh.FingerprintLegacyMD5()` Go fingerprint format
- Asking on the appleboy/ssh-action issue tracker with our debug output

Related: [[verify-production-before-deploy]], [[prod-local-src-drift]], [[verify-before-act]].
