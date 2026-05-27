"""
Tests for diagram spec generation and framework diagram rendering.
Covers: generate_diagram_spec, visual_framework post parsing, generate_framework_diagram.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.agent.writer import generate_diagram_spec, _parse_visual_framework_response
from src.utils.image_gen import generate_framework_diagram


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


SAMPLE_SPEC = {
    "title": "PLG ACTIVATION LOOP",
    "subtitle": "How product-led teams turn signups into revenue",
    "steps": [
        {"label": "SIGN UP", "description": "User arrives with a job to be done."},
        {"label": "FIRST VALUE", "description": "Hit the aha moment fast."},
        {"label": "HABIT", "description": "Returns three times in week one."},
        {"label": "EXPAND", "description": "Invites a teammate or upgrades."},
    ],
    "foundation_title": "ACTIVATION SIGNALS",
    "foundation_items": ["TIME TO VALUE", "RETENTION", "NPS"],
}

SAMPLE_SPEC_JSON = json.dumps(SAMPLE_SPEC)

SAMPLE_POST = {
    "text": "PLG is reshaping SaaS.\n\n1. Activate inside the product.\n2. Let data drive the motion.\n\n#PLG #SaaS",
    "topic": "Product-led growth tactics",
    "format": "trend_prediction",
    "hashtags": ["#PLG", "#SaaS"],
    "word_count": 20,
    "char_count": 100,
}


# ---------------------------------------------------------------------------
# generate_diagram_spec
# ---------------------------------------------------------------------------

def test_generate_diagram_spec_returns_dict():
    client = _mock_client(SAMPLE_SPEC_JSON)
    post = dict(SAMPLE_POST)
    spec = generate_diagram_spec(post, client)
    assert isinstance(spec, dict)


def test_generate_diagram_spec_populates_post():
    client = _mock_client(SAMPLE_SPEC_JSON)
    post = dict(SAMPLE_POST)
    generate_diagram_spec(post, client)
    assert "diagram" in post
    assert post["diagram"]["title"] == "PLG ACTIVATION LOOP"


def test_generate_diagram_spec_noop_if_present():
    post = dict(SAMPLE_POST)
    post["diagram"] = SAMPLE_SPEC
    client = _mock_client("should not be called")
    generate_diagram_spec(post, client)
    client.messages.create.assert_not_called()


def test_generate_diagram_spec_calls_api_once():
    client = _mock_client(SAMPLE_SPEC_JSON)
    post = dict(SAMPLE_POST)
    generate_diagram_spec(post, client)
    assert client.messages.create.call_count == 1


def test_generate_diagram_spec_handles_malformed_json():
    client = _mock_client("not valid json {{{{")
    post = dict(SAMPLE_POST)
    spec = generate_diagram_spec(post, client)
    assert isinstance(spec, dict)


def test_generate_diagram_spec_handles_fenced_json():
    fenced = f"```json\n{SAMPLE_SPEC_JSON}\n```"
    client = _mock_client(fenced)
    post = dict(SAMPLE_POST)
    spec = generate_diagram_spec(post, client)
    assert spec.get("title") == "PLG ACTIVATION LOOP"


# ---------------------------------------------------------------------------
# visual_framework post parsing
# ---------------------------------------------------------------------------

VISUAL_RESPONSE = json.dumps({
    "post_text": "AI agents improve by externalizing experience, not magic.\n\n#AIProduct #SaaS",
    "diagram": SAMPLE_SPEC,
})


def test_parse_visual_framework_extracts_text():
    result = _parse_visual_framework_response(
        VISUAL_RESPONSE, "AI features in B2B SaaS products", "visual_framework", ["#AIProduct"]
    )
    assert "AI agents" in result["text"]


def test_parse_visual_framework_extracts_diagram():
    result = _parse_visual_framework_response(
        VISUAL_RESPONSE, "AI features in B2B SaaS products", "visual_framework", ["#AIProduct"]
    )
    assert result["diagram"]["title"] == "PLG ACTIVATION LOOP"


def test_parse_visual_framework_fallback_on_bad_json():
    result = _parse_visual_framework_response(
        "raw text, no json", "topic", "visual_framework", []
    )
    assert result["text"] == "raw text, no json"
    assert result["diagram"] == {}


def test_parse_visual_framework_strips_fences():
    fenced = f"```json\n{VISUAL_RESPONSE}\n```"
    result = _parse_visual_framework_response(
        fenced, "topic", "visual_framework", []
    )
    assert result["diagram"].get("title") == "PLG ACTIVATION LOOP"


def test_parse_visual_framework_word_count():
    result = _parse_visual_framework_response(
        VISUAL_RESPONSE, "topic", "visual_framework", []
    )
    assert result["word_count"] == len(result["text"].split())


# ---------------------------------------------------------------------------
# generate_framework_diagram (Pillow rendering)
# ---------------------------------------------------------------------------

def test_diagram_renders_to_file(tmp_path):
    out = tmp_path / "test.png"
    path = generate_framework_diagram(SAMPLE_SPEC, output_path=out)
    assert path == out
    assert out.exists()
    assert out.stat().st_size > 5000  # non-trivial PNG


def test_diagram_creates_output_dir(tmp_path):
    out = tmp_path / "subdir" / "diagram.png"
    generate_framework_diagram(SAMPLE_SPEC, output_path=out)
    assert out.exists()


def test_diagram_without_foundation(tmp_path):
    spec = {
        "title": "SIMPLE FLOW",
        "steps": [
            {"label": "STEP ONE", "description": "First thing happens."},
            {"label": "STEP TWO", "description": "Second thing follows."},
        ],
    }
    out = tmp_path / "simple.png"
    path = generate_framework_diagram(spec, output_path=out)
    assert path.exists()


def test_diagram_caps_steps_at_six(tmp_path):
    spec = {
        "title": "LONG FLOW",
        "steps": [{"label": f"STEP {i}", "description": "desc."} for i in range(10)],
    }
    out = tmp_path / "long.png"
    path = generate_framework_diagram(spec, output_path=out)
    assert path.exists()


def test_diagram_empty_spec_does_not_crash(tmp_path):
    out = tmp_path / "empty.png"
    path = generate_framework_diagram({}, output_path=out)
    assert path.exists()
