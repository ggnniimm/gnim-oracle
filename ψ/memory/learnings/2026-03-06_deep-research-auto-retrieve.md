# Deep Research Auto-Retrieve via AppleScript

**Date**: 2026-03-06
**Context**: Ming asked "ทำยังไงให้ผลมาเลย โดยไม่ต้องบอก"

## Solution

Added step 5 to `deep-research.ts`: after starting research, poll via AppleScript every 5 seconds until result appears, then print it.

```typescript
// Poll via osascript → Chrome JavaScript execution
// Checks last Gemini tab for message-content element
// Returns __STILL_LOADING__ if spinner visible or no content
// Returns full text when done
```

**Why AppleScript instead of MQTT extension?**
Extension's `get_response`/`get_text` commands use `chrome.scripting.executeScript` which doesn't respond (timeout) on Antigravity browser. AppleScript → Chrome JavaScript works reliably.

**Prerequisite**: Chrome → View → Developer → Allow JavaScript from Apple Events

## Known Issue

Script grabs "last Gemini tab" — if multiple tabs exist, may grab wrong one. Should track specific tab created in step 1.

## Tags

`deep-research`, `applescript`, `automation`, `chrome`
