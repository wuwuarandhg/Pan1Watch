import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


openai_stub = types.ModuleType("openai")


class _AsyncOpenAI:  # pragma: no cover - test stub only
    def __init__(self, *args, **kwargs):
        pass


openai_stub.AsyncOpenAI = _AsyncOpenAI
sys.modules.setdefault("openai", openai_stub)

from src.core.ai_client import _extract_chat_content


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, choices):
        self.choices = choices


def test_extract_chat_content_accepts_plain_text():
    response = _Response([_Choice("hello")])
    assert _extract_chat_content(response) == "hello"


def test_extract_chat_content_accepts_content_parts():
    response = _Response([
        _Choice(
            [
                {"type": "text", "text": "line1"},
                {"type": "image_url", "image_url": {"url": "x"}},
                {"type": "text", "text": "line2"},
            ]
        )
    ])
    assert _extract_chat_content(response) == "line1\nline2"


def test_extract_chat_content_rejects_empty_choices():
    response = _Response(None)
    with pytest.raises(RuntimeError, match="choices"):
        _extract_chat_content(response)
