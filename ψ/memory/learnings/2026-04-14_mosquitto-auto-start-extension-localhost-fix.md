---
title: ## Mosquitto Auto-start + Extension Localhost Fix
tags: [mqtt, mosquitto, extension, deep-research, local-setup]
created: 2026-04-14
source: Deep research MQTT setup 2026-03-06
---

# ## Mosquitto Auto-start + Extension Localhost Fix

## Mosquitto Auto-start + Extension Localhost Fix

For deep-research MQTT setup on Mac:
1. Create `/opt/homebrew/etc/mosquitto/mosquitto.conf` with dual listeners (TCP 1883 + WebSocket 9001) — the `.example` file alone isn't enough
2. `brew services restart mosquitto` for auto-start on boot
3. Change `MQTT_URL` in `~/Downloads/claude-browser-proxy-main/background.js` from remote URL to `ws://localhost:9001`

**AppleScript fallback** when extension fails: Use Chrome AppleScript with "Allow JavaScript from Apple Events" permission. More reliable than chrome.scripting.executeScript on Antigravity browser.

---
*Added via Oracle Learn*
