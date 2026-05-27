"""
OpenAI image generation for LinkedIn post cards.

Uses gpt-image-1 (the model behind ChatGPT's free image generation)
with DALL-E 3 as fallback. Produces light lavender/white infographic-style
visuals matching the master prompt template in src/templates/.
"""
import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


_STYLE_BLOCK = """\
STYLE:
- Light lavender/white background (#f5f0ff or white)
- Primary colors: purple (#7B5EA7), blue (#4A90D9), yellow (#F5C842), teal (#4ECDC4)
- Hand-drawn/sketch-style icons (not photorealistic)
- Rounded rectangle boxes with soft drop shadows
- Bold sans-serif title (large, dark navy)
- Subtitle in lighter italic or regular weight
- Dashed and solid arrows showing flow/direction
- Small emoji-style or outline icons inside each box
- Numbered section labels in colored pill/badge shapes

LAYOUT:
- 1080x1350px portrait for LinkedIn
- 4-section flow: [Left column] → [Center grid] → [Right column]
- Bottom strip for sub-process steps (horizontal icon chain)
- "Why It Matters" callout box with checklist bullets

OUTPUT:
- Label each section with numbers (1, 2, 3, 4)
- Use short 2-4 word headers per box
- Add 1-line subtitles under each header
- Include a small robot/AI mascot character in bottom-left corner
- Add creator initials "JW" badge (circle) in top-left\
"""


def format_image_prompt(diagram: dict, post_text: str) -> str:
    """Build the full image generation prompt from a diagram spec and post text."""
    title    = diagram.get("title", "FRAMEWORK")
    subtitle = diagram.get("subtitle", "")
    steps    = diagram.get("steps", [])
    f_title  = diagram.get("foundation_title", "")
    f_items  = diagram.get("foundation_items") or []

    lines = []

    # Hook — first non-empty line of post
    hook_lines = [ln.strip() for ln in post_text.strip().splitlines() if ln.strip()]
    hook = hook_lines[0] if hook_lines else ""

    lines.append(f"TITLE: {title}")
    if subtitle:
        lines.append(f"SUBTITLE: {subtitle}")
    lines.append("")
    if hook:
        lines.append(f"CONTEXT: {hook}")
        lines.append("")

    lines.append("FRAMEWORK STEPS (sequential flow, left to right or top to bottom):")
    for i, step in enumerate(steps, 1):
        label = step.get("label", "")
        desc  = step.get("description", "")
        lines.append(f"  {i}. {label} — {desc}")

    if f_items:
        lines.append("")
        header = f_title if f_title else "FOUNDATION"
        lines.append(f"{header}:")
        lines.append("  " + "  ·  ".join(f_items))

    content = "\n".join(lines)

    return (
        "Create a professional explainer infographic in the style of a LinkedIn "
        "thought-leadership visual with the following specs:\n\n"
        f"{_STYLE_BLOCK}\n\n"
        f"CONTENT TO VISUALIZE:\n{content}"
    )


def generate_image(
    diagram: dict,
    post_text: str,
    output_path: Optional[Path] = None,
    api_key: Optional[str] = None,
) -> Path:
    """
    Generate a LinkedIn card image via OpenAI.

    Tries gpt-image-1 first (the model behind ChatGPT free image generation),
    falls back to dall-e-3 if the account doesn't have access yet.
    """
    import openai

    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    if output_path is None:
        out_dir = Path(__file__).parent.parent.parent / "output" / "images"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"card_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = openai.OpenAI(api_key=api_key)
    prompt = format_image_prompt(diagram, post_text)

    # gpt-image-1 = the model ChatGPT free uses; portrait 1024×1536
    # dall-e-3 fallback = portrait 1024×1792
    candidates = [
        ("gpt-image-1", "1024x1536"),
        ("dall-e-3",    "1024x1792"),
    ]

    last_error = None
    for model, size in candidates:
        try:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size=size,
                response_format="b64_json",
            )
            img_bytes = base64.b64decode(response.data[0].b64_json)
            output_path.write_bytes(img_bytes)
            return output_path
        except openai.NotFoundError:
            # Model not available on this account tier — try next
            last_error = f"{model} not available"
            continue
        except openai.BadRequestError as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"OpenAI image generation failed: {last_error}")
