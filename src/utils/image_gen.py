"""
Quote-card image generator for LinkedIn posts.
Produces a clean 1200x627 branded card using the post's hook line.
"""
import textwrap
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "images"

# Brand palette — adjust to match your personal brand
BRAND = {
    "bg": "#0A0A0A",          # near-black background
    "accent": "#2563EB",       # blue accent bar
    "hook_text": "#FFFFFF",    # hook line (white)
    "sub_text": "#94A3B8",     # byline (slate-400)
    "tag_bg": "#1E3A5F",       # hashtag pill background
    "tag_text": "#93C5FD",     # hashtag pill text
}

# LinkedIn recommended OG size
W, H = 1200, 627


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try to load a system font, fall back to default."""
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


def _extract_hook(post_text: str) -> str:
    """Pull the first non-empty line as the hook."""
    for line in post_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return post_text.split(".")[0]


def _extract_hashtags(post_text: str) -> list[str]:
    """Pull hashtags from the post text."""
    import re
    return re.findall(r"#\w+", post_text)[:4]


def generate_quote_card(
    post_text: str,
    author_name: str = "Jake Wilkowski",
    author_headline: str = "Senior Product Manager | SaaS & DaaS",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate a branded LinkedIn quote card from a post's hook line.
    Returns the path to the saved PNG.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    hook = _extract_hook(post_text)
    hashtags = _extract_hashtags(post_text)

    img = Image.new("RGB", (W, H), color=BRAND["bg"])
    draw = ImageDraw.Draw(img)

    # Left accent bar
    draw.rectangle([0, 0, 6, H], fill=BRAND["accent"])

    # Top accent line
    draw.rectangle([6, 0, W, 4], fill=BRAND["accent"])

    # Wrap hook text
    font_hook = _load_font(52, bold=True)
    font_sub = _load_font(26)
    font_tag = _load_font(22)
    font_name = _load_font(28, bold=True)
    font_title = _load_font(22)

    margin = 80
    max_width = W - margin * 2

    # Wrap hook into lines that fit
    wrapped = textwrap.fill(hook, width=38)
    lines = wrapped.splitlines()

    # Draw hook text centered vertically
    line_height = 64
    total_text_height = len(lines) * line_height
    y_start = (H - total_text_height) // 2 - 40

    for i, line in enumerate(lines):
        draw.text((margin, y_start + i * line_height), line, font=font_hook, fill=BRAND["hook_text"])

    # Divider
    divider_y = y_start + total_text_height + 30
    draw.rectangle([margin, divider_y, margin + 60, divider_y + 3], fill=BRAND["accent"])

    # Author block
    author_y = divider_y + 20
    draw.text((margin, author_y), author_name, font=font_name, fill=BRAND["hook_text"])
    draw.text((margin, author_y + 36), author_headline, font=font_title, fill=BRAND["sub_text"])

    # Hashtag pills bottom-right
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
                radius=8,
                fill=BRAND["tag_bg"],
            )
            draw.text(
                (pill_x + pill_pad, pill_y + 5),
                tag, font=font_tag, fill=BRAND["tag_text"],
            )

    # Bottom-right watermark
    draw.text((W - margin, H - 30), "linkedin", font=font_title, fill=BRAND["sub_text"], anchor="rm")

    # Save
    if output_path is None:
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"card_{stamp}.png"

    img.save(output_path, "PNG", optimize=True)
    return output_path
