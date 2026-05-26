"""
LinkedIn post writer — generates posts in Senior PM voice using Claude.
"""
import json
import random
from typing import Optional

import anthropic

from src.agent.persona import PERSONA_SYSTEM_PROMPT, POST_FORMATS, HASHTAG_MAP, TOPIC_CATEGORIES


def generate_post(
    research_brief: str,
    topic: str,
    post_format: Optional[str] = None,
    custom_angle: Optional[str] = None,
    client: Optional[anthropic.Anthropic] = None,
) -> dict:
    """Generate a LinkedIn post from a research brief."""
    if client is None:
        import os
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Prefer forward-looking formats unless caller specifies one
    preferred = ["trend_prediction", "framework", "hot_take", "breakdown", "myth_busting", "data_insight"]
    chosen_format = post_format or random.choice(preferred)
    fmt = POST_FORMATS[chosen_format]
    hashtags = HASHTAG_MAP.get(topic, ["#ProductManagement", "#SaaS", "#GTM"])

    angle_note = f"\n\nSpecific angle to emphasize: {custom_angle}" if custom_angle else ""

    user_prompt = f"""Write a LinkedIn post for a Senior Product Manager in the SaaS/DaaS space.

RESEARCH BRIEF:
{research_brief}
{angle_note}

POST FORMAT: {chosen_format}
Format description: {fmt['description']}
Structure to follow: {fmt['structure']}
Target length: {fmt['length']}

HASHTAGS to use (pick 3-5 most relevant): {', '.join(hashtags)}

RULES:
- Open with a PREDICTION, PATTERN, or FRAMEWORK — not a personal story opener
- Write for both a senior PM AND an executive reading on mobile
- Include one forward-looking take (where is this heading in 12-24 months?)
- Use structure: numbered lists, named frameworks, clear before/after when possible
- Ground every claim in a concrete signal, pattern, or market observation
- Never name specific companies, clients, or employers
- Never use: "delve into", "it's worth noting", "in today's fast-paced landscape",
  "game-changer", "revolutionize", "synergy", or "leverage" as a verb
- Short paragraphs, line breaks between each for mobile readability
- Do NOT use em-dashes (—) more than once
- Do NOT start with "I"

Return ONLY the post text, ready to copy-paste to LinkedIn. No meta-commentary."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=600,
        system=PERSONA_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    post_text = message.content[0].text.strip()

    return {
        "text": post_text,
        "topic": topic,
        "format": chosen_format,
        "hashtags": hashtags,
        "word_count": len(post_text.split()),
        "char_count": len(post_text),
    }


def generate_post_variants(
    research_brief: str,
    topic: str,
    count: int = 3,
    client: Optional[anthropic.Anthropic] = None,
) -> list[dict]:
    """Generate multiple post variants to choose from."""
    if client is None:
        import os
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    formats = random.sample(list(POST_FORMATS.keys()), min(count, len(POST_FORMATS)))
    variants = []
    for fmt in formats:
        post = generate_post(research_brief, topic, post_format=fmt, client=client)
        variants.append(post)
    return variants


def refine_post(post_text: str, feedback: str, client: Optional[anthropic.Anthropic] = None) -> str:
    """Refine an existing post based on feedback."""
    if client is None:
        import os
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=600,
        system=PERSONA_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here is a LinkedIn post draft:\n\n{post_text}\n\nFeedback to incorporate: {feedback}\n\nReturn the revised post only.",
            }
        ],
    )
    return message.content[0].text.strip()
