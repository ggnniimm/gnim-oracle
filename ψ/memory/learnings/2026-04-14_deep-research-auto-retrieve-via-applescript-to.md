---
title: ## Deep Research Auto-Retrieve via AppleScript
tags: [deep-research, applescript, automation, chrome]
created: 2026-04-14
source: Deep research auto-retrieve feature 2026-03-06
---

# ## Deep Research Auto-Retrieve via AppleScript

## Deep Research Auto-Retrieve via AppleScript

To auto-retrieve Gemini Deep Research results without manual polling:
1. After starting research, poll via AppleScript every 5 seconds until result appears
2. AppleScript → Chrome JavaScript works reliably when extension's `get_text`/`get_response` fails (chrome.scripting.executeScript timeout on Antigravity browser)

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

**Prerequisite**: Chrome → View → Developer → Allow JavaScript from Apple Events

**Known issue**: Grabs "last Gemini tab" — if multiple tabs exist, may grab wrong one.

---
*Added via Oracle Learn*
