# Mosquitto Auto-start + Extension Localhost Fix

**Date**: 2026-03-06
**Context**: /deep-research failed because MQTT broker wasn't running and extension pointed to remote URL

## Problems

1. **Mosquitto not running**: `/opt/homebrew/etc/mosquitto/mosquitto.conf` didn't exist (only `.example`). `brew services` showed `error` status.
2. **Extension hardcoded remote URL**: `background.js` line 7 had `wss://super-duper-...app.github.dev` instead of `ws://localhost:9001`

## Fixes

1. Created `mosquitto.conf` with dual listeners (TCP 1883 + WebSocket 9001) + `brew services restart mosquitto` for auto-start on boot
2. Changed `MQTT_URL` in `~/Downloads/claude-browser-proxy-main/background.js` to `ws://localhost:9001`

## Bonus: AppleScript fallback for reading Gemini

When extension `get_text`/`get_response` fails (chrome.scripting.executeScript timeout on Antigravity browser), use Chrome AppleScript:

```applescript
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if URL of t contains "gemini" then
        return execute t javascript "document.querySelector('message-content:last-of-type')?.innerText || document.body.innerText"
      end if
    end repeat
  end repeat
end tell
```

Requires: Chrome → View → Developer → Allow JavaScript from Apple Events

## Tags

`mqtt`, `mosquitto`, `extension`, `deep-research`, `applescript`
