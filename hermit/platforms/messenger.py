"""
hermit/platforms/messenger.py — Facebook Messenger via Playwright (fast)
"""
from __future__ import annotations
import asyncio
from hermit.platforms.base import Platform, Message, Conversation

MESSENGER_URL = "https://www.messenger.com"

JS_GET_CONVOS = (
    "() => {"
    "  const results = [];"
    "  const seen = new Set();"
    "  const links = document.querySelectorAll('a[href*=\"/t/\"]');"
    "  for (const link of links) {"
    "    const href = link.getAttribute('href') || '';"
    "    if (!href.includes('/t/')) continue;"
    "    const parts = href.split('/t/');"
    "    const thread_id = parts[1] ? parts[1].replace(/[/]+$/, '') : null;"
    "    if (!thread_id || seen.has(thread_id)) continue;"
    "    seen.add(thread_id);"
    "    const nameEl = link.querySelector('span[dir=\"auto\"]');"
    "    const raw = (nameEl ? nameEl.innerText : link.innerText) || '';"
    "    const lines = raw.trim().split('\\n').map(s => s.trim()).filter(Boolean);"
    "    const name = lines[0] || '';"
    "    const preview = lines.slice(1).join(' ').slice(0, 40);"
    "    if (!name) continue;"
    "    results.push({ id: thread_id, name: name.slice(0, 35), preview });"
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
    "  const isTS = (s) => {"
    "    if (!s) return false;"
    "    if (/^\\d{1,2}[:/]\\d{2}/.test(s)) return true;"
    "    if (/^\\d{1,2}\\/\\d{1,2}/.test(s)) return true;"
    "    for (const w of DAYS) { if (s.startsWith(w)) return true; }"
    "    for (const w of MONTHS) { if (s.startsWith(w)) return true; }"
    "    return false;"
    "  };"
    "  const isName = (s) => {"
    "    if (!s || s.length < 2 || s.length > 50) return false;"
    "    if (isTS(s)) return false;"
    "    if (SKIP.has(s)) return false;"
    "    if (/^(You |This |The |A )/.test(s)) return false;"
    "    return true;"
    "  };"
    # Use aria-label on the message list to find the outgoing container boundary
    # More reliable: find the actual sent-by-me container using data attributes
    "  const chatLeft = window.innerWidth * 0.28;"
    "  const imgMap = [];"
    "  const allImgs = document.querySelectorAll('img[src]');"
    "  for (const img of allImgs) {"
    "    const src = img.getAttribute('src') || '';"
    "    if (!src.startsWith('http')) continue;"
    "    if (src.includes('emoji') || src.includes('static') || src.includes('rsrc')) continue;"
    "    const r = img.getBoundingClientRect();"
    "    if (r.left < chatLeft) continue;"
    "    if (r.width < 80 || r.height < 80) continue;"
    "    const ratio = r.width / r.height;"
    "    if (ratio > 0.85 && ratio < 1.15 && r.width < 120) continue;"
    "    let node = img; let inNav = false; let isMe = false;"
    "    for (let j = 0; j < 14; j++) {"
    "      if (!node.parentElement) break; node = node.parentElement;"
    "      const role = node.getAttribute('role') || '';"
    "      if (role === 'navigation' || role === 'list' || role === 'listitem' || role === 'grid') { inNav = true; break; }"
    "      const scope = node.getAttribute('data-scope') || '';"
    "      if (scope === 'outgoing' || (node.className && node.className.includes('outgoing'))) isMe = true;"
    "    }"
    "    if (inNav) continue;"
    "    if (!isMe) isMe = (r.left + r.width / 2) > (window.innerWidth * 0.6);"
    "    imgMap.push({ src, isMe, y: r.top });"
    "  }"
    "  const msgs = [];"
    "  const bubbles = document.querySelectorAll('div[dir=\"auto\"]');"
    "  for (const bubble of bubbles) {"
    "    const text = (bubble.innerText || '').trim();"
    "    if (!text || text.length > 2000) continue;"
    "    const rect = bubble.getBoundingClientRect();"
    "    if (rect.width === 0) continue;"
    # Walk up to check for outgoing markers — more reliable than position
    "    let node = bubble;"
    "    let isMe = false;"
    "    for (let j = 0; j < 12; j++) {"
    "      if (!node.parentElement) break;"
    "      node = node.parentElement;"
    "      const scope = node.getAttribute('data-scope') || '';"
    "      const cls = node.className || '';"
    "      if (scope === 'outgoing' || cls.includes('outgoing')) { isMe = true; break; }"
    # Fallback to position only if no explicit marker found
    "      if (j === 11) {"
    "        isMe = (rect.left + rect.width / 2) > (window.innerWidth * 0.6);"
    "      }"
    "    }"
    "    msgs.push({ text, isMe, x: rect.left, y: rect.top, w: rect.width, h: rect.height });"
    "  }"
    # Collect labels only from chat area (exclude sidebar left 25%)
    "  const labels = [];"
    "  const allEls = document.querySelectorAll('span, div');"
    "  for (const el of allEls) {"
    "    if (el.children.length > 0) continue;"
    "    const t = (el.innerText || '').trim();"
    "    if (!t || t.length > 60 || t.length < 2) continue;"
    "    const r = el.getBoundingClientRect();"
    "    if (r.width === 0 || r.height === 0 || r.left < chatLeft) continue;"
    "    labels.push({ text: t, y: r.top, x: r.left });"
    "  }"
    # Match labels to messages; carry sender forward for consecutive messages
    "  const msgTexts = new Set(msgs.map(m => m.text));"
    "  const result = [];"
    "  let lastSender = '';"
    "  for (const msg of msgs) {"
    "    let sender = '';"
    "    let timestamp = '';"
    "    for (const lbl of labels) {"
    "      if (lbl.text === msg.text) continue;"
    "      if (msgTexts.has(lbl.text)) continue;"
    "      const dist = Math.abs(lbl.y - msg.y);"
    "      if (dist > 80) continue;"
    "      if (isTS(lbl.text)) { if (!timestamp) timestamp = lbl.text; continue; }"
    "      if (!sender && !msg.isMe && isName(lbl.text)) sender = lbl.text;"
    "    }"
    # Carry sender forward if same side and no new name found
    "    if (!msg.isMe) {"
    "      if (sender && !isTS(sender) && !msgTexts.has(sender)) {"
    "        lastSender = sender;"
    "      } else {"
    "        sender = lastSender;"
    "      }"
    "      if (timestamp) lastSender = '';"
    "    } else {"
    "      lastSender = '';"
    "    }"
    "    result.push({ text: msg.text, isMe: msg.isMe, sender, timestamp, images: [], _y: msg.y });"
    "  }"
    "  for (const img of imgMap) {"
    "    let closest = null; let minDist = 120;"
    "    for (const r of result) {"
    "      if (!r._y) continue;"
    "      const d = Math.abs(r._y - img.y);"
    "      if (d < minDist) { minDist = d; closest = r; }"
    "    }"
    "    if (closest) { closest.images.push(img.src); }"
    "    else { result.push({ text: '', isMe: img.isMe, sender: '', timestamp: '', images: [img.src] }); }"
    "  }"
    "  return result.filter(r => r.text || r.images.length).slice(-limit);"
    "}"
)

JS_FOCUS_INPUT = (
    "() => {"
    "  const el = document.querySelector('div[contenteditable=\"true\"][role=\"textbox\"]')"
    "          || document.querySelector('div[contenteditable=\"true\"]');"
    "  if (el) { el.focus(); return true; }"
    "  return false;"
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
            import tempfile, os
            tmp = os.path.join(tempfile.gettempdir(), "hermit_debug.png")
            await self._page.screenshot(path=tmp)
            return []
        raw = await self._page.evaluate(JS_GET_CONVOS)
        convos = [Conversation(id=r["id"], name=r["name"], platform="messenger", last_message=r.get("preview","")) for r in raw]
        self._current_convo_id = None
        return convos

    async def get_messages(self, convo_id: str, limit: int = 40) -> list[Message]:
        await self._ensure_page()
        if self._current_convo_id != convo_id:
            await self._page.goto(
                f"{MESSENGER_URL}/t/{convo_id}/",
                wait_until="domcontentloaded", timeout=20000
            )
            try:
                await self._page.wait_for_selector('div[dir="auto"]', timeout=10000)
                await asyncio.sleep(0.8)
            except Exception:
                import tempfile, os
                tmp = os.path.join(tempfile.gettempdir(), "hermit_debug_chat.png")
                await self._page.screenshot(path=tmp)
                return []
            self._current_convo_id = convo_id

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
            for i, m in enumerate(raw) if m["text"] or m.get("images")
        ]

    async def send_message(self, convo_id: str, text: str) -> bool:
        await self._ensure_page()
        if self._current_convo_id != convo_id:
            await self._page.goto(
                f"{MESSENGER_URL}/t/{convo_id}/",
                wait_until="domcontentloaded", timeout=20000
            )
            await self._page.wait_for_selector('div[contenteditable="true"]', timeout=8000)
            self._current_convo_id = convo_id
        try:
            sent = await self._page.evaluate("""
                (msg) => {
                    const el = document.querySelector('div[contenteditable="true"][role="textbox"]')
                            || document.querySelector('div[contenteditable="true"]');
                    if (!el) return false;
                    el.focus();
                    // Try modern InputEvent first, fall back to execCommand
                    try {
                        const dt = new DataTransfer();
                        dt.setData('text/plain', msg);
                        el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true }));
                        if (el.innerText.trim() === '') {
                            document.execCommand('insertText', false, msg);
                        }
                    } catch(e) {
                        document.execCommand('insertText', false, msg);
                    }
                    return el.innerText.trim().length > 0;
                }
            """, text)
            if not sent:
                return False
            await asyncio.sleep(0.2)
            await self._page.keyboard.press("Enter")
            await asyncio.sleep(0.3)
            return True
        except Exception as e:
            print(f"  Send failed: {e}")
            return False

    async def _ensure_page(self):
        if self._page is None:
            await self._init_browser(headless=True)