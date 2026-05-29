"""
OpenAI image generation for LinkedIn post cards.

Uses gpt-image-1 (the model behind ChatGPT's free image generation)
with DALL-E 3 as fallback. Rotates between two visual styles:
  1. Light lavender/white infographic (clean, editorial)
  2. Dark neon numbered-steps roadmap (bold, high-contrast)
"""
import base64
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Optional


# Style 1 — Light lavender/white infographic
_LIGHT_LAVENDER_PROMPT = """\
Create a professional explainer infographic in the style of a LinkedIn \
thought-leadership visual with the following specs:

STYLE:
- Light lavender/white background (#f5f0ff or white)
- Primary colors: purple (#7B5EA7), blue (#4A90D9), yellow (#F5C842), \
teal (#4ECDC4)
- Hand-drawn/sketch-style icons (not photorealistic)
- Rounded rectangle boxes with soft drop shadows
- Bold sans-serif title (large, dark navy)
- Subtitle in lighter italic or regular weight
- Dashed and solid arrows showing flow/direction
- Small emoji-style or outline icons inside each box
- Numbered section labels in colored pill/badge shapes

LAYOUT:
- 1200x1200px or 1080x1350px (square or portrait for LinkedIn)
- 4-section flow: [Left column] → [Center grid] → [Right column]
- Bottom strip for sub-process steps (horizontal icon chain)
- "Why It Matters" callout box with checklist bullets

CONTENT TO VISUALIZE:
{content}

OUTPUT:
- Label each section with numbers (1, 2, 3, 4)
- Use short 2-4 word headers per box
- Add 1-line subtitles under each header
- Include a small robot/AI mascot character in bottom-left corner
- Add creator initials badge (circle) in top-left\
"""

# Style 2 — Dark neon numbered-steps roadmap
_DARK_NEON_PROMPT = """\
Create a bold LinkedIn thought-leadership infographic in a dark neon \
numbered-steps roadmap style with the following specs:

STYLE:
- Deep navy/space background (#070B14 to #0D1525 gradient)
- Neon green (#00FF7F) glowing borders on each step card
- Title text: large, bold, white with yellow accent (#F5C842) on key words
- Subtitle: smaller, lighter gray-white text below the title
- Each card: dark surface (#0F1923) with a 2px neon green glowing border \
and subtle inner glow
- Neon-colored glowing icons (green, yellow, purple) inside each card — \
outline/line style, not photorealistic
- Numbered circular badges (1, 2, 3...) in bright neon green at card \
corners connecting the flow path
- Bullet points inside each card use small arrow (→) or checkmark bullets \
in neon green
- A bottom "key takeaway" line in each card in italic lighter text with \
a right-arrow prefix

LAYOUT:
- 1080x1350px portrait (LinkedIn optimized)
- Large bold title block at the top (2-3 lines)
- Steps arranged in a 2-column grid flowing in S-curve order: \
top-left → top-right → middle-left → middle-right → bottom-left → bottom-right
- Each step card shows: step number badge, bold step title, 3-4 bullet points, \
1 takeaway line
- A glowing neon divider line between the title block and the step grid
- "JW" initials badge (dark circle with neon green border) in the bottom-right corner

CONTENT TO VISUALIZE:
{content}

OUTPUT:
- Make the title dominant — it should read like a bold LinkedIn hook
- Each step card gets a relevant neon-glowing icon in the top-right corner
- The numbered badges should visually connect as a flow path across the grid
- Keep bullet text short (5-8 words per bullet)
- The overall feel: high-contrast, professional, scroll-stopping\
"""

_STYLES = [_LIGHT_LAVENDER_PROMPT, _DARK_NEON_PROMPT]


def format_image_prompt(diagram: dict, post_text: str, style_prompt: Optional[str] = None) -> str:
    """Build the full image generation prompt from a diagram spec and post text.

    style_prompt: pass a specific style template, or None to pick randomly.
    """
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

    chosen_style = style_prompt or random.choice(_STYLES)
    return chosen_style.format(content=content)


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

    # gpt-image-1 = the model behind ChatGPT free image generation
    #   - returns b64_json by default; does NOT accept response_format param
    # dall-e-3 fallback
    #   - requires response_format="b64_json" to get bytes instead of a URL
    candidates = [
        ("gpt-image-1", "1024x1536", {}),
        ("dall-e-3",    "1024x1792", {"response_format": "b64_json"}),
    ]

    errors = []
    for model, size, extra_kwargs in candidates:
        try:
            print(f"[openai_image_gen] trying {model} @ {size}...")
            response = client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size=size,
                **extra_kwargs,
            )
            # gpt-image-1 returns b64_json by default; dall-e-3 with response_format also
            img_b64 = response.data[0].b64_json
            if img_b64:
                output_path.write_bytes(base64.b64decode(img_b64))
                print(f"[openai_image_gen] success with {model}")
                return output_path
            # fallback: URL response (dall-e-3 without response_format)
            url = response.data[0].url
            if url:
                import urllib.request
                urllib.request.urlretrieve(url, output_path)
                print(f"[openai_image_gen] success with {model} (url)")
                return output_path
        except Exception as e:
            msg = f"{model}: {e}"
            print(f"[openai_image_gen] failed — {msg}")
            errors.append(msg)
            continue

    raise RuntimeError(f"OpenAI image generation failed: {'; '.join(errors)}")
