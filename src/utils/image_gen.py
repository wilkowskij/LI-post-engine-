"""
Image generator for LinkedIn posts.

Every post is accompanied by a framework diagram — a visual that explains
the concept, process, or mental model in the post text.

No quote cards. The diagram does the teaching; the post text provides context.
"""
import os
import re
import textwrap
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "images"

# Design language: professional, elegant, sophisticated
# Palette: charcoal bg · warm gold accent · Liberation Serif display type
BRAND = {
    "bg":           "#111827",   # Charcoal
    "surface":      "#1C2A3A",   # Elevated card surface
    "found_bg":     "#0D1520",   # Foundation pill depth
    "accent":       "#C9A255",   # Warm gold
    "hook_text":    "#F8FAFC",   # Near-white
    "sub_text":     "#94A3B8",   # Cool mid-gray
    "muted":        "#64748B",   # Darker gray (byline)
}

W, H = 1200, 627


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_font(size: int, bold: bool = False, serif: bool = False):
    from PIL import ImageFont
    if serif:
        candidates = [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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


def _base(draw):
    """Charcoal fill + thin gold top accent line."""
    draw.rectangle([0, 0, W, H], fill=BRAND["bg"])
    draw.rectangle([0, 0, W, 3], fill=BRAND["accent"])


# ---------------------------------------------------------------------------
# Framework diagram
# ---------------------------------------------------------------------------

def generate_framework_diagram(
    diagram: dict,
    author_name: str = "Jeff Wilkowski",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Render a visual framework diagram.

    diagram keys:
      title            str   Framework name (will be uppercased)
      subtitle         str   One-line tagline
      steps            list  [{"label": str, "description": str}, ...]
      foundation_title str   Header for the bottom row (optional)
      foundation_items list  ["ITEM", ...] shown as pills (optional)
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"diagram_{stamp}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    from PIL import Image, ImageDraw

    img = Image.new("RGB", (W, H), color=BRAND["bg"])
    draw = ImageDraw.Draw(img)
    _base(draw)

    title           = diagram.get("title", "FRAMEWORK").upper()
    subtitle        = diagram.get("subtitle", "")
    steps           = diagram.get("steps", [])[:6]
    foundation_title = diagram.get("foundation_title", "")
    foundation_items = (diagram.get("foundation_items") or [])[:6]
    has_foundation  = bool(foundation_items)

    # Fonts
    f_title   = _load_font(28, bold=True, serif=True)
    f_sub     = _load_font(15)
    f_num     = _load_font(20, bold=True)
    f_label   = _load_font(12, bold=True)
    f_desc    = _load_font(11)
    f_found_h = _load_font(11, bold=True)
    f_found   = _load_font(11, bold=True)
    f_byline  = _load_font(13)

    margin = 40

    # Title block
    title_y = 16
    draw.text((W // 2, title_y), title, font=f_title, fill=BRAND["hook_text"], anchor="mt")
    sub_y = title_y + 36
    if subtitle:
        draw.text((W // 2, sub_y), subtitle, font=f_sub, fill=BRAND["sub_text"], anchor="mt")

    header_bottom = sub_y + (20 if subtitle else 0)

    # Layout zones
    footer_h = 52 if has_foundation else 0
    byline_h = 22
    step_top = header_bottom + 14
    step_bot = H - footer_h - byline_h - 8

    # Step boxes
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

        # Box background + thin gold left border
        draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=6, fill=BRAND["surface"])
        draw.rounded_rectangle([bx, by, bx + 3, by + box_h], radius=2, fill=BRAND["accent"])

        cx = bx + box_w // 2

        # Step number 01, 02, 03 …
        draw.text((cx, by + 14), f"{i + 1:02d}", font=f_num, fill=BRAND["accent"], anchor="mt")

        # Label (uppercase, bold white)
        label = step.get("label", "").upper()
        label_y = by + 40
        for j, ll in enumerate(textwrap.fill(label, width=max(6, box_w // 8)).splitlines()[:2]):
            draw.text((cx, label_y + j * 15), ll, font=f_label, fill=BRAND["hook_text"], anchor="mt")

        # Description (gray, wrapped)
        desc = step.get("description", "")
        desc_y = label_y + 32
        for j, dl in enumerate(textwrap.fill(desc, width=max(8, box_w // 6)).splitlines()[:5]):
            draw.text((cx, desc_y + j * 13), dl, font=f_desc, fill=BRAND["sub_text"], anchor="mt")

    # Foundation row
    if has_foundation:
        found_top = H - footer_h - byline_h + 4
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
        ni  = len(foundation_items)
        gap = 8
        pill_w = max(40, (W - 2 * margin - (ni - 1) * gap) // ni)

        for i, item in enumerate(foundation_items):
            px = margin + i * (pill_w + gap)
            draw.rounded_rectangle(
                [px, pill_top, px + pill_w, pill_top + pill_h_px],
                radius=4,
                fill=BRAND["found_bg"],
            )
            draw.rectangle([px, pill_top, px + pill_w, pill_top + 2], fill=BRAND["accent"])
            draw.text(
                (px + pill_w // 2, pill_top + pill_h_px // 2 + 1),
                item.upper(),
                font=f_found,
                fill=BRAND["sub_text"],
                anchor="mm",
            )

    # Byline
    draw.text((W - margin, H - 8), author_name, font=f_byline, fill=BRAND["muted"], anchor="rb")

    img.save(output_path, "PNG", optimize=True)
    return output_path


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def generate_post_image(
    post: dict,
    author_name: str = "Jeff Wilkowski",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate the diagram image for a post.
    Requires post["diagram"] to be populated — call writer.generate_diagram_spec()
    first if the post was not generated in visual_framework format.

    Uses Playwright HTML renderer when available; falls back to Pillow.
    """
    diagram = post.get("diagram")
    if not diagram:
        raise ValueError(
            "post has no 'diagram' spec. Call writer.generate_diagram_spec(post, client) first."
        )

    try:
        from src.utils.html_renderer import render_card
        return render_card(
            diagram,
            post.get("text", ""),
            author_name=author_name,
            output_path=output_path,
        )
    except ImportError:
        pass

    return generate_framework_diagram(diagram, author_name=author_name, output_path=output_path)
