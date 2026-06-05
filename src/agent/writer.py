"""
LinkedIn post writer — generates posts in Senior PM voice using Claude.
"""
import json
import random
from typing import Optional

import anthropic

from src.agent.persona import PERSONA_SYSTEM_PROMPT, POST_FORMATS, HASHTAG_MAP, TOPIC_CATEGORIES

_VISUAL_FRAMEWORK_SUFFIX = """

IMPORTANT — this is a visual_framework post. Return a single JSON object (no markdown fences) with exactly these keys:

{
  "post_text": "<the LinkedIn post text, ready to copy-paste>",
  "diagram": {
    "title": "<ALL CAPS framework name, max 5 words>",
    "subtitle": "<one short descriptive sentence about what the diagram shows>",
    "steps": [
      {"label": "<ALL CAPS step label, 2-3 words>", "description": "<one sentence, max 12 words>"},
      ...
    ],
    "foundation_title": "<ALL CAPS title for the bottom row, optional>",
    "foundation_items": ["<ITEM LABEL>", ...]
  }
}

Steps: 4-5 items. Foundation items: 3-5 items (or omit the array if there is no natural foundation layer).
The diagram must be self-contained — someone who only sees the image should understand the framework.

CRITICAL RULES FOR post_text:
- The post_text must read as a complete, standalone LinkedIn post — no references to the diagram at all.
- Never write "[see diagram]", "see above", "as shown", "the framework below", or any phrase that references the image.
- The diagram is an attached image. The post text will appear separately. Write the post_text as if no image exists.
- Never name specific companies, clients, or competitors — speak in patterns and principles."""


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

    preferred = ["trend_prediction", "framework", "hot_take", "breakdown", "myth_busting", "data_insight"]
    chosen_format = post_format or random.choice(preferred)
    fmt = POST_FORMATS[chosen_format]
    hashtags = HASHTAG_MAP.get(topic, ["#ProductManagement", "#SaaS", "#GTM"])

    angle_note = f"\n\nSpecific angle to emphasize: {custom_angle}" if custom_angle else ""

    is_visual = chosen_format == "visual_framework"
    format_suffix = _VISUAL_FRAMEWORK_SUFFIX if is_visual else "\nReturn ONLY the post text, ready to copy-paste to LinkedIn. No meta-commentary."

    user_prompt = f"""Write a LinkedIn post for Jeff Wilkowski — Senior PM in the SaaS/PLG/DaaS space.

RESEARCH BRIEF:
{research_brief}
{angle_note}

POST FORMAT: {chosen_format}
What it is: {fmt['description']}
How it should be structured: {fmt['structure']}
Target length: {fmt['length']}

HASHTAGS — pick 5-8 that fit naturally and are relevant to the industry: {', '.join(hashtags)}

A few reminders about voice:
- Write like you're explaining something important to a smart colleague, not writing a blog post
- One strong, specific idea defended well beats five shallow points
- Don't cite specific reports or statistics unless you'd stake your reputation on the accuracy —
  it's better to say "I've seen this pattern" than invent a precise number
- The opener should earn attention through genuine curiosity or a real challenge to assumptions —
  it doesn't have to be a prediction or framework announcement
- If you end with a question, make it one that actually has stakes — not "what do you think?"
- Write for mobile: short paragraphs, natural line breaks, varied sentence length
{format_suffix}"""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=900 if is_visual else 600,
        system=PERSONA_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()

    if is_visual:
        data = _parse_visual_framework_response(raw, topic, chosen_format, hashtags)
        data["text"] = _stop_slop_pass(data["text"], client)
        return data

    post_text = _enforce_char_limit(raw, client, user_prompt)
    post_text = _stop_slop_pass(post_text, client)

    return {
        "text": post_text,
        "topic": topic,
        "format": chosen_format,
        "hashtags": hashtags,
        "word_count": len(post_text.split()),
        "char_count": len(post_text),
    }


_LI_CHAR_LIMIT = 3000


def _enforce_char_limit(text: str, client, original_prompt: str, limit: int = _LI_CHAR_LIMIT) -> str:
    """If text exceeds the LinkedIn character limit, ask Claude to tighten it."""
    if len(text) <= limit:
        return text

    tighten_prompt = (
        f"This LinkedIn post is {len(text)} characters — over the {limit}-character limit.\n\n"
        f"{text}\n\n"
        f"Tighten it to under {limit} characters while keeping every key idea. "
        f"Return ONLY the revised post text, nothing else."
    )
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=600,
        system=PERSONA_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": tighten_prompt}],
    )
    return message.content[0].text.strip()


_STOP_SLOP_PROMPT = """\
Review this LinkedIn post and fix every AI writing pattern you find. Apply ALL rules below:

REMOVE throat-clearing openers:
"Here's the thing:" / "Here's what/why X" / "It turns out" / "The truth is," /
"The uncomfortable truth is" / "Make no mistake" / "Let that sink in." /
"The reality is" / "I'll be honest" / "At the end of the day"

REMOVE binary contrast structures — state the point directly instead:
"Not X. But Y." / "The answer isn't X. It's Y." / "not just X but also Y" /
"aren't failing because X ... Y is the problem" / "It's not X. It's Y."

REMOVE dramatic fragments used for emphasis:
"Every time." / "Full stop." / "Day one." / "That's it." / "Simple as that." /
Any sentence under 5 words that exists only for punch — fold it into the prior sentence.

REMOVE lazy extremes: every, always, never, everyone, nobody — replace with specifics.

KILL all adverbs: really, just, literally, genuinely, honestly, simply, actually, deeply,
truly, fundamentally, inherently, inevitably, crucially, importantly, quietly, clearly

FIX false agency — name the human actor:
Wrong: "the data tells us" / "the market rewards" / "the culture shifts" /
"the conversation moves" / "pricing evolves"
Right: "buyers pay" / "you read the data and see" / "teams shift behavior"

FIX passive voice: find the actor, make them the subject.

FIX Wh- sentence openers: "What makes this hard..." → "The constraint is..."

REMOVE business jargon:
navigate→handle, unpack→explain, landscape→situation, deep dive→analysis,
circle back→return to, double down→commit, table stakes→baseline requirement,
dressed up as→disguised as (then rewrite to be direct), substrate→foundation

NO em-dashes anywhere. Use commas or periods.

NO company or product names: remove any specific company, tool, or product name
and replace with a description of the pattern or category instead.
Wrong: "like Clay separating platform from token cost"
Right: "like separating platform access from consumption cost"

NO manufactured statistics: if a number like "the failing 95%" or "3x the multiple"
appears without a real source, rewrite as a pattern observation instead.
Wrong: "The failing 95% aren't losing at AI"
Right: "Most teams aren't losing at AI"

NO diagram references in post text: remove any phrase like "[see diagram]",
"see above", "as shown", "the framework below", "the pattern looks like this:" followed
by nothing. The post text must stand completely alone.

Return ONLY the revised post text. No commentary, no scoring, no explanation.
Preserve the hashtags exactly as written at the end.\
"""


def _stop_slop_pass(text: str, client) -> str:
    """Run a stop-slop cleanup pass to remove AI writing patterns."""
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=700,
        system=PERSONA_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"{_STOP_SLOP_PROMPT}\n\nPOST:\n{text}"}],
    )
    return message.content[0].text.strip()


def _parse_visual_framework_response(raw: str, topic: str, fmt: str, hashtags: list) -> dict:
    """Parse the JSON response for a visual_framework post."""
    try:
        # Strip accidental markdown fences
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip()

        data = json.loads(text)
        post_text = data.get("post_text", raw)
        diagram = data.get("diagram", {})
    except (json.JSONDecodeError, ValueError):
        post_text = raw
        diagram = {}

    return {
        "text": post_text,
        "topic": topic,
        "format": fmt,
        "hashtags": hashtags,
        "diagram": diagram,
        "word_count": len(post_text.split()),
        "char_count": len(post_text),
    }


_DIAGRAM_SPEC_PROMPT = """\
You are given a LinkedIn post. Generate a framework diagram spec that visually explains \
the core concept, process, or mental model in the post.

The diagram should TEACH something the reader can apply — not repeat the post text.

Return a single JSON object (no markdown fences):
{
  "title": "<ALL CAPS framework name, 3-5 words>",
  "subtitle": "<one tagline describing what the diagram shows, max 12 words>",
  "steps": [
    {"label": "<ALL CAPS, 2-3 words>", "description": "<one sentence, max 12 words>"},
    ...
  ],
  "foundation_title": "<ALL CAPS foundation layer header, optional>",
  "foundation_items": ["<ITEM>", ...]
}

Steps: 4-5 items that form a logical sequence or flow.
Foundation items: 3-5 supporting concepts (omit the key entirely if there is no natural layer).
The diagram must stand alone — someone who only sees the image should understand the framework."""


def generate_diagram_spec(post: dict, client: Optional[anthropic.Anthropic] = None) -> dict:
    """
    Generate a framework diagram spec for any post format.
    Adds the spec to post["diagram"] in-place and returns the spec dict.
    Already-present specs (visual_framework posts) are returned as-is.
    """
    if post.get("diagram"):
        return post["diagram"]

    if client is None:
        import os
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=600,
        system="You create concise, clear visual framework diagrams for LinkedIn posts.",
        messages=[
            {
                "role": "user",
                "content": (
                    f"{_DIAGRAM_SPEC_PROMPT}\n\n"
                    f"POST:\n{post['text']}"
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    try:
        text = raw
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip()
        spec = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        spec = {}

    post["diagram"] = spec
    return spec


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
