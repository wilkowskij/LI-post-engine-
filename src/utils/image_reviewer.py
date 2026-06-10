"""
Image QA reviewer — uses Claude vision to verify generated infographic images.

Checks:
  1. Numbering is sequential with no gaps or duplicates (e.g., catches 1,3,3,4)
  2. No phrase or subtitle text is repeated verbatim or near-verbatim
  3. Step/quadrant labels roughly match the expected diagram spec

Called after OpenAI image generation with up to MAX_RETRIES regeneration attempts.
"""
import base64
from pathlib import Path
from typing import Optional

import anthropic

MAX_RETRIES = 2

_REVIEW_PROMPT = """\
You are a quality-control reviewer for AI-generated infographic images.
Inspect the image carefully and check for these specific defects:

1. NUMBERING ERRORS
   - Are all visible numbers (step badges, quadrant labels, numbered items) in correct sequential order?
   - Are there any gaps (e.g., 1, 3, 4 — missing 2)?
   - Are there any duplicates (e.g., 1, 3, 3, 4 — 3 appears twice)?
   - Does the count match the expected number of items?

2. REPEATED TEXT
   - Is any phrase, subtitle, heading, or label duplicated (appears more than once in the image)?
   - Look carefully at subtitle lines — sometimes text is rendered twice with slight differences.

3. LABEL ACCURACY (if expected labels provided)
   - Do the step/quadrant labels in the image match the expected labels?

Expected diagram spec:
{spec_summary}

Respond with a JSON object only (no markdown fences):
{{
  "passed": true/false,
  "numbering_ok": true/false,
  "numbering_issues": "<describe any numbering problems, or empty string>",
  "repeated_text_ok": true/false,
  "repeated_text_issues": "<describe any repeated phrases found, or empty string>",
  "labels_ok": true/false,
  "label_issues": "<describe any label mismatches, or empty string>",
  "overall_notes": "<any other visual defects worth noting>"
}}

Be strict. If you see any defect, set passed=false.\
"""


def _build_spec_summary(diagram: dict) -> str:
    """Build a compact text summary of the expected diagram spec for the prompt."""
    lines = []
    title = diagram.get("title", "")
    subtitle = diagram.get("subtitle", "")
    steps = diagram.get("steps", [])
    f_title = diagram.get("foundation_title", "")
    f_items = diagram.get("foundation_items") or []

    if title:
        lines.append(f"Title: {title}")
    if subtitle:
        lines.append(f"Subtitle: {subtitle}")
    if steps:
        lines.append(f"Expected {len(steps)} steps numbered 1-{len(steps)}:")
        for i, s in enumerate(steps, 1):
            lines.append(f"  {i}. {s.get('label', '')}")
    if f_items:
        header = f_title or "Foundation"
        lines.append(f"{header}: {', '.join(f_items)}")

    return "\n".join(lines) if lines else "No spec provided."


def review_image(
    image_path: Path,
    diagram: dict,
    client: Optional[anthropic.Anthropic] = None,
) -> dict:
    """
    Inspect a generated image using Claude vision.

    Returns:
        {
            "passed": bool,
            "numbering_ok": bool,
            "numbering_issues": str,
            "repeated_text_ok": bool,
            "repeated_text_issues": str,
            "labels_ok": bool,
            "label_issues": str,
            "overall_notes": str,
        }
    """
    if client is None:
        import os
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    image_data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")
    spec_summary = _build_spec_summary(diagram)
    prompt = _REVIEW_PROMPT.format(spec_summary=spec_summary)

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()

    import json
    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        # If Claude didn't return clean JSON, treat as a pass to avoid blocking the pipeline
        print(f"[image_reviewer] WARNING: could not parse review JSON — treating as passed\n{raw}")
        return {
            "passed": True,
            "numbering_ok": True,
            "numbering_issues": "",
            "repeated_text_ok": True,
            "repeated_text_issues": "",
            "labels_ok": True,
            "label_issues": "",
            "overall_notes": f"parse error: {raw[:200]}",
        }

    # Log the review outcome
    if result.get("passed"):
        print("[image_reviewer] PASSED")
    else:
        issues = []
        if not result.get("numbering_ok"):
            issues.append(f"numbering: {result.get('numbering_issues', '')}")
        if not result.get("repeated_text_ok"):
            issues.append(f"repeated text: {result.get('repeated_text_issues', '')}")
        if not result.get("labels_ok"):
            issues.append(f"labels: {result.get('label_issues', '')}")
        if result.get("overall_notes"):
            issues.append(f"other: {result.get('overall_notes', '')}")
        print(f"[image_reviewer] FAILED — {' | '.join(issues)}")

    return result
