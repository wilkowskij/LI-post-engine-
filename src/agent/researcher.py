"""
Research agent — finds trending topics and supporting data for LinkedIn posts.

Primary path: marketing_agent.run_research_agent (agentic loop with claude-opus-4-7)
Fallback: Tavily direct search or Claude training-data synthesis
"""
import os
import random
from datetime import datetime
from typing import Optional

import anthropic

from src.agent.persona import TOPIC_CATEGORIES


def research_trending_topics(category: Optional[str] = None) -> dict:
    """
    Research a topic using the agentic marketing agent.
    Falls back to direct Tavily search or training-data synthesis if needed.
    """
    topic = category or random.choice(TOPIC_CATEGORIES)

    try:
        from src.agent.marketing_agent import run_research_agent
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=5)
        return run_research_agent(topic, client)
    except Exception:
        pass

    # Legacy fallback: direct Tavily search
    return _tavily_research(topic)


def _tavily_research(topic: str) -> dict:
    """Direct Tavily search, bypassing the agentic loop."""
    try:
        from tavily import TavilyClient
        key = os.environ.get("TAVILY_API_KEY", "")
        if not key or key == "your_tavily_api_key":
            raise ValueError("Tavily key not set")
        client = TavilyClient(api_key=key)
    except Exception:
        return _fallback_research(topic)

    queries = {
        "Product-led growth tactics": "product-led growth SaaS 2025 case study results",
        "Go-to-market strategy for SaaS": "SaaS go to market strategy 2025 trends",
        "Pricing and packaging strategy": "SaaS pricing strategy 2025 trends research",
        "Activation and time-to-value": "SaaS activation time to value product-led growth 2025",
        "Product-led sales (PLS) motions": "product-led sales PLS SaaS motion 2025",
        "Data-as-a-Service business models": "data as a service DaaS market trends 2025",
        "AI features in B2B SaaS products": "AI features B2B SaaS product adoption 2025",
        "Data monetization and governance": "data monetization strategy enterprise 2025",
        "Building with LLMs in SaaS products": "LLM integration B2B SaaS product feature 2025",
        "API-first product design": "API-first product design trends developer experience 2025",
        "Understanding the B2B buyer as a PM": "B2B buyer behavior SaaS product management 2025",
        "Enterprise sales and product alignment": "enterprise SaaS product led sales 2025",
        "Metrics that matter to buyers and boards": "SaaS metrics KPIs executives buyers boards 2025",
        "Feature prioritization frameworks": "feature prioritization frameworks product management 2025",
        "Customer discovery and research": "B2B customer discovery methods product management 2025",
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
    """
    Convert a research dict into a text brief for the post writer.

    If the research came from the agentic marketing agent it already has
    structured fields (hook, data_points, core_insight). Otherwise synthesize
    via a quick Claude call.
    """
    # Agentic brief: convert structured fields to text directly
    if research.get("agentic"):
        from src.agent.marketing_agent import brief_to_text
        return brief_to_text(research)

    # Legacy path: synthesize from raw Tavily output
    sources_text = ""
    if research.get("sources"):
        sources_text = "\n\nRecent sources:\n" + "\n".join(
            f"- {s['title']}: {s['snippet']}"
            for s in research["sources"]
        )

    summary_text = ""
    if research.get("summary"):
        summary_text = f"\n\nResearch summary: {research['summary']}"

    prompt = (
        f"Topic area: {research['topic']}"
        f"{summary_text}{sources_text}\n\n"
        "Based on this topic and any current context above, generate a research brief for a LinkedIn post.\n"
        "Include:\n"
        "1. A specific angle or hook (surprising stat, contrarian take, or timely observation)\n"
        "2. 2-3 concrete data points or examples a PM would know from experience or industry knowledge\n"
        "3. The core insight or lesson\n"
        "4. A suggested post format: trend_prediction / framework / hot_take / breakdown / myth_busting / data_insight\n\n"
        "Keep the brief to 150-200 words. Be specific — no vague generalities."
    )

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=400,
        system="You are a research assistant helping a Senior PM create LinkedIn content. Be specific, data-driven, and current.",
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
