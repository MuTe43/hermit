"""
hermit/media.py — Download and open media attachments
"""
from __future__ import annotations
import os
import sys
import asyncio
import tempfile
import hashlib
from pathlib import Path

MEDIA_DIR = Path(tempfile.gettempdir()) / "hermit_media"
MEDIA_DIR.mkdir(exist_ok=True)


async def download_image(page, url: str) -> Path | None:
    """
    Download image via Playwright navigation — inherits all browser cookies/headers.
    Much more reliable than fetch() for CDN URLs.
    """
    fname = hashlib.md5(url.encode()).hexdigest()[:16] + ".jpg"
    dest  = MEDIA_DIR / fname
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    try:
        # Open a new tab, navigate to the image URL directly
        # This uses the full browser session including all auth cookies
        context = page.context
        new_page = await context.new_page()
        try:
            response = await new_page.goto(url, wait_until="load", timeout=15000)
            if response and response.ok:
                body = await response.body()
                if body:
                    with open(dest, "wb") as f:
                        f.write(body)
                    return dest
        finally:
            await new_page.close()
    except Exception as e:
        pass

    return None


def open_file(path: Path) -> bool:
    """Open file with OS default application."""
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
        return True
    except Exception:
        return False


def cleanup_old_media(max_files: int = 50):
    """Prune old cached media files."""
    files = sorted(MEDIA_DIR.glob("*"), key=lambda f: f.stat().st_mtime)
    for f in files[:-max_files]:
        try:
            f.unlink()
        except Exception:
            pass