"""
hermit — distraction-free unified messaging CLI

Usage:
  hermit                 launch the app
  hermit login fb        log into Facebook Messenger
  hermit login wa        log into WhatsApp
  hermit logout          clear all saved sessions
  hermit logout fb       clear Messenger session only
  hermit status          show which platforms are logged in
  hermit version         show version
"""
import sys
import asyncio
from hermit.store import SessionStore


def run():
    # Fix Windows encoding + emoji support
    if sys.platform == "win32":
        import os
        os.system("chcp 65001 >nul 2>&1")  # UTF-8 code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    # Force Python UTF-8 mode
    import os
    os.environ.setdefault("PYTHONUTF8", "1")

    args = sys.argv[1:]

    if not args:
        from hermit.app import HermitApp
        HermitApp().run()
        return

    cmd = args[0].lower()
    store = SessionStore()

    if cmd == "login":
        target = args[1].lower() if len(args) > 1 else "all"
        asyncio.run(_login(store, target))

    elif cmd == "logout":
        target = args[1].lower() if len(args) > 1 else "all"
        _logout(store, target)

    elif cmd == "status":
        _status(store)

    elif cmd in ("version", "--version", "-v"):
        from hermit import __version__
        print(f"hermit v{__version__}")

    elif cmd in ("help", "--help", "-h"):
        print(__doc__)

    else:
        print(f"  Unknown command: {cmd}")
        print("  Run 'hermit help' for usage.")


async def _login(store, target):
    from hermit.platforms.messenger import MessengerPlatform
    from hermit.platforms.whatsapp import WhatsAppPlatform

    mapping = {
        "fb": MessengerPlatform,
        "messenger": MessengerPlatform,
        "wa": WhatsAppPlatform,
        "whatsapp": WhatsAppPlatform,
    }

    if target == "all":
        # Ask which platform instead of blindly logging into both
        print("\n  Which platform?")
        print("  [1] Facebook Messenger  (fb)")
        print("  [2] WhatsApp            (wa)")
        print("  [3] Both\n")
        pick = input("  > ").strip().lower()
        if pick in ("1", "fb", "messenger"):
            targets = [MessengerPlatform(store)]
        elif pick in ("2", "wa", "whatsapp"):
            targets = [WhatsAppPlatform(store)]
        elif pick in ("3", "both", "all"):
            targets = [MessengerPlatform(store), WhatsAppPlatform(store)]
        else:
            print("  Cancelled.")
            return
    elif target in mapping:
        targets = [mapping[target](store)]
    else:
        print(f"  Unknown platform: '{target}'")
        print("  Options: fb, wa")
        return

    for platform in targets:
        print(f"\n  Logging into {platform.name}...")
        await platform.login()


def _logout(store, target):
    if target == "all":
        sessions = store.list_sessions()
        if not sessions:
            print("  No sessions to clear.")
            return
        for s in sessions:
            store.clear_session(s)
            print(f"  Cleared: {s}")
    else:
        name = {"fb": "messenger", "wa": "whatsapp"}.get(target, target)
        store.clear_session(name)
        print(f"  Cleared: {name}")


def _status(store):
    sessions = store.list_sessions()
    print()
    if sessions:
        print("  Logged in:")
        for s in sessions:
            print(f"    [+] {s}")
    else:
        print("  Not logged into any platform.")
        print("  Run: hermit login fb")
    print()