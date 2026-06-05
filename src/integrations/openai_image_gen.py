"""
OpenAI image generation for LinkedIn post cards.

Uses gpt-image-1 (the model behind ChatGPT's free image generation)
with DALL-E 3 as fallback. Rotates between six visually distinct styles:
  1. Light lavender/white infographic (clean, editorial)
  2. Dark neon numbered-steps roadmap (bold, high-contrast)
  3. Bold typography minimalist (oversized text as design element)
  4. 2x2 strategy matrix (consulting/quadrant framework)
  5. Iceberg model (visible vs. hidden layers)
  6. Editorial muted magazine (warm cream, serif, sophisticated)
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
- 1080x1350px portrait (LinkedIn optimized)
- TOP SECTION: bold framework title + one-line subtitle (NOT a numbered box)
- MIDDLE GRID: 2-column grid of step cards — all steps numbered consecutively 1, 2, 3, 4, 5
  - Do NOT place any unnumbered context or hook text inside the step grid
  - Every cell in the grid is a numbered step card — no exceptions
  - Flow arrows connect: card 1 → card 2 → card 3 → card 4 → card 5 (S-curve)
- BOTTOM STRIP: "Why It Matters" with 3-4 short checklist bullets (no number badge)

CONTENT TO VISUALIZE:
{content}

OUTPUT:
- Number every step card: 01, 02, 03, 04, 05 — all must have a visible numbered badge
- Use short 2-4 word headers per step box
- Add 1-line description under each header
- Include a small robot/AI mascot character in bottom-left of the Why It Matters strip
- Add "JW" initials badge (small circle) in bottom-right corner\
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

# Style 3 — Bold typography minimalist
_BOLD_TYPOGRAPHY_PROMPT = """\
Create a bold typographic LinkedIn infographic where oversized text IS the \
primary design element — no photography, minimal iconography.

STYLE:
- Off-white background (#FAFAFA or #F8F6F2)
- Ultra-bold sans-serif headline at 40-50% of vertical space — readable as a thumbnail
- Color palette: deep charcoal (#1A1A1A) for primary text + ONE warm accent \
(choose from: terracotta #C4704F, dusty blue #3D6B8E, or slate green #3D6B5A)
- Thin geometric rule lines, brackets, or bold underlines as the only decoration
- Weight contrast: ultra-bold for labels, regular weight for descriptions
- Any statistics or numbers displayed at massive scale as a design feature
- Clean, editorial look — Wall Street Journal data graphics aesthetic

LAYOUT:
- 1080x1350px portrait
- Giant hook title at top (all-caps or title case, fills 40-45% of height)
- 3-5 framework points below in a clean vertical list with generous spacing
- Each point: accent-colored short bold label + 1-sentence description in lighter weight
- Bottom band: thin rule line + key takeaway or "JW" byline in small muted text
- Generous white space throughout — breathing room is a design feature

CONTENT TO VISUALIZE:
{content}

OUTPUT:
- The title must dominate — make it so large it feels almost too big
- Use the accent color sparingly: key words in the title, bullet labels, rule lines only
- No more than 10-15 words per bullet point line
- The overall feel: editorial, confident, no-nonsense — built to stop a scroll\
"""

# Style 4 — 2x2 strategy matrix
_QUADRANT_MATRIX_PROMPT = """\
Create a professional 2x2 strategy matrix LinkedIn infographic in a \
consulting/strategy style.

STYLE:
- Clean white background (#FFFFFF) with very subtle light gray grid (#F2F2F2)
- Axis lines in medium gray (#999999), clearly labeled at each end
- Four quadrant tinted fills using 2 accent colors at 15% opacity:
  top-left light blue (#EBF4FD), top-right light green (#EBF7EE),
  bottom-left light amber (#FEF8EB), bottom-right light purple (#F3EEFB)
- Quadrant labels in bold dark navy (#1A2744), centered in each quadrant
- Clean sans-serif font (no serifs, no decorative elements)
- McKinsey/strategy consulting aesthetic — rigorous and minimal

LAYOUT:
- 1080x1080px square
- Bold title at the top above the matrix (2 lines maximum)
- Short subtitle: "X-axis = [low→high label] | Y-axis = [low→high label]"
- Large 2x2 grid taking up 70% of the image
- Each quadrant: bold 2-3 word label at top + 2-3 tight bullet points
- Small circular number badges (1-4) in quadrant corners
- Footer: thin rule + one-line strategic insight + "JW" badge bottom right

CONTENT TO VISUALIZE:
{content}

OUTPUT:
- Map the framework steps into the 4 quadrants by logical opposition or tension
- Axis labels must make the core tradeoff immediately obvious
- Each quadrant label should be memorable and distinct (avoid generic terms)
- The overall feel: board-room ready, strategy deck quality\
"""

# Style 5 — Iceberg model
_ICEBERG_PROMPT = """\
Create an iceberg model LinkedIn infographic revealing visible surface vs. \
hidden depth — a reveal structure that shows what most people miss.

STYLE:
- Upper section (above waterline, ~30% of height): pale sky blue (#E8F4FD) \
with soft white clouds or gradient suggesting open air
- Waterline: a clear, bold horizontal line with subtle wave texture, \
labeled "WHAT MOST PEOPLE SEE" on the left
- Lower section (below waterline, ~70% of height): deep ocean blue \
(#0B3D6E graduating to #061F3A at the bottom)
- Iceberg shape: above water in crisp white (#FFFFFF), \
below water in translucent ice blue (#A8D4F0 at 60% opacity)
- Above-water text: dark navy — the obvious, surface-level items (1-2 only)
- Below-water text: white or very light — the hidden factors (3-5 items)
- Gold accent (#F5C842) for title and section dividers

LAYOUT:
- 1080x1350px portrait
- Bold gold title at the very top: "THE [FRAMEWORK NAME] ICEBERG"
- Above waterline: 1-2 items (the commonly observed behaviors/symptoms)
- Clear waterline divider with "WHAT MOST PEOPLE SEE" label
- Below waterline: 3-5 items in the iceberg body, spaced vertically, \
getting progressively more foundational toward the bottom
- Each item: bold short label + 1-line description
- Bottom edge: key insight in small white italic

CONTENT TO VISUALIZE:
{content}

OUTPUT:
- Reframe the framework steps as surface observations (above) vs. root causes (below)
- The below-water items should feel like genuine revelations — things people overlook
- The depth should feel real: bottom items most hidden, most important
- The overall feel: thought-provoking, "now I see it differently"\
"""

# Style 6 — Editorial muted magazine
_EDITORIAL_MUTED_PROMPT = """\
Create an editorial magazine-style LinkedIn infographic with a warm, \
sophisticated palette — think Harvard Business Review meets LinkedIn.

STYLE:
- Warm cream/parchment background (#F5F0E8)
- Dark navy primary typography (#1C2B4A)
- ONE warm accent color (choose whichever fits the topic best): \
  terracotta (#C4704F) for operational/business topics, \
  forest green (#2D5A27) for growth/strategy topics, \
  slate blue (#3D5A80) for data/technology topics
- Thin elegant serif font for the title (editorial, authoritative)
- Clean modern sans-serif for all body text and labels
- Minimal geometric decoration: thin horizontal rule lines, \
  small filled squares as bullet markers, subtle underlines
- No gradients, no shadows, no textures — flat and refined throughout

LAYOUT:
- 1080x1350px portrait
- Overline at top: small caps category label in accent color \
  (e.g., "PRODUCT STRATEGY" or "GTM INSIGHT")
- Large serif title below: 2-3 lines, fills 25-30% of height
- Thin rule line separating header from body
- 3-5 framework items in a clean numbered vertical list, well-spaced
- Each item: accent-colored number + bold sans-serif label (6-8 words) \
  + 1-2 sentence description in lighter weight
- Bottom: thin rule + italic key takeaway sentence
- Bottom right: "JW" monogram in a small circle, accent color border

CONTENT TO VISUALIZE:
{content}

OUTPUT:
- The title should read like a magazine headline, not a diagram label
- Maximum 3-4 uses of the accent color total — restraint is the point
- Generous line spacing and padding — white space signals quality
- The overall feel: authoritative, considered, worth saving and re-reading\
"""

_STYLES = [
    _LIGHT_LAVENDER_PROMPT,
    _DARK_NEON_PROMPT,
    _BOLD_TYPOGRAPHY_PROMPT,
    _QUADRANT_MATRIX_PROMPT,
    _ICEBERG_PROMPT,
    _EDITORIAL_MUTED_PROMPT,
]


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
