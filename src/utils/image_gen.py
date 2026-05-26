"""
Image generators for LinkedIn posts.

Quote card:  OpenAI gpt-image-1 (primary) or Pillow (fallback).
Framework diagram: Pillow — renders a numbered step-flow with a foundation layer.
"""
import base64
import os
import re
import textwrap
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "images"

OPENAI_IMAGE_SIZE = "1536x1024"

BRAND = {
    "bg": "#0A0A0A",
    "accent": "#2563EB",
    "hook_text": "#FFFFFF",
    "sub_text": "#94A3B8",
    "tag_bg": "#1E3A5F",
    "tag_text": "#93C5FD",
    "found_bg": "#111827",
}

# Step-number circle colors (cycles if more than 5 steps)
STEP_COLORS = ["#2563EB", "#059669", "#F59E0B", "#DC2626", "#7C3AED"]

W, H = 1200, 627


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _hex(color: str) -> tuple:
    """Convert #RRGGBB to (R, G, B)."""
    c = color.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))


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


def _accent_bars(draw, brand=BRAND):
    draw.rectangle([0, 0, 6, H], fill=brand["accent"])
    draw.rectangle([6, 0, W, 4], fill=brand["accent"])


# ---------------------------------------------------------------------------
# Quote card (OpenAI + Pillow fallback)
# ---------------------------------------------------------------------------

def _generate_with_openai(hook, author_name, author_headline, hashtags, output_path):
    from openai import OpenAI
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


def _generate_with_pillow(hook, author_name, author_headline, hashtags, output_path):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (W, H), color=BRAND["bg"])
    draw = ImageDraw.Draw(img)
    _accent_bars(draw)

    font_hook = _load_font(52, bold=True)
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


def generate_quote_card(
    post_text: str,
    author_name: str = "Jeff Wilkowski",
    author_headline: str = "Senior Product Manager | SaaS & DaaS",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate a branded LinkedIn quote card.
    Uses gpt-image-1 when OPENAI_API_KEY is set, otherwise Pillow.
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


# ---------------------------------------------------------------------------
# Framework diagram (Pillow only)
# ---------------------------------------------------------------------------

def generate_framework_diagram(
    diagram: dict,
    author_name: str = "Jeff Wilkowski",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Render a visual framework diagram from a structured spec dict.

    Expected dict keys:
      title            str   ALL CAPS framework name
      subtitle         str   optional tagline
      steps            list  [{"label": str, "description": str}, ...]
      foundation_title str   optional header for the bottom row
      foundation_items list  optional ["ITEM", ...] shown as pills at the bottom
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"diagram_{stamp}.png"

    from PIL import Image, ImageDraw

    img = Image.new("RGB", (W, H), color=BRAND["bg"])
    draw = ImageDraw.Draw(img)
    _accent_bars(draw)

    title = diagram.get("title", "FRAMEWORK").upper()
    subtitle = diagram.get("subtitle", "")
    steps = diagram.get("steps", [])[:6]
    foundation_title = diagram.get("foundation_title", "")
    foundation_items = (diagram.get("foundation_items") or [])[:6]

    has_foundation = bool(foundation_items)

    # Fonts
    f_title = _load_font(30, bold=True)
    f_subtitle = _load_font(16)
    f_step_num = _load_font(18, bold=True)
    f_step_label = _load_font(13, bold=True)
    f_step_desc = _load_font(11)
    f_found_head = _load_font(12, bold=True)
    f_found_item = _load_font(12, bold=True)
    f_byline = _load_font(14)

    margin = 36

    # -- Title block --
    title_y = 18
    draw.text((W // 2, title_y), title, font=f_title, fill=BRAND["hook_text"], anchor="mt")
    sub_y = title_y + 38
    if subtitle:
        draw.text((W // 2, sub_y), subtitle, font=f_subtitle, fill=BRAND["sub_text"], anchor="mt")

    header_bottom = sub_y + (22 if subtitle else 0)

    # -- Layout areas --
    footer_h = 54 if has_foundation else 0
    byline_h = 24
    step_top = header_bottom + 14
    step_bottom = H - footer_h - byline_h - 10

    # -- Step boxes --
    n = max(1, len(steps))
    arrow_gap = 22
    total_arrows = (n - 1) * arrow_gap
    box_w = max(60, (W - 2 * margin - total_arrows) // n)
    box_h = step_bottom - step_top

    for i, step in enumerate(steps):
        bx = margin + i * (box_w + arrow_gap)
        by = step_top

        # Arrow from previous box
        if i > 0:
            ax = bx - arrow_gap
            mid_y = by + box_h // 2
            draw.line([(ax, mid_y), (bx - 4, mid_y)], fill=BRAND["accent"], width=2)
            # Arrowhead
            draw.polygon(
                [(bx - 4, mid_y), (bx - 10, mid_y - 5), (bx - 10, mid_y + 5)],
                fill=BRAND["accent"],
            )

        # Box
        draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=8, fill=BRAND["tag_bg"])

        cx = bx + box_w // 2

        # Number circle
        color = STEP_COLORS[i % len(STEP_COLORS)]
        r = 13
        cy_circle = by + 18
        draw.ellipse([cx - r, cy_circle - r, cx + r, cy_circle + r], fill=color)
        draw.text((cx, cy_circle), str(i + 1), font=f_step_num, fill="#FFFFFF", anchor="mm")

        # Label
        label = step.get("label", "").upper()
        label_y = cy_circle + r + 8
        draw.text((cx, label_y), label, font=f_step_label, fill=BRAND["hook_text"], anchor="mt")

        # Description — wrap to fit box width
        desc = step.get("description", "")
        char_width = max(8, box_w // 7)
        wrapped = textwrap.fill(desc, width=char_width)
        desc_y = label_y + 18
        for j, line in enumerate(wrapped.splitlines()[:5]):
            draw.text(
                (cx, desc_y + j * 14),
                line,
                font=f_step_desc,
                fill=BRAND["sub_text"],
                anchor="mt",
            )

    # -- Foundation row --
    if has_foundation:
        found_top = H - footer_h - byline_h
        if foundation_title:
            draw.text(
                (W // 2, found_top + 2),
                foundation_title.upper(),
                font=f_found_head,
                fill=BRAND["sub_text"],
                anchor="mt",
            )
        pill_top = found_top + (18 if foundation_title else 4)
        pill_h_px = 26
        ni = len(foundation_items)
        pill_gap = 8
        pill_w = max(40, (W - 2 * margin - (ni - 1) * pill_gap) // ni)

        for i, item in enumerate(foundation_items):
            px = margin + i * (pill_w + pill_gap)
            py = pill_top
            draw.rounded_rectangle([px, py, px + pill_w, py + pill_h_px], radius=6, fill=BRAND["found_bg"])
            draw.text(
                (px + pill_w // 2, py + pill_h_px // 2),
                item.upper(),
                font=f_found_item,
                fill=BRAND["tag_text"],
                anchor="mm",
            )

    # -- Byline --
    draw.text(
        (W - margin, H - 10),
        author_name,
        font=f_byline,
        fill=BRAND["sub_text"],
        anchor="rb",
    )

    img.save(output_path, "PNG", optimize=True)
    return output_path


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def generate_post_image(
    post: dict,
    author_name: str = "Jeff Wilkowski",
    author_headline: str = "Senior Product Manager | SaaS & DaaS",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Choose the right image type based on post format.
    visual_framework posts get a diagram; all others get a quote card.
    """
    if post.get("format") == "visual_framework" and post.get("diagram"):
        return generate_framework_diagram(
            post["diagram"],
            author_name=author_name,
            output_path=output_path,
        )
    return generate_quote_card(
        post["text"],
        author_name=author_name,
        author_headline=author_headline,
        output_path=output_path,
    )
