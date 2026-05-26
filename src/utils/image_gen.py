"""
Image generators for LinkedIn posts.

Quote card:       OpenAI gpt-image-1 (primary) or Pillow (fallback).
Framework diagram: Pillow — step-flow with gold accents, serif typography.

Design language: professional, elegant, sophisticated.
  Palette — charcoal #111827 bg · warm gold #C9A255 accent · near-white text
  Typography — Liberation Serif Bold for display; Liberation Sans for body
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
    "bg":           "#111827",   # Charcoal — richer depth than pure black
    "surface":      "#1C2A3A",   # Elevated card surface
    "found_bg":     "#0D1520",   # Foundation pill depth
    "accent":       "#C9A255",   # Warm gold
    "accent_light": "#E8D5A3",   # Champagne / light gold
    "hook_text":    "#F8FAFC",   # Near-white (slightly warm)
    "sub_text":     "#94A3B8",   # Cool mid-gray
    "muted":        "#64748B",   # Darker muted gray
}

W, H = 1200, 627


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _extract_hook(post_text: str) -> str:
    for line in post_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return post_text.split(".")[0]


def _extract_hashtags(post_text: str) -> list[str]:
    return re.findall(r"#\w+", post_text)[:4]


def _load_font(size: int, bold: bool = False, serif: bool = False):
    """Load font with serif support for display text."""
    from PIL import ImageFont

    if serif:
        candidates = [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"
            if bold else "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _bg(draw):
    """Fill background and draw thin gold top accent line."""
    from PIL import ImageDraw
    draw.rectangle([0, 0, W, H], fill=BRAND["bg"])
    draw.rectangle([0, 0, W, 3], fill=BRAND["accent"])


def _build_image_prompt(hook: str, author_name: str, author_headline: str, hashtags: list[str]) -> str:
    tags_str = "  ".join(hashtags) if hashtags else ""
    return (
        "Create a professional LinkedIn thought-leadership image. "
        "Deep charcoal background (#111827). A thin warm-gold (#C9A255) horizontal accent line at the very top. "
        f"Large, bold serif font (elegant, editorial style) white text centered: \"{hook}\" "
        "Below the quote, a short thin warm-gold divider line, then the author's name "
        f"\"{author_name}\" in bold white and their title \"{author_headline}\" in cool gray. "
        f"Small warm-gold hashtag text bottom-right: {tags_str}. "
        "Sophisticated, minimal, executive aesthetic — no photos, no icons, no logos. "
        "Typography-driven. Landscape 3:2."
    )


# ---------------------------------------------------------------------------
# OpenAI quote card
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


# ---------------------------------------------------------------------------
# Pillow quote card
# ---------------------------------------------------------------------------

def _generate_with_pillow(hook, author_name, author_headline, hashtags, output_path):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (W, H), color=BRAND["bg"])
    draw = ImageDraw.Draw(img)
    _bg(draw)

    margin_x = 96
    margin_top = 60

    # Fonts
    f_hook = _load_font(46, bold=True, serif=True)
    f_author_name = _load_font(22, bold=True)
    f_author_title = _load_font(17)
    f_hash = _load_font(16)

    # Wrap hook text
    wrapped = textwrap.fill(hook, width=44)
    lines = wrapped.splitlines()
    line_h = 58
    block_h = len(lines) * line_h

    # Vertical center — nudge up slightly to leave room for author footer
    y_quote = max(margin_top, (H - block_h) // 2 - 36)

    for i, line in enumerate(lines):
        draw.text(
            (margin_x, y_quote + i * line_h),
            line,
            font=f_hook,
            fill=BRAND["hook_text"],
        )

    # Thin gold rule below quote
    rule_y = y_quote + block_h + 24
    draw.rectangle([margin_x, rule_y, margin_x + 48, rule_y + 2], fill=BRAND["accent"])

    # Author block
    author_y = rule_y + 18
    draw.text((margin_x, author_y), author_name, font=f_author_name, fill=BRAND["hook_text"])
    draw.text(
        (margin_x, author_y + 30),
        author_headline,
        font=f_author_title,
        fill=BRAND["sub_text"],
    )

    # Hashtags — plain gold text, bottom-right
    if hashtags:
        tag_text = "  ".join(hashtags)
        draw.text(
            (W - margin_x, H - 30),
            tag_text,
            font=f_hash,
            fill=BRAND["accent"],
            anchor="rb",
        )

    img.save(output_path, "PNG", optimize=True)
    return output_path


def generate_quote_card(
    post_text: str,
    author_name: str = "Jeff Wilkowski",
    author_headline: str = "Senior Product Manager | SaaS & DaaS",
    output_path: Optional[Path] = None,
) -> Path:
    """Generate a branded LinkedIn quote card."""
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
# Pillow framework diagram
# ---------------------------------------------------------------------------

def generate_framework_diagram(
    diagram: dict,
    author_name: str = "Jeff Wilkowski",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Render a visual framework diagram.

    diagram keys:
      title            str   ALL CAPS framework name
      subtitle         str   optional tagline
      steps            list  [{"label": str, "description": str}, ...]
      foundation_title str   optional header for the bottom row
      foundation_items list  optional ["ITEM", ...]
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"diagram_{stamp}.png"

    from PIL import Image, ImageDraw

    img = Image.new("RGB", (W, H), color=BRAND["bg"])
    draw = ImageDraw.Draw(img)
    _bg(draw)

    title = diagram.get("title", "FRAMEWORK").upper()
    subtitle = diagram.get("subtitle", "")
    steps = diagram.get("steps", [])[:6]
    foundation_title = diagram.get("foundation_title", "")
    foundation_items = (diagram.get("foundation_items") or [])[:6]
    has_foundation = bool(foundation_items)

    # Fonts
    f_title    = _load_font(28, bold=True, serif=True)
    f_subtitle = _load_font(15)
    f_stepnum  = _load_font(20, bold=True)
    f_label    = _load_font(12, bold=True)
    f_desc     = _load_font(11)
    f_found_h  = _load_font(11, bold=True)
    f_found    = _load_font(11, bold=True)
    f_byline   = _load_font(13)

    margin = 40

    # -- Title --
    title_y = 16
    draw.text((W // 2, title_y), title, font=f_title, fill=BRAND["hook_text"], anchor="mt")
    sub_y = title_y + 36
    if subtitle:
        draw.text((W // 2, sub_y), subtitle, font=f_subtitle, fill=BRAND["sub_text"], anchor="mt")

    header_bottom = sub_y + (20 if subtitle else 0)

    # -- Layout zones --
    footer_h  = 52 if has_foundation else 0
    byline_h  = 22
    step_top  = header_bottom + 14
    step_bot  = H - footer_h - byline_h - 8

    # -- Step boxes --
    n = max(1, len(steps))
    arrow_gap = 18
    box_w = max(60, (W - 2 * margin - (n - 1) * arrow_gap) // n)
    box_h = step_bot - step_top

    for i, step in enumerate(steps):
        bx = margin + i * (box_w + arrow_gap)
        by = step_top

        # Thin arrow between boxes
        if i > 0:
            mid_y = by + box_h // 2
            ax_start = bx - arrow_gap + 2
            ax_end   = bx - 3
            draw.line([(ax_start, mid_y), (ax_end, mid_y)], fill=BRAND["accent"], width=1)
            draw.polygon(
                [(ax_end, mid_y), (ax_end - 7, mid_y - 4), (ax_end - 7, mid_y + 4)],
                fill=BRAND["accent"],
            )

        # Box background
        draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=6, fill=BRAND["surface"])

        # Thin gold left accent border on each box
        draw.rounded_rectangle([bx, by, bx + 3, by + box_h], radius=2, fill=BRAND["accent"])

        cx = bx + box_w // 2
        inner_x = bx + 4  # offset past the gold bar

        # Step number: "01", "02", …
        num_str = f"{i + 1:02d}"
        num_y = by + 14
        draw.text((cx, num_y), num_str, font=f_stepnum, fill=BRAND["accent"], anchor="mt")

        # Label
        label = step.get("label", "").upper()
        label_y = num_y + 26
        # Wrap label if needed
        label_lines = textwrap.fill(label, width=max(6, box_w // 8)).splitlines()
        for j, ll in enumerate(label_lines[:2]):
            draw.text(
                (cx, label_y + j * 15),
                ll,
                font=f_label,
                fill=BRAND["hook_text"],
                anchor="mt",
            )

        # Description
        desc = step.get("description", "")
        desc_y = label_y + len(label_lines[:2]) * 15 + 6
        desc_lines = textwrap.fill(desc, width=max(8, box_w // 6)).splitlines()
        for j, dl in enumerate(desc_lines[:5]):
            draw.text(
                (cx, desc_y + j * 13),
                dl,
                font=f_desc,
                fill=BRAND["sub_text"],
                anchor="mt",
            )

    # -- Foundation row --
    if has_foundation:
        found_top = H - footer_h - byline_h + 4

        # Thin gold separator
        draw.rectangle([margin, found_top - 2, W - margin, found_top - 1], fill=BRAND["muted"])

        if foundation_title:
            draw.text(
                (W // 2, found_top + 2),
                foundation_title.upper(),
                font=f_found_h,
                fill=BRAND["sub_text"],
                anchor="mt",
            )

        pill_top = found_top + (16 if foundation_title else 4)
        pill_h_px = 24
        ni = len(foundation_items)
        gap = 8
        pill_w = max(40, (W - 2 * margin - (ni - 1) * gap) // ni)

        for i, item in enumerate(foundation_items):
            px = margin + i * (pill_w + gap)
            draw.rounded_rectangle(
                [px, pill_top, px + pill_w, pill_top + pill_h_px],
                radius=4,
                fill=BRAND["found_bg"],
            )
            # Thin gold top line on each pill
            draw.rectangle([px, pill_top, px + pill_w, pill_top + 2], fill=BRAND["accent"])
            draw.text(
                (px + pill_w // 2, pill_top + pill_h_px // 2 + 1),
                item.upper(),
                font=f_found,
                fill=BRAND["sub_text"],
                anchor="mm",
            )

    # -- Byline --
    draw.text(
        (W - margin, H - 8),
        author_name,
        font=f_byline,
        fill=BRAND["muted"],
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
    Route to the right image type based on post format.
    visual_framework → diagram; everything else → quote card.
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
