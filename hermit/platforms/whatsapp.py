"""
hermit/platforms/whatsapp.py — WhatsApp Web via Playwright
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from hermit.platforms.base import Platform, Message, Conversation

WHATSAPP_URL = "https://web.whatsapp.com"


class WhatsAppPlatform(Platform):
    name = "whatsapp"

    async def login(self) -> bool:
        print("\n  Opening WhatsApp Web...")
        print("  Scan the QR code with your phone, then press Enter here.\n")
        await self._init_browser(headless=False)
        await self._page.goto(WHATSAPP_URL)
        input("  >> Press Enter after scanning the QR code: ")
        await self._save_session()
        await self._close_browser()
        print("  Session saved!\n")
        return True

    async def get_conversations(self) -> list[Conversation]:
        if not self.store.get_session(self.name):
            print("  Not logged in. Run: hermit login wa")
            return []

        await self._ensure_page()
        print("  Loading WhatsApp...")
        await self._page.goto(WHATSAPP_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        try:
            await self._page.wait_for_selector('[data-testid="cell-frame-container"]', timeout=15000)
            items = await self._page.query_selector_all('[data-testid="cell-frame-container"]')
            convos = []

            for item in items[:20]:
                try:
                    name_el = await item.query_selector('[data-testid="cell-frame-title"]')
                    name = await name_el.inner_text() if name_el else "Unknown"
                    convo_id = name.replace(" ", "_").lower()

                    convos.append(Conversation(
                        id=convo_id,
                        name=name.strip()[:35],
                        platform="whatsapp",
                        last_message="",
                        unread=0
                    ))
                except Exception:
                    continue

            return convos
        except Exception as e:
            print(f"  Error: {e}")
            return []

    async def get_messages(self, convo_id: str, limit: int = 40) -> list[Message]:
        await self._ensure_page()
        # Click the right conversation by searching
        name = convo_id.replace("_", " ")
        try:
            search = await self._page.wait_for_selector(
                '[data-testid="search-input"], [title="Search input textbox"]',
                timeout=8000
            )
            await search.evaluate("el => el.focus()")
            await self._page.keyboard.type(name, delay=50)
            await asyncio.sleep(1.5)
            result = await self._page.query_selector('[data-testid="cell-frame-container"]')
            if result:
                await result.evaluate("el => el.click()")
                await asyncio.sleep(2)
        except Exception as e:
            print(f"  Could not open conversation: {e}")
            return []

        try:
            msgs = []
            els = await self._page.query_selector_all('[data-testid="msg-container"]')
            for i, el in enumerate(els[-limit:]):
                try:
                    text_el = await el.query_selector('.copyable-text')
                    text = await text_el.inner_text() if text_el else ""
                    if not text:
                        continue
                    class_attr = await el.get_attribute("class") or ""
                    is_me = "message-out" in class_attr
                    msgs.append(Message(
                        id=f"wa_{i}",
                        sender="you" if is_me else name,
                        text=text.strip(),
                        timestamp="",
                        is_me=is_me
                    ))
                except Exception:
                    continue
            return msgs
        except Exception as e:
            print(f"  Error loading messages: {e}")
            return []

    async def send_message(self, convo_id: str, text: str) -> bool:
        await self._ensure_page()
        try:
            focused = await self._page.evaluate("""
                () => {
                    const el = document.querySelector('[data-testid="conversation-compose-box-input"]')
                           || document.querySelector('div[contenteditable="true"]');
                    if (el) { el.focus(); return true; }
                    return false;
                }
            """)
            if not focused:
                return False
            await asyncio.sleep(0.3)
            await self._page.keyboard.type(text, delay=40)
            await asyncio.sleep(0.3)
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(1)
            return True
        except Exception as e:
            print(f"  Send failed: {e}")
            return False

    async def _ensure_page(self):
        if self._page is None:
            await self._init_browser(headless=True)