"""
Quote-card image generator for LinkedIn posts.

Primary: OpenAI gpt-image-1 (GPT Image 2) — produces AI-generated branded cards.
Fallback: Pillow — used when OPENAI_API_KEY is not set.
"""
import base64
import os
import re
import textwrap
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "images"

# LinkedIn landscape size closest to 1200×627 OG ratio
OPENAI_IMAGE_SIZE = "1536x1024"

# Brand palette (used by Pillow fallback)
BRAND = {
    "bg": "#0A0A0A",
    "accent": "#2563EB",
    "hook_text": "#FFFFFF",
    "sub_text": "#94A3B8",
    "tag_bg": "#1E3A5F",
    "tag_text": "#93C5FD",
}

W, H = 1200, 627


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_hook(post_text: str) -> str:
    for line in post_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return post_text.split(".")[0]


def _extract_hashtags(post_text: str) -> list[str]:
    return re.findall(r"#\w+", post_text)[:4]


def _build_image_prompt(hook: str, author_name: str, author_headline: str, hashtags: list[str]) -> str:
    tags_str = "  ".join(hashtags) if hashtags else ""
    return (
        "Create a professional LinkedIn thought-leadership quote card image. "
        "Dark near-black background (#0A0A0A). A bold electric-blue (#2563EB) vertical accent bar on the left edge "
        "and a thin horizontal accent line along the top. "
        f"Large bold white sans-serif text centered on the card reading: \"{hook}\" "
        "Below the quote, a short blue divider line, then the author's name in white bold "
        f"\"{author_name}\" and their title in slate-grey \"{author_headline}\". "
        f"Small blue hashtag pills in the bottom-right corner: {tags_str}. "
        "Clean, minimal, corporate-tech aesthetic. No stock photos, no people, no logos. "
        "High contrast. Landscape orientation 3:2 ratio. Photorealistic render quality."
    )


# ---------------------------------------------------------------------------
# GPT Image 2 (gpt-image-1) generator
# ---------------------------------------------------------------------------

def _generate_with_openai(
    hook: str,
    author_name: str,
    author_headline: str,
    hashtags: list[str],
    output_path: Path,
) -> Path:
    from openai import OpenAI  # lazy import — only needed when key is present

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = _build_image_prompt(hook, author_name, author_headline, hashtags)

    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=OPENAI_IMAGE_SIZE,
        quality="high",
        n=1,
    )

    image_data = base64.b64decode(response.data[0].b64_json)
    output_path.write_bytes(image_data)
    return output_path


# ---------------------------------------------------------------------------
# Pillow fallback
# ---------------------------------------------------------------------------

def _load_font(size: int, bold: bool = False):
    from PIL import ImageFont
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf" if bold else "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _generate_with_pillow(
    hook: str,
    author_name: str,
    author_headline: str,
    hashtags: list[str],
    output_path: Path,
) -> Path:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (W, H), color=BRAND["bg"])
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, 6, H], fill=BRAND["accent"])
    draw.rectangle([6, 0, W, 4], fill=BRAND["accent"])

    font_hook = _load_font(52, bold=True)
    font_sub = _load_font(26)
    font_tag = _load_font(22)
    font_name = _load_font(28, bold=True)
    font_title = _load_font(22)

    margin = 80
    wrapped = textwrap.fill(hook, width=38)
    lines = wrapped.splitlines()
    line_height = 64
    total_text_height = len(lines) * line_height
    y_start = (H - total_text_height) // 2 - 40

    for i, line in enumerate(lines):
        draw.text((margin, y_start + i * line_height), line, font=font_hook, fill=BRAND["hook_text"])

    divider_y = y_start + total_text_height + 30
    draw.rectangle([margin, divider_y, margin + 60, divider_y + 3], fill=BRAND["accent"])

    author_y = divider_y + 20
    draw.text((margin, author_y), author_name, font=font_name, fill=BRAND["hook_text"])
    draw.text((margin, author_y + 36), author_headline, font=font_title, fill=BRAND["sub_text"])

    if hashtags:
        pill_x = W - margin
        pill_y = H - 60
        pill_h = 32
        pill_pad = 14
        for tag in reversed(hashtags):
            bbox = draw.textbbox((0, 0), tag, font=font_tag)
            tag_w = bbox[2] - bbox[0] + pill_pad * 2
            pill_x -= tag_w + 10
            draw.rounded_rectangle(
                [pill_x, pill_y, pill_x + tag_w, pill_y + pill_h],
                radius=8, fill=BRAND["tag_bg"],
            )
            draw.text((pill_x + pill_pad, pill_y + 5), tag, font=font_tag, fill=BRAND["tag_text"])

    draw.text((W - margin, H - 30), "linkedin", font=font_title, fill=BRAND["sub_text"], anchor="rm")
    img.save(output_path, "PNG", optimize=True)
    return output_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_quote_card(
    post_text: str,
    author_name: str = "Jake Wilkowski",
    author_headline: str = "Senior Product Manager | SaaS & DaaS",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate a branded LinkedIn quote card.
    Uses gpt-image-1 (GPT Image 2) when OPENAI_API_KEY is set, otherwise Pillow.
    Returns the path to the saved PNG.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"card_{stamp}.png"

    hook = _extract_hook(post_text)
    hashtags = _extract_hashtags(post_text)

    if os.environ.get("OPENAI_API_KEY"):
        return _generate_with_openai(hook, author_name, author_headline, hashtags, output_path)

    return _generate_with_pillow(hook, author_name, author_headline, hashtags, output_path)
