import json
from hermit.store import SessionStore


def test_save_and_get_session(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.store.Path.home", lambda: tmp_path)
    store = SessionStore()

    store.save_session("fb", {"cookies": [{"name": "c_user", "value": "123"}]})
    result = store.get_session("fb")

    assert result is not None
    assert result["cookies"][0]["value"] == "123"


def test_get_missing_session(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.store.Path.home", lambda: tmp_path)
    store = SessionStore()

    assert store.get_session("nonexistent") is None


def test_clear_session(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.store.Path.home", lambda: tmp_path)
    store = SessionStore()

    store.save_session("fb", {"cookies": []})
    assert store.get_session("fb") is not None

    store.clear_session("fb")
    assert store.get_session("fb") is None


def test_clear_missing_session_no_error(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.store.Path.home", lambda: tmp_path)
    store = SessionStore()
    store.clear_session("nonexistent")  # should not raise


def test_list_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.store.Path.home", lambda: tmp_path)
    store = SessionStore()

    store.save_session("fb", {"cookies": []})
    store.save_session("wa", {"cookies": []})

    sessions = store.list_sessions()
    assert sorted(sessions) == ["fb", "wa"]


def test_list_sessions_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.store.Path.home", lambda: tmp_path)
    store = SessionStore()

    assert store.list_sessions() == []


def test_corrupt_session_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr("hermit.store.Path.home", lambda: tmp_path)
    store = SessionStore()

    path = store._path("fb")
    path.write_text("not valid json{{{")

    assert store.get_session("fb") is None
