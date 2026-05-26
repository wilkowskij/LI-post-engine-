"""
Researcher tests — fallback research, brief building, query map coverage.
"""
import pytest
from unittest.mock import MagicMock

from src.agent.researcher import research_trending_topics, build_research_brief, _fallback_research
from src.agent.persona import TOPIC_CATEGORIES, POST_FORMATS


def _mock_client(text: str) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    client.messages.create.return_value = msg
    return client


# ── fallback research ────────────────────────────────────────────────────────

def test_fallback_returns_dict():
    result = _fallback_research("Product-led growth tactics")
    assert isinstance(result, dict)


def test_fallback_required_keys():
    result = _fallback_research("Product-led growth tactics")
    for key in ("topic", "query", "summary", "sources", "researched_at", "fallback"):
        assert key in result, f"Missing key: {key!r}"


def test_fallback_topic_preserved():
    result = _fallback_research("Go-to-market strategy for SaaS")
    assert result["topic"] == "Go-to-market strategy for SaaS"


def test_fallback_random_topic_when_none():
    result = _fallback_research()
    assert result["topic"] in TOPIC_CATEGORIES


def test_fallback_sources_empty():
    result = _fallback_research("Pricing and packaging strategy")
    assert result["sources"] == []


# ── query map coverage ───────────────────────────────────────────────────────

def test_all_topics_have_query_entries():
    """Every topic in TOPIC_CATEGORIES must map to a Tavily search query."""
    # We test this by checking the queries dict inside research_trending_topics
    # by importing it from the module source
    import src.agent.researcher as researcher_mod
    import inspect, ast

    src_text = inspect.getsource(researcher_mod.research_trending_topics)
    # Parse out the queries dict keys via a quick string check
    for topic in TOPIC_CATEGORIES:
        assert topic in src_text, (
            f"Topic {topic!r} has no Tavily query in researcher.py"
        )


# ── build_research_brief ─────────────────────────────────────────────────────

def test_build_brief_returns_string():
    client = _mock_client("This is the research brief.")
    result = build_research_brief(_fallback_research("PLG"), client)
    assert isinstance(result, str)


def test_build_brief_calls_api():
    client = _mock_client("Brief text.")
    build_research_brief(_fallback_research("PLG"), client)
    assert client.messages.create.call_count == 1


def test_build_brief_prompt_contains_valid_formats():
    client = _mock_client("Brief text.")
    build_research_brief(_fallback_research("PLG"), client)
    call_kwargs = client.messages.create.call_args
    prompt = call_kwargs[1]["messages"][0]["content"]
    # At least one of the real format names should appear in the prompt
    assert any(f in prompt for f in POST_FORMATS), (
        f"No known format names found in brief prompt.\nPrompt: {prompt}"
    )


def test_build_brief_prompt_no_old_format_names():
    client = _mock_client("Brief text.")
    build_research_brief(_fallback_research("PLG"), client)
    call_kwargs = client.messages.create.call_args
    prompt = call_kwargs[1]["messages"][0]["content"]
    for old in ("trend_analysis", "story"):
        assert old not in prompt, f"Old format name {old!r} still in brief prompt"


# ── research_trending_topics (Tavily absent fallback) ────────────────────────

def test_research_uses_fallback_without_tavily(monkeypatch):
    """When Tavily is not installed, should gracefully fall back."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "tavily":
            raise ImportError("tavily not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    result = research_trending_topics("Product-led growth tactics")
    assert result["fallback"] is True
    assert result["topic"] == "Product-led growth tactics"
