"""
hermit/platforms/whatsapp.py — WhatsApp Web via Playwright
"""
from __future__ import annotations
import asyncio
from hermit.platforms.base import Platform, Message, Conversation

WHATSAPP_URL = "https://web.whatsapp.com"

COMPOSE_SEL = 'div[contenteditable="true"][data-tab="10"]'


class WhatsAppPlatform(Platform):
    name = "whatsapp"

    def __init__(self, store):
        super().__init__(store)
        self._current_convo_id = None

    async def login(self) -> bool:
        print("\n  Opening WhatsApp Web...")
        print("  Scan the QR code with your phone, then press Enter here.\n")
        await self._init_browser(headless=False)
        await self._page.goto(WHATSAPP_URL)
        input("  >> Press Enter after scanning: ")
        await self._save_session()
        await self._close_browser()
        print("  Session saved!\n")
        return True

    async def get_conversations(self) -> list[Conversation]:
        if not self.store.get_session(self.name):
            return []
        await self._ensure_page()
        if WHATSAPP_URL not in self._page.url:
            await self._page.goto(WHATSAPP_URL, wait_until="domcontentloaded", timeout=30000)
        try:
            await self._page.wait_for_selector('[data-testid="cell-frame-container"]', timeout=20000)
        except Exception:
            return []
        await asyncio.sleep(1.5)
        items = await self._page.query_selector_all('[data-testid="cell-frame-container"]')
        convos = []
        for item in items[:20]:
            try:
                name_el    = await item.query_selector('[data-testid="cell-frame-title"]')
                preview_el = await item.query_selector('[data-testid="last-msg-status"] ~ span, .x1iyjqo2')
                name       = (await name_el.inner_text()).strip() if name_el else ""
                preview    = (await preview_el.inner_text()).strip() if preview_el else ""
                if not name:
                    continue
                convos.append(Conversation(
                    id=name,
                    name=name[:35],
                    platform="whatsapp",
                    last_message=preview[:40],
                ))
            except Exception:
                continue
        self._current_convo_id = None
        return convos

    async def get_messages(self, convo_id: str, limit: int = 40) -> list[Message]:
        await self._ensure_page()
        if self._current_convo_id != convo_id:
            await self._open_convo(convo_id)
        try:
            msgs = []
            els  = await self._page.query_selector_all('[data-testid="msg-container"]')
            for i, el in enumerate(els[-limit:]):
                try:
                    text_el = await el.query_selector('.copyable-text, [data-pre-plain-text]')
                    text    = (await text_el.inner_text()).strip() if text_el else ""
                    if not text:
                        continue
                    cls   = await el.get_attribute("class") or ""
                    is_me = "message-out" in cls
                    msgs.append(Message(
                        id=f"wa_{i}",
                        sender="you" if is_me else convo_id,
                        text=text,
                        timestamp="",
                        is_me=is_me,
                    ))
                except Exception:
                    continue
            return msgs
        except Exception:
            return []

    async def send_message(self, convo_id: str, text: str) -> bool:
        await self._ensure_page()
        if self._current_convo_id != convo_id:
            await self._open_convo(convo_id)
        try:
            # Use same execCommand approach that works in headless
            await self._page.evaluate(
                '([s, t]) => { const el = document.querySelector(s); if (!el) return; el.focus(); document.execCommand("insertText", false, t); }',
                [COMPOSE_SEL, text]
            )
            await asyncio.sleep(0.15)
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(0.5)
            return True
        except Exception:
            return False

    async def _open_convo(self, convo_id: str):
        """Search and open a conversation by name."""
        try:
            # Click search, type name, click first result
            search = await self._page.wait_for_selector(
                '[data-testid="search-container"] [contenteditable="true"], [title="Search input textbox"]',
                timeout=8000
            )
            await search.click()
            # Clear and type via execCommand so it works headless
            await self._page.evaluate(
                '([s, t]) => { const el = document.querySelector(s); if (!el) return; el.focus(); document.execCommand("selectAll"); document.execCommand("insertText", false, t); }',
                ['[data-testid="search-container"] [contenteditable="true"]', convo_id]
            )
            await asyncio.sleep(1.5)
            result = await self._page.query_selector('[data-testid="cell-frame-container"]')
            if result:
                await result.click()
                await asyncio.sleep(1.0)
                # Pre-focus compose box
                try:
                    await self._page.wait_for_selector(COMPOSE_SEL, timeout=5000, state="attached")
                except Exception:
                    pass
                await self._page.evaluate(
                    '(s) => { const el = document.querySelector(s); if (el) el.focus(); }',
                    COMPOSE_SEL
                )
        except Exception:
            pass
        self._current_convo_id = convo_id

    async def _ensure_page(self):
        if self._page is None:
            await self._init_browser(headless=True)