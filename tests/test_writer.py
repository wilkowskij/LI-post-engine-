"""
Writer tests — generate_post and refine_post with a mocked Anthropic client.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.agent.writer import generate_post, refine_post
from src.agent.persona import POST_FORMATS, TOPIC_CATEGORIES


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


TOPIC = "Product-led growth tactics"
BRIEF = "PLG adoption increased 40% YoY. Companies activating users inside the product convert 3x faster."
FAKE_POST = "PLG is reshaping how SaaS companies grow.\n\n1. Activation beats demos.\n2. Data drives the motion.\n\nWhere is PLG heading in 2027?\n\n#PLG #SaaS #ProductStrategy"


def test_generate_post_returns_dict():
    client = _mock_client(FAKE_POST)
    result = generate_post(BRIEF, TOPIC, client=client)
    assert isinstance(result, dict)


def test_generate_post_required_keys():
    client = _mock_client(FAKE_POST)
    result = generate_post(BRIEF, TOPIC, client=client)
    for key in ("text", "topic", "format", "hashtags", "word_count", "char_count"):
        assert key in result, f"Missing key: {key!r}"


def test_generate_post_text_matches():
    client = _mock_client(FAKE_POST)
    result = generate_post(BRIEF, TOPIC, client=client)
    assert result["text"] == FAKE_POST


def test_generate_post_topic_preserved():
    client = _mock_client(FAKE_POST)
    result = generate_post(BRIEF, TOPIC, client=client)
    assert result["topic"] == TOPIC


def test_generate_post_format_valid():
    client = _mock_client(FAKE_POST)
    result = generate_post(BRIEF, TOPIC, client=client)
    assert result["format"] in POST_FORMATS


def test_generate_post_explicit_format():
    client = _mock_client(FAKE_POST)
    result = generate_post(BRIEF, TOPIC, post_format="hot_take", client=client)
    assert result["format"] == "hot_take"


def test_generate_post_word_count():
    client = _mock_client(FAKE_POST)
    result = generate_post(BRIEF, TOPIC, client=client)
    assert result["word_count"] == len(FAKE_POST.split())


def test_generate_post_char_count():
    client = _mock_client(FAKE_POST)
    result = generate_post(BRIEF, TOPIC, client=client)
    assert result["char_count"] == len(FAKE_POST)


def test_generate_post_calls_api_once():
    client = _mock_client(FAKE_POST)
    generate_post(BRIEF, TOPIC, client=client)
    assert client.messages.create.call_count == 1


def test_generate_post_custom_angle_in_prompt():
    client = _mock_client(FAKE_POST)
    generate_post(BRIEF, TOPIC, custom_angle="Focus on activation loops", client=client)
    call_kwargs = client.messages.create.call_args
    user_msg = call_kwargs[1]["messages"][0]["content"]
    assert "activation loops" in user_msg.lower()


def test_refine_post_returns_string():
    client = _mock_client("Refined post text here.")
    result = refine_post(FAKE_POST, "Make it punchier", client=client)
    assert isinstance(result, str)
    assert result == "Refined post text here."


def test_refine_post_includes_feedback_in_prompt():
    client = _mock_client("Revised.")
    refine_post(FAKE_POST, "Add a stronger opening hook", client=client)
    call_kwargs = client.messages.create.call_args
    user_msg = call_kwargs[1]["messages"][0]["content"]
    assert "stronger opening hook" in user_msg


def test_generate_post_hashtags_are_list():
    client = _mock_client(FAKE_POST)
    result = generate_post(BRIEF, TOPIC, client=client)
    assert isinstance(result["hashtags"], list)
    assert len(result["hashtags"]) > 0
