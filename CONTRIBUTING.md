# Contributing to hermit

## Setup

```bash
git clone https://github.com/yourusername/hermit
cd hermit
pip install -e .
playwright install chromium
```

## Adding a platform

1. Create `hermit/platforms/yourplatform.py`
2. Subclass `Platform` from `hermit.platforms.base`
3. Implement: `login`, `get_conversations`, `get_messages`, `send_message`
4. Register it in `hermit/app.py` in the `self.platforms` dict and add a switch key

Use `headless=False` while developing so you can see what the browser is doing.

## Debugging selectors

```python
import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.messenger.com")
        input("Explore the page, then press Enter to close")
        await browser.close()

asyncio.run(debug())
```

## What needs help

- Better selector resilience (Messenger/WhatsApp update their HTML constantly)
- Telegram support via official API
- iMessage on macOS via AppleScript
- OS-level notifications for new messages
- Unread message counts
- Image/attachment indicators