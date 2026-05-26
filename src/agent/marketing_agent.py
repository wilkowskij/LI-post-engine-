"""
Marketing research agent — agentic loop using Claude claude-opus-4-7 with adaptive thinking.

Runs a multi-step tool-use loop to research Product Management, SaaS, and DaaS news,
then returns a structured research brief ready for the post writer.
"""
import json
import os
import re
from datetime import datetime
from typing import Optional

import anthropic

from src.agent.persona import TOPIC_CATEGORIES


# ---------------------------------------------------------------------------
# System prompt (cached via prompt caching)
# ---------------------------------------------------------------------------

_RESEARCH_SYSTEM = """You are a senior content researcher specializing in Product Management, \
SaaS, and Data-as-a-Service. Your job is to find real, current signals that a Senior PM with \
10+ years of experience can turn into a compelling LinkedIn thought-leadership post.

Research principles:
- Prioritize specific data (percentages, dollar figures, growth rates) over vague trends
- Look for surprising findings — the stat that challenges conventional wisdom is gold
- Find recent (2025-2026) market signals, not evergreen advice
- Two well-sourced findings beat five shallow ones

Your workflow:
1. Run 1-2 targeted searches on the given topic
2. If a result looks substantive, fetch the article for more detail
3. Once you have 2-3 solid findings, call `finalize_research` with your brief

Stop researching when you have enough for one sharp, specific post angle. \
Do not over-research. Quality over coverage."""

# Tool definitions
_TOOLS = [
    {
        "name": "search_news",
        "description": (
            "Search for recent news, research reports, and data about a PM/SaaS/DaaS topic. "
            "Returns titles, URLs, and snippets from top results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Specific search query. Include year (2025 or 2026) and the exact angle "
                        "you need — e.g. 'product-led growth conversion rates 2025 data'"
                    ),
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_article",
        "description": "Fetch the full text of an article URL to read deeper details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL of the article to fetch",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "finalize_research",
        "description": (
            "Submit the final research brief when you have enough to write a sharp LinkedIn post. "
            "Call this once — it ends the research loop."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hook": {
                    "type": "string",
                    "description": (
                        "The specific, compelling opening angle: a surprising stat, a market shift, "
                        "or a contrarian observation grounded in something you found"
                    ),
                },
                "data_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "2-3 concrete data points, examples, or market signals from research",
                    "minItems": 1,
                    "maxItems": 4,
                },
                "core_insight": {
                    "type": "string",
                    "description": "The one-sentence takeaway a PM or exec should walk away with",
                },
                "suggested_format": {
                    "type": "string",
                    "enum": [
                        "framework",
                        "trend_prediction",
                        "hot_take",
                        "breakdown",
                        "myth_busting",
                        "data_insight",
                    ],
                    "description": "Post format that best fits this research angle",
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "snippet": {"type": "string"},
                        },
                    },
                    "description": "Sources used (title + url + brief snippet)",
                },
            },
            "required": ["hook", "data_points", "core_insight", "suggested_format"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _get_tavily():
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key or key == "your_tavily_api_key":
        return None
    try:
        from tavily import TavilyClient
        return TavilyClient(api_key=key)
    except (ImportError, Exception):
        return None


def _search_news(query: str, tavily=None) -> dict:
    if tavily:
        try:
            resp = tavily.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                include_answer=True,
            )
            return {
                "summary": resp.get("answer", ""),
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", "")[:400],
                    }
                    for r in resp.get("results", [])[:5]
                ],
            }
        except Exception as e:
            return {"error": str(e), "results": []}

    return {
        "note": "Web search unavailable (TAVILY_API_KEY not configured). Rely on training data.",
        "results": [],
    }


def _fetch_article(url: str) -> dict:
    try:
        import requests

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; LI-Post-Engine/1.0; +https://github.com)"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        # Strip HTML tags
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()

        return {"content": text[:3000], "url": url}

    except Exception as e:
        return {"error": str(e), "url": url}


def _execute_tool(name: str, inputs: dict, tavily=None) -> dict:
    if name == "search_news":
        return _search_news(inputs["query"], tavily)
    if name == "fetch_article":
        return _fetch_article(inputs["url"])
    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

def run_research_agent(
    topic: str,
    client: Optional[anthropic.Anthropic] = None,
) -> dict:
    """
    Run the agentic research loop for a given topic.
    Returns a structured research brief dict.
    """
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    tavily = _get_tavily()

    messages = [
        {
            "role": "user",
            "content": (
                f"Research this topic for a LinkedIn post targeting Senior PMs and executives:\n\n"
                f"**{topic}**\n\n"
                f"Today: {datetime.now().strftime('%B %d, %Y')}\n\n"
                f"Find recent (2025–2026) news, stats, or market signals. "
                f"When you have 2–3 solid findings, call `finalize_research`."
            ),
        }
    ]

    max_iterations = 8

    for _ in range(max_iterations):
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": _RESEARCH_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=_TOOLS,
            thinking={"type": "adaptive"},
            messages=messages,
        )

        # Append full content (including thinking blocks) to preserve loop state
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            finalized_brief = None

            for block in response.content:
                if block.type != "tool_use":
                    continue

                if block.name == "finalize_research":
                    finalized_brief = block.input
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"status": "accepted"}),
                        }
                    )
                else:
                    result = _execute_tool(block.name, block.input, tavily)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        }
                    )

            messages.append({"role": "user", "content": tool_results})

            if finalized_brief:
                return _enrich_brief(finalized_brief, topic)

    return _fallback_brief(topic)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enrich_brief(brief: dict, topic: str) -> dict:
    return {
        "topic": topic,
        "hook": brief.get("hook", ""),
        "data_points": brief.get("data_points", []),
        "core_insight": brief.get("core_insight", ""),
        "suggested_format": brief.get("suggested_format", "trend_prediction"),
        "sources": brief.get("sources", []),
        "researched_at": datetime.now().isoformat(),
        "agentic": True,
    }


def _fallback_brief(topic: str) -> dict:
    return {
        "topic": topic,
        "hook": "",
        "data_points": [],
        "core_insight": "",
        "suggested_format": "trend_prediction",
        "sources": [],
        "researched_at": datetime.now().isoformat(),
        "agentic": True,
        "fallback": True,
    }


# ---------------------------------------------------------------------------
# Public helper: format brief as text for the writer
# ---------------------------------------------------------------------------

def brief_to_text(brief: dict) -> str:
    """Convert an agent research brief to the text format expected by the writer."""
    parts = []

    if brief.get("hook"):
        parts.append(f"Hook / angle: {brief['hook']}")

    if brief.get("data_points"):
        parts.append("Data points:")
        for dp in brief["data_points"]:
            parts.append(f"  - {dp}")

    if brief.get("core_insight"):
        parts.append(f"Core insight: {brief['core_insight']}")

    if brief.get("suggested_format"):
        parts.append(f"Suggested format: {brief['suggested_format']}")

    if brief.get("sources"):
        parts.append("Sources:")
        for s in brief["sources"]:
            title = s.get("title", "")
            snippet = s.get("snippet", "")
            if title or snippet:
                parts.append(f"  - {title}: {snippet[:150]}")

    return "\n".join(parts) if parts else f"Topic: {brief.get('topic', '')}"
