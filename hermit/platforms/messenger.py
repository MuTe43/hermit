"""
hermit/platforms/messenger.py — Facebook Messenger via Playwright
"""
from __future__ import annotations
import asyncio
from hermit.platforms.base import Platform, Message, Conversation

MESSENGER_URL = "https://www.messenger.com"

JS_GET_CONVOS = (
    "() => {"
    "  const results = [], seen = new Set();"
    "  for (const link of document.querySelectorAll('a[href*=\"/t/\"]')) {"
    "    const href = link.getAttribute('href') || '';"
    "    const tid = href.split('/t/')[1]?.replace(/\\/+$/, '');"
    "    if (!tid || seen.has(tid)) continue;"
    "    seen.add(tid);"
    "    const raw = (link.querySelector('span[dir=\"auto\"]') || link).innerText || '';"
    "    const lines = raw.trim().split('\\n').map(s => s.trim()).filter(Boolean);"
    "    const name = lines[0];"
    "    if (!name) continue;"
    "    results.push({ id: tid, name: name.slice(0, 35), preview: lines.slice(1).join(' ').slice(0, 40) });"
    "    if (results.length >= 20) break;"
    "  }"
    "  return results;"
    "}"
)

JS_GET_MESSAGES = (
    "(limit) => {"
    "  const SKIP = new Set(['Enter','Like','More','Reply','React','Send','GIF','Sticker','Unsend','Remove','Seen','Delivered','Mon','Tue','Wed','Thu','Fri','Sat','Sun','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday','Today','Yesterday']);"
    "  const DAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday','Today','Yesterday'];"
    "  const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];"
    "  const isTS = s => {"
    "    if (!s) return false;"
    "    if (/^\\d{1,2}[:/]\\d{2}/.test(s) || /^\\d{1,2}\\/\\d{1,2}/.test(s)) return true;"
    "    return [...DAYS, ...MONTHS].some(w => s.startsWith(w));"
    "  };"
    "  const isName = s => s && s.length >= 2 && s.length <= 50 && !isTS(s) && !SKIP.has(s) && !/^(You |This |The |A )/.test(s);"
    "  const msgs = [];"
    "  for (const bubble of document.querySelectorAll('div[dir=\"auto\"]')) {"
    "    let text = (bubble.innerText || '').trim();"
    "    if (!text) {"
    "      text = Array.from(bubble.querySelectorAll('img[alt]')).map(i => i.getAttribute('alt')).join('').trim();"
    "    } else {"
    "      for (const img of bubble.querySelectorAll('img[alt]')) {"
    "        const alt = img.getAttribute('alt') || '';"
    "        if (alt && !text.includes(alt)) text += alt;"
    "      }"
    "    }"
    "    if (!text || text.length > 2000) continue;"
    "    const rect = bubble.getBoundingClientRect();"
    "    if (rect.width === 0) continue;"
    "    let node = bubble, isMe = false;"
    "    for (let j = 0; j < 12; j++) {"
    "      if (!node.parentElement) break;"
    "      node = node.parentElement;"
    "      const scope = node.getAttribute('data-scope') || '';"
    "      if (scope === 'outgoing' || (node.className && node.className.includes('outgoing'))) { isMe = true; break; }"
    "      if (j === 11) isMe = (rect.left + rect.width / 2) > (window.innerWidth * 0.6);"
    "    }"
    "    msgs.push({ text, isMe, x: rect.left, y: rect.top, w: rect.width, h: rect.height });"
    "  }"
    "  const chatLeft = window.innerWidth * 0.25;"
    "  const labels = [];"
    "  for (const el of document.querySelectorAll('span, div')) {"
    "    if (el.children.length > 0) continue;"
    "    const t = (el.innerText || '').trim();"
    "    if (!t || t.length > 60 || t.length < 2) continue;"
    "    const r = el.getBoundingClientRect();"
    "    if (r.width === 0 || r.height === 0 || r.left < chatLeft) continue;"
    "    labels.push({ text: t, y: r.top });"
    "  }"
    "  const imgMap = [];"
    "  for (const img of document.querySelectorAll('img[src]')) {"
    "    const src = img.getAttribute('src') || '';"
    "    if (!src.startsWith('http') || src.includes('emoji') || src.includes('static') || src.includes('rsrc')) continue;"
    "    const r = img.getBoundingClientRect();"
    "    if (r.left < chatLeft || r.width < 80 || r.height < 80) continue;"
    "    const ratio = r.width / r.height;"
    "    if (ratio > 0.85 && ratio < 1.15 && r.width < 120) continue;"
    "    let node = img, inNav = false, isMe = false;"
    "    for (let j = 0; j < 14; j++) {"
    "      if (!node.parentElement) break;"
    "      node = node.parentElement;"
    "      const role = node.getAttribute('role') || '';"
    "      if (['navigation','list','listitem','grid'].includes(role)) { inNav = true; break; }"
    "      const scope = node.getAttribute('data-scope') || '';"
    "      if (scope === 'outgoing' || (node.className && node.className.includes('outgoing'))) isMe = true;"
    "    }"
    "    if (inNav) continue;"
    "    if (!isMe) isMe = (r.left + r.width / 2) > (window.innerWidth * 0.6);"
    "    imgMap.push({ src, isMe, y: img.offsetTop || (r.top + window.scrollY) });"
    "  }"
    "  imgMap.sort((a, b) => a.y - b.y);"
    "  const msgTexts = new Set(msgs.map(m => m.text));"
    "  const result = [];"
    "  let lastSender = '';"
    "  for (const msg of msgs) {"
    "    let sender = '', timestamp = '';"
    "    for (const lbl of labels) {"
    "      if (lbl.text === msg.text || msgTexts.has(lbl.text)) continue;"
    "      if (Math.abs(lbl.y - msg.y) > 80) continue;"
    "      if (isTS(lbl.text)) { if (!timestamp) timestamp = lbl.text; continue; }"
    "      if (!sender && !msg.isMe && isName(lbl.text)) sender = lbl.text;"
    "    }"
    "    if (!msg.isMe) {"
    "      if (sender && !isTS(sender) && !msgTexts.has(sender)) lastSender = sender;"
    "      else if (!timestamp) sender = lastSender;"
    "      else lastSender = '';"
    "    } else { lastSender = ''; }"
    "    result.push({ text: msg.text, isMe: msg.isMe, sender, timestamp, images: [], _y: msg.y + window.scrollY });"
    "  }"
    "  for (const img of imgMap) {"
    "    let closest = null, minDist = 200;"
    "    for (const r of result) {"
    "      const d = Math.abs(r._y - img.y);"
    "      if (d < minDist) { minDist = d; closest = r; }"
    "    }"
    "    if (closest) closest.images.push(img.src);"
    "    else result.push({ text: '', isMe: img.isMe, sender: '', timestamp: '', images: [img.src], _y: img.y });"
    "  }"
    "  return result.filter(r => r.text || r.images.length).slice(-limit);"
    "}"
)


class MessengerPlatform(Platform):
    name = "messenger"

    def __init__(self, store):
        super().__init__(store)
        self._current_convo_id = None

    async def login(self) -> bool:
        print("\n  Opening Messenger in your browser...")
        print("  Log in, then come back here and press Enter.\n")
        await self._init_browser(headless=False)
        await self._page.goto(MESSENGER_URL)
        input("  >> Press Enter once you're logged in: ")
        await self._save_session()
        await self._close_browser()
        print("  Session saved. You won't need to log in again.\n")
        return True

    async def get_conversations(self) -> list[Conversation]:
        if not self.store.get_session(self.name):
            return []
        await self._ensure_page()
        if MESSENGER_URL not in self._page.url:
            await self._page.goto(MESSENGER_URL, wait_until="domcontentloaded", timeout=30000)
        if "login" in self._page.url:
            return []
        try:
            await self._page.wait_for_selector('a[href*="/t/"]', timeout=12000)
        except Exception:
            return []
        raw = await self._page.evaluate(JS_GET_CONVOS)
        self._current_convo_id = None
        return [
            Conversation(id=r["id"], name=r["name"], platform="messenger", last_message=r.get("preview", ""))
            for r in raw
        ]

    async def _nav_to_convo(self, convo_id: str):
        """Navigate to a conversation and wait for it to fully load."""
        await self._page.goto(
            f"{MESSENGER_URL}/t/{convo_id}/",
            wait_until="domcontentloaded",
            timeout=20000
        )
        try:
            await self._page.wait_for_selector('[role="main"]', timeout=10000)
        except Exception:
            pass
        await asyncio.sleep(1.0)
        # Scroll to bottom of chat container
        await self._page.evaluate("""
            () => {
                for (const sel of ['[role="main"] [data-virtualized]', '[role="grid"]', '[role="main"]']) {
                    const el = document.querySelector(sel);
                    if (el && el.scrollHeight > el.clientHeight) { el.scrollTop = el.scrollHeight; return; }
                }
                window.scrollTo(0, document.body.scrollHeight);
            }
        """)
        await asyncio.sleep(0.4)
        # Pre-focus textbox so first send works immediately
        try:
            await self._page.wait_for_selector(
                'div[contenteditable="true"][role="textbox"]',
                timeout=5000, state="attached"
            )
        except Exception:
            pass
        await self._page.evaluate("""
            () => {
                const el = document.querySelector('div[contenteditable="true"][role="textbox"]');
                if (el) el.focus();
            }
        """)
        self._current_convo_id = convo_id

    async def get_messages(self, convo_id: str, limit: int = 40) -> list[Message]:
        await self._ensure_page()
        if self._current_convo_id != convo_id:
            await self._nav_to_convo(convo_id)
        raw = await self._page.evaluate(JS_GET_MESSAGES, limit)
        return [
            Message(
                id=f"msg_{i}",
                sender="you" if m["isMe"] else (m["sender"] or "?"),
                text=m["text"],
                timestamp=m["timestamp"],
                is_me=m["isMe"],
                attachments=m.get("images", [])
            )
            for i, m in enumerate(raw)
        ]

    async def send_message(self, convo_id: str, text: str) -> bool:
        await self._ensure_page()
        if self._current_convo_id != convo_id:
            await self._nav_to_convo(convo_id)
        try:
            await self._page.evaluate(
                '([s, t]) => { const el = document.querySelector(s); if (!el) return; el.focus(); document.execCommand("insertText", false, t); }',
                ['div[contenteditable="true"][role="textbox"]', text]
            )
            await asyncio.sleep(0.15)
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(0.5)
            return True
        except Exception:
            return False

    async def _ensure_page(self):
        if self._page is None:
            await self._init_browser(headless=True)