import pytest
from hermit.platforms.base import Message, Conversation, Platform


def test_message_creation():
    msg = Message(
        id="1",
        sender="Alice",
        text="Hello",
        timestamp="2024-01-01 12:00",
        is_me=False,
    )
    assert msg.sender == "Alice"
    assert msg.text == "Hello"
    assert msg.is_me is False
    assert msg.attachments == []


def test_message_with_attachments():
    msg = Message(
        id="2",
        sender="Bob",
        text="Check this",
        timestamp="2024-01-01 12:01",
        is_me=True,
        attachments=["img1.jpg", "img2.jpg"],
    )
    assert len(msg.attachments) == 2


def test_conversation_creation():
    convo = Conversation(
        id="c1",
        name="Alice",
        platform="fb",
    )
    assert convo.name == "Alice"
    assert convo.last_message == ""
    assert convo.unread == 0
    assert convo.avatar is None


def test_conversation_with_unread():
    convo = Conversation(
        id="c2",
        name="Work Group",
        platform="fb",
        last_message="meeting at 3",
        unread=5,
    )
    assert convo.unread == 5
    assert convo.last_message == "meeting at 3"


def test_platform_is_abstract():
    with pytest.raises(TypeError):
        Platform(store=None)


def test_platform_subclass_must_implement_methods():
    class IncompletePlatform(Platform):
        pass

    with pytest.raises(TypeError):
        IncompletePlatform(store=None)


def test_platform_complete_subclass():
    class FakePlatform(Platform):
        name = "fake"

        async def login(self):
            return True

        async def get_conversations(self):
            return []

        async def get_messages(self, convo_id, limit=50):
            return []

        async def send_message(self, convo_id, text):
            return True

    p = FakePlatform(store=None)
    assert p.name == "fake"
    assert p._browser is None
