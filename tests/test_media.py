import sys
from pathlib import Path
from unittest.mock import patch
from hermit.media import cleanup_old_media, open_file


def test_cleanup_old_media_keeps_recent(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.media.MEDIA_DIR", tmp_path)

    for i in range(5):
        (tmp_path / f"file{i}.jpg").write_bytes(b"data")

    cleanup_old_media(max_files=3)

    remaining = list(tmp_path.glob("*"))
    assert len(remaining) == 3


def test_cleanup_old_media_no_files(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.media.MEDIA_DIR", tmp_path)
    cleanup_old_media(max_files=10)  # should not raise


def test_cleanup_old_media_under_limit(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.media.MEDIA_DIR", tmp_path)

    for i in range(3):
        (tmp_path / f"file{i}.jpg").write_bytes(b"data")

    cleanup_old_media(max_files=10)

    remaining = list(tmp_path.glob("*"))
    assert len(remaining) == 3


def test_open_file_windows(tmp_path):
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"data")

    with patch("hermit.media.sys") as mock_sys, \
         patch("hermit.media.os") as mock_os:
        mock_sys.platform = "win32"
        mock_os.startfile = lambda x: None
        result = open_file(test_file)
        assert result is True


def test_open_file_linux(tmp_path):
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"data")

    with patch("hermit.media.sys") as mock_sys, \
         patch("hermit.media.os") as mock_os:
        mock_sys.platform = "linux"
        mock_os.system = lambda x: 0
        result = open_file(test_file)
        assert result is True
