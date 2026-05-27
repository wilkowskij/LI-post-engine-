"""
HTML-based LinkedIn card renderer using Playwright.

Layout (1080 × 1350 portrait):
  ─ gold accent bar
  ─ hook text zone  (first 1-2 sentences from the post)
  ─ diagram zone    (numbered vertical flow with arrows)
  ─ foundation row  (optional pills)
  ─ byline
"""
import re
from pathlib import Path
from typing import Optional


# ── brand palette ────────────────────────────────────────────────────────────
BRAND = {
    "bg":      "#111827",
    "surface": "#1C2A3A",
    "deep":    "#0D1520",
    "gold":    "#C9A255",
    "white":   "#F8FAFC",
    "gray":    "#94A3B8",
    "muted":   "#64748B",
    "border":  "#1F2D3D",
}

CARD_W, CARD_H = 1080, 1350


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_hook(post_text: str, max_chars: int = 180) -> str:
    """Pull the first sentence / opening line from the post."""
    lines = [ln.strip() for ln in post_text.strip().splitlines() if ln.strip()]
    first = lines[0] if lines else ""
    if len(first) <= max_chars:
        return first
    # Truncate at a word boundary
    cut = first[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + " …"


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


# ── HTML template ─────────────────────────────────────────────────────────────

_CSS = f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  width: {CARD_W}px;
  height: {CARD_H}px;
  background: {BRAND['bg']};
  font-family: 'Inter', 'Liberation Sans', 'DejaVu Sans', system-ui, sans-serif;
  color: {BRAND['white']};
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

/* ── top accent bar ── */
.accent-bar {{
  height: 5px;
  background: linear-gradient(90deg, {BRAND['gold']}, #E8C97A, {BRAND['gold']});
  flex-shrink: 0;
}}

/* ── hook zone ── */
.hook-zone {{
  padding: 36px 52px 28px;
  flex-shrink: 0;
  border-bottom: 1px solid {BRAND['border']};
}}

.author-label {{
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: {BRAND['gold']};
  margin-bottom: 16px;
}}

.hook-text {{
  font-size: 30px;
  font-weight: 800;
  line-height: 1.25;
  color: {BRAND['white']};
  margin-bottom: 14px;
  letter-spacing: -0.01em;
}}

.hook-sub {{
  font-size: 16px;
  font-weight: 400;
  line-height: 1.5;
  color: {BRAND['gray']};
}}

/* ── diagram zone ── */
.diagram-zone {{
  flex: 1;
  padding: 24px 52px 20px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}}

.framework-label {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: {BRAND['gold']};
  margin-bottom: 16px;
}}

.steps-list {{
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 0;
}}

.step-card {{
  background: {BRAND['surface']};
  border-radius: 8px;
  border-left: 4px solid {BRAND['gold']};
  padding: 14px 20px 14px 18px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  flex: 1;
}}

.step-num {{
  font-size: 22px;
  font-weight: 900;
  color: {BRAND['gold']};
  min-width: 34px;
  line-height: 1;
  padding-top: 2px;
}}

.step-body {{
  flex: 1;
  min-width: 0;
}}

.step-label {{
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: {BRAND['white']};
  margin-bottom: 4px;
  line-height: 1.3;
}}

.step-desc {{
  font-size: 13px;
  font-weight: 400;
  color: {BRAND['gray']};
  line-height: 1.45;
}}

.step-arrow {{
  text-align: center;
  color: {BRAND['gold']};
  font-size: 16px;
  padding: 3px 0;
  flex-shrink: 0;
  opacity: 0.7;
}}

/* ── foundation row ── */
.foundation {{
  padding: 16px 52px 0;
  flex-shrink: 0;
}}

.foundation-divider {{
  height: 1px;
  background: {BRAND['border']};
  margin-bottom: 14px;
}}

.foundation-title {{
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: {BRAND['muted']};
  text-align: center;
  margin-bottom: 10px;
}}

.pills {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}}

.pill {{
  background: {BRAND['deep']};
  border-top: 2px solid {BRAND['gold']};
  border-radius: 4px;
  padding: 5px 14px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: {BRAND['gray']};
}}

/* ── byline ── */
.byline {{
  padding: 12px 52px 18px;
  text-align: right;
  font-size: 12px;
  font-weight: 500;
  color: {BRAND['muted']};
  letter-spacing: 0.04em;
  flex-shrink: 0;
}}
"""


def build_card_html(
    diagram: dict,
    post_text: str,
    author_name: str = "Jeff Wilkowski",
) -> str:
    hook = _esc(_extract_hook(post_text))
    subtitle = _esc(diagram.get("subtitle", ""))
    title = _esc(diagram.get("title", "The Framework").upper())
    steps = diagram.get("steps", [])[:6]
    foundation_title = diagram.get("foundation_title", "")
    foundation_items = (diagram.get("foundation_items") or [])[:8]

    # Build step cards HTML
    steps_html = []
    for i, step in enumerate(steps):
        if i > 0:
            steps_html.append('<div class="step-arrow">↓</div>')
        label = _esc(step.get("label", ""))
        desc = _esc(step.get("description", ""))
        steps_html.append(f"""
        <div class="step-card">
          <div class="step-num">{i + 1:02d}</div>
          <div class="step-body">
            <div class="step-label">{label}</div>
            <div class="step-desc">{desc}</div>
          </div>
        </div>""")

    # Foundation row HTML
    foundation_html = ""
    if foundation_items:
        pills = "".join(
            f'<div class="pill">{_esc(item.upper())}</div>'
            for item in foundation_items
        )
        ft = f'<div class="foundation-title">{_esc(foundation_title.upper())}</div>' if foundation_title else ""
        foundation_html = f"""
    <div class="foundation">
      <div class="foundation-divider"></div>
      {ft}
      <div class="pills">{pills}</div>
    </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head>
<body>
  <div class="accent-bar"></div>

  <div class="hook-zone">
    <div class="author-label">{_esc(author_name)}</div>
    <div class="hook-text">{hook}</div>
    {'<div class="hook-sub">' + subtitle + '</div>' if subtitle else ''}
  </div>

  <div class="diagram-zone">
    <div class="framework-label">{title}</div>
    <div class="steps-list">
      {''.join(steps_html)}
    </div>
  </div>

  {foundation_html}

  <div class="byline">{_esc(author_name)}</div>
</body>
</html>"""


# ── Playwright screenshot ──────────────────────────────────────────────────────

def render_card(
    diagram: dict,
    post_text: str,
    author_name: str = "Jeff Wilkowski",
    output_path: Optional[Path] = None,
) -> Path:
    """Render the LinkedIn card to a PNG using Playwright."""
    if output_path is None:
        from datetime import datetime
        OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "images"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"card_{stamp}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = build_card_html(diagram, post_text, author_name=author_name)

    from playwright.sync_api import sync_playwright

    def _find_headless_shell() -> Optional[str]:
        """Scan PLAYWRIGHT_BROWSERS_PATH for a usable headless-shell binary."""
        import os
        base = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
        if not base.exists():
            return None
        # Prefer headless_shell over full chrome (old headless removed in Chromium 112+)
        for name in ("headless_shell", "chrome-headless-shell", "chrome"):
            for binary in sorted(base.rglob(name), reverse=True):
                if binary.is_file() and os.access(binary, os.X_OK):
                    return str(binary)
        return None

    with sync_playwright() as pw:
        launch_kwargs: dict = {}
        try:
            browser = pw.chromium.launch(**launch_kwargs)
        except Exception:
            # Binary version mismatch — try auto-detected path
            fallback = _find_headless_shell()
            if not fallback:
                raise
            browser = pw.chromium.launch(executable_path=fallback)

        page = browser.new_page(viewport={"width": CARD_W, "height": CARD_H})
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=str(output_path), type="png", clip={
            "x": 0, "y": 0, "width": CARD_W, "height": CARD_H,
        })
        browser.close()

    return output_path
