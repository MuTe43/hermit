"""
hermit/platforms/base.py — Abstract base for all messaging platforms
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    id: str
    sender: str
    text: str
    timestamp: str
    is_me: bool
    attachments: list = field(default_factory=list)


@dataclass
class Conversation:
    id: str
    name: str
    platform: str
    last_message: str = ""
    unread: int = 0
    avatar: Optional[str] = None


class Platform(ABC):
    name: str = "base"

    def __init__(self, store):
        self.store = store
        self._browser = None
        self._page = None
        self._context = None
        self._pw = None

    @abstractmethod
    async def login(self) -> bool: ...

    @abstractmethod
    async def get_conversations(self) -> list[Conversation]: ...

    @abstractmethod
    async def get_messages(self, convo_id: str, limit: int = 50) -> list[Message]: ...

    @abstractmethod
    async def send_message(self, convo_id: str, text: str) -> bool: ...

    async def _init_browser(self, headless: bool = True):
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=headless)
        kwargs = {}
        session = self.store.get_session(self.name)
        if session:
            kwargs["storage_state"] = session
        self._context = await self._browser.new_context(**kwargs)
        self._page = await self._context.new_page()

    async def _save_session(self):
        if self._context:
            state = await self._context.storage_state()
            self.store.save_session(self.name, state)

    async def _close_browser(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._browser = None
        self._page = None
        self._context = None
        self._pw = None