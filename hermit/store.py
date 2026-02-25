"""
hermit/store.py — Local session storage (~/.hermit/)
"""
from __future__ import annotations
import json
import os
from pathlib import Path


class SessionStore:
    def __init__(self):
        self.dir = Path.home() / ".hermit"
        self.dir.mkdir(exist_ok=True)
        try:
            os.chmod(self.dir, 0o700)
        except Exception:
            pass  # Windows doesn't support unix perms

    def _path(self, platform: str) -> Path:
        return self.dir / f"{platform}_session.json"

    def save_session(self, platform: str, state: dict) -> None:
        path = self._path(platform)
        with open(path, "w") as f:
            json.dump(state, f)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass

    def get_session(self, platform: str) -> dict | None:
        path = self._path(platform)
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def clear_session(self, platform: str) -> None:
        path = self._path(platform)
        if path.exists():
            path.unlink()

    def list_sessions(self) -> list[str]:
        return [p.stem.replace("_session", "") for p in self.dir.glob("*_session.json")]