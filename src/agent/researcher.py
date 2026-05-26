"""
Research agent — finds trending topics and supporting data for LinkedIn posts.
"""
import os
import json
import random
from datetime import datetime
from typing import Optional

import anthropic

from src.agent.persona import TOPIC_CATEGORIES


def research_trending_topics(category: Optional[str] = None) -> dict:
    """Use Tavily to find current, relevant news and data for a topic."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    except (ImportError, KeyError):
        return _fallback_research(category)

    topic = category or random.choice(TOPIC_CATEGORIES)

    queries = {
        "Product-led growth tactics": "product-led growth SaaS 2025 case study results",
        "Data-as-a-Service business models": "data as a service DaaS market trends 2025",
        "AI features in B2B SaaS products": "AI features B2B SaaS product adoption 2025",
        "Pricing and packaging strategy": "SaaS pricing strategy 2025 trends research",
        "Customer discovery and research": "B2B customer discovery methods product management 2025",
        "Metrics and product analytics": "SaaS metrics benchmarks 2025 product analytics",
        "Platform and ecosystem strategy": "SaaS platform ecosystem strategy 2025",
        "Enterprise sales and product alignment": "enterprise SaaS product led sales 2025",
        "API-first product design": "API-first product design trends developer experience 2025",
        "Building vs buying data infrastructure": "build vs buy data infrastructure SaaS 2025",
        "Product team structure and culture": "product team structure best practices 2025",
        "Go-to-market strategy for SaaS": "SaaS go to market strategy 2025 trends",
        "Developer experience (DX) as a product": "developer experience product SaaS 2025",
        "Data monetization and governance": "data monetization strategy enterprise 2025",
        "Feature prioritization frameworks": "feature prioritization frameworks product management 2025",
    }

    query = queries.get(topic, f"{topic} 2025 trends insights")

    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_answer=True,
        )
        return {
            "topic": topic,
            "query": query,
            "summary": response.get("answer", ""),
            "sources": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:300],
                }
                for r in response.get("results", [])[:3]
            ],
            "researched_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return _fallback_research(topic, error=str(e))


def _fallback_research(category: Optional[str] = None, error: str = "") -> dict:
    """Fallback when Tavily is unavailable — Claude generates context from training data."""
    topic = category or random.choice(TOPIC_CATEGORIES)
    return {
        "topic": topic,
        "query": f"{topic} recent trends",
        "summary": "",
        "sources": [],
        "researched_at": datetime.now().isoformat(),
        "fallback": True,
        "error": error,
    }


def build_research_brief(research: dict, client: anthropic.Anthropic) -> str:
    """Use Claude to synthesize research into a post brief."""
    sources_text = ""
    if research.get("sources"):
        sources_text = "\n\nRecent sources:\n" + "\n".join(
            f"- {s['title']}: {s['snippet']}"
            for s in research["sources"]
        )

    summary_text = ""
    if research.get("summary"):
        summary_text = f"\n\nResearch summary: {research['summary']}"

    prompt = f"""Topic area: {research['topic']}
{summary_text}{sources_text}

Based on this topic and any current context above, generate a research brief for a LinkedIn post.
Include:
1. A specific angle or hook (surprising stat, contrarian take, or timely observation)
2. 2-3 concrete data points or examples a PM would know from experience or industry knowledge
3. The core insight or lesson
4. A suggested post format: story / hot_take / framework / trend_analysis / data_insight / myth_busting

Keep the brief to 150-200 words. Be specific — no vague generalities."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=400,
        system="You are a research assistant helping a Senior PM create LinkedIn content. Be specific, data-driven, and current.",
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
