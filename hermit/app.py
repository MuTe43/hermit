"""
hermit/app.py — Terminal UI (brutalist noir aesthetic)
"""
import sys
import os
import asyncio
from datetime import datetime

from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt

from hermit.store import SessionStore
from hermit.platforms.messenger import MessengerPlatform
from hermit.platforms.whatsapp import WhatsAppPlatform
from hermit.platforms.base import Message
from hermit.media import download_image, open_file, cleanup_old_media

# ── Palette ──────────────────────────────────────────────────────────────────
AMBER     = "#FFB300"
AMBER_DIM = "#7A5500"
WHITE     = "#E8E8E8"
GREY      = "#555555"
GREEN     = "#00E676"
RED       = "#FF3D3D"
CYAN      = "#00BCD4"
W         = 56

POLL_INTERVAL = 10

console = Console(highlight=False)


def clear():
    os.system("cls" if sys.platform == "win32" else "clear")

def _sep():
    console.print(f"  [{AMBER_DIM}]{'─' * W}[/]")

def _header(subtitle: str = ""):
    console.print()
    t = Text()
    t.append("  H E R M I T", style=f"bold {AMBER}")
    if subtitle:
        sub = subtitle[:38] + "…" if len(subtitle) > 38 else subtitle
        t.append(f"  /  {sub}", style=AMBER_DIM)
    console.print(t)
    _sep()
    console.print()

def _footer(hints: list[str]):
    console.print()
    _sep()
    console.print("  " + "   ".join(f"[{GREY}]{h}[/]" for h in hints))
    console.print()

def _wrap(text: str, width: int = 52) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            if line:
                lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        lines.append(line)
    return lines or [""]


def screen_conversations(convos, platform_name):
    clear()
    _header(platform_name)
    for i, c in enumerate(convos):
        num     = Text(f"  {str(i + 1).rjust(2)}  ", style=AMBER_DIM)
        name    = Text(c.name[:22].ljust(22), style=f"bold {WHITE}")
        preview = Text(f"  {c.last_message[:26]}" if c.last_message else "", style=GREY)
        unread  = Text(f"  +{c.unread}", style=f"bold {GREEN}") if c.unread else Text("")
        console.print(num + name + preview + unread)
    _footer(["# open", "r refresh", "w whatsapp", "m messenger", "q quit"])
    return Prompt.ask(f"  [{AMBER}]>[/]").strip().lower()


def screen_chat(convo, messages, status_msg: str = "", new_count: int = 0, photo_index: dict = {}):
    clear()
    _header(convo.name)

    if not messages:
        console.print(f"  [{GREY}]no messages loaded[/]\n")
    else:
        prev_sender = None
        prev_date   = None
        photo_num   = 1  # incrementing number for each photo in this view

        for msg in messages[-30:]:
            ts    = msg.timestamp or ""
            label = "you" if msg.is_me else (msg.sender if msg.sender and msg.sender != "?" else "—")

            # Day separator
            date_part = ""
            for word in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday","Today","Yesterday"]:
                if word in ts:
                    date_part = ts
                    break
            if date_part and date_part != prev_date:
                console.print(f"\n  [{AMBER_DIM}]── {date_part} ──[/]\n")
                prev_date = date_part

            if msg.is_me:
                if prev_sender != "you":
                    console.print(Text("  you", style=f"bold {AMBER_DIM}"), justify="right")
                # Build one line: text + photo tags appended inline
                line = Text()
                if msg.text:
                    line.append(f"  {msg.text[:52]}", style=f"bold {GREEN}")
                for url in msg.attachments:
                    photo_index[photo_num] = url
                    line.append(f"  [p{photo_num}]", style=f"bold {CYAN}")
                    photo_num += 1
                if line:
                    console.print(line, justify="right")
                prev_sender = "you"
            else:
                if prev_sender != label:
                    console.print(Text(f"  {label[:40]}", style=f"bold {AMBER}"))
                # Build one line: text + photo tags appended inline
                line = Text()
                if msg.text:
                    line.append(f"  {msg.text[:52]}", style=WHITE)
                for url in msg.attachments:
                    photo_index[photo_num] = url
                    line.append(f"  [p{photo_num}]", style=f"bold {CYAN}")
                    photo_num += 1
                if line:
                    console.print(line)
                prev_sender = label

            console.print()

    if new_count:
        console.print(f"  [{GREEN}]↑ {new_count} new message{'s' if new_count > 1 else ''} — press r[/]\n")
    if status_msg:
        console.print(f"  [{RED}]{status_msg}[/]\n")

    hints = ["enter send", "r refresh", "p# view photo", "b back", "q quit"]
    _footer(hints)


async def _quit(platforms):
    for p in platforms.values():
        try:
            await p._close_browser()
        except Exception:
            pass
    os._exit(0)


class HermitApp:
    def __init__(self):
        self.store = SessionStore()
        self.platforms = {
            "messenger": MessengerPlatform(self.store),
            "whatsapp":  WhatsAppPlatform(self.store),
        }
        self.current_platform = "messenger"

    def run(self):
        asyncio.run(self._main())

    async def _main(self):
        sessions = self.store.list_sessions()
        if sessions and self.current_platform not in sessions:
            self.current_platform = sessions[0]

        platform = self.platforms[self.current_platform]
        convos   = []

        while True:
            if not convos:
                clear()
                _header(self.current_platform)
                with console.status(f"[{AMBER}]loading...[/]"):
                    convos = await platform.get_conversations()

            if not convos:
                clear()
                _header("not logged in")
                console.print(f"  [bold {RED}]no session found.[/]")
                console.print(f"  [dim]run:[/] [bold {AMBER}]hermit login fb[/]\n")
                input("  press enter to exit...")
                return

            choice = screen_conversations(convos, self.current_platform)

            if choice in ("q", "quit"):
                clear()
                console.print(f"\n  [{AMBER_DIM}]goodbye.[/]\n")
                await _quit(self.platforms)

            elif choice in ("r", "refresh"):
                convos = []

            elif choice in ("w", "wa", "whatsapp"):
                self.current_platform = "whatsapp"
                platform = self.platforms[self.current_platform]
                convos   = []

            elif choice in ("m", "fb", "messenger"):
                self.current_platform = "messenger"
                platform = self.platforms[self.current_platform]
                convos   = []

            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(convos):
                    result = await self._chat(platform, convos[idx])
                    if result == "quit":
                        await _quit(self.platforms)

    async def _chat(self, platform, convo):
        messages    = []
        status_msg  = ""
        new_count   = 0
        photo_index = {}  # num -> url, rebuilt each render

        cleanup_old_media()

        while True:
            if not messages:
                clear()
                _header(convo.name)
                with console.status(f"[{AMBER}]loading messages...[/]"):
                    messages = await platform.get_messages(convo.id)
                new_count = 0

            photo_index.clear()
            screen_chat(convo, messages, status_msg, new_count, photo_index)
            status_msg = ""
            new_count  = 0

            try:
                user_input = await _input_with_poll(platform, convo, messages, POLL_INTERVAL)
            except _NewMessages as e:
                new_count = e.count
                continue
            except (KeyboardInterrupt, EOFError):
                return "back"

            cmd = user_input.lower().strip()

            if cmd in ("q", "quit"):
                clear()
                console.print(f"\n  [{AMBER_DIM}]goodbye.[/]\n")
                return "quit"

            elif cmd in ("b", "back"):
                return "back"

            elif cmd in ("r", "refresh"):
                messages = []
                continue

            # p1, p2, p3 etc — view a photo
            elif cmd.startswith("p") and cmd[1:].isdigit():
                num = int(cmd[1:])
                url = photo_index.get(num)
                if url:
                    with console.status(f"[{CYAN}]downloading photo...[/]"):
                        path = await download_image(platform._page, url)
                    if path:
                        open_file(path)
                        status_msg = f"opened  [p{num}]"
                    else:
                        status_msg = f"failed to download [p{num}]"
                else:
                    status_msg = f"no [p{num}] in current view"

            elif user_input:
                with console.status(f"[{AMBER}]sending...[/]"):
                    ok = await platform.send_message(convo.id, user_input)
                if ok:
                    messages.append(Message(
                        id="local",
                        sender="you",
                        text=user_input,
                        timestamp=datetime.now().strftime("%H:%M"),
                        is_me=True
                    ))
                else:
                    status_msg = "failed to send — try again"


class _NewMessages(Exception):
    def __init__(self, count: int):
        self.count = count


async def _input_with_poll(platform, convo, current_messages, poll_interval):
    loop = asyncio.get_event_loop()
    input_task = loop.run_in_executor(None, lambda: input("  > ").strip())
    poll_task  = _poll_loop(platform, convo, current_messages, poll_interval)

    done, pending = await asyncio.wait(
        [asyncio.ensure_future(input_task), asyncio.ensure_future(poll_task)],
        return_when=asyncio.FIRST_COMPLETED
    )

    for t in pending:
        t.cancel()
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass

    return done.pop().result()


async def _poll_loop(platform, convo, current_messages, interval):
    await asyncio.sleep(interval)
    try:
        fresh = await platform.get_messages(convo.id)
        if len(fresh) > len(current_messages):
            raise _NewMessages(len(fresh) - len(current_messages))
    except _NewMessages:
        raise
    except Exception:
        pass
    await asyncio.sleep(999999)