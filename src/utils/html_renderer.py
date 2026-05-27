"""
HTML-based LinkedIn card renderer using Playwright.

Layout (1080 × 1350 portrait):
  ─ gold accent bar
  ─ hook text zone  (first 1-2 sentences from the post)
  ─ diagram zone    (numbered vertical flow with arrows)
  ─ foundation row  (optional pills)
  ─ byline
"""
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
* {{ margin: 0; padding: 0; box-sizing: border-box; text-decoration: none !important; }}
a, a:link, a:visited, a:hover, a:active {{ color: inherit !important; text-decoration: none !important; }}

body {{
  width: {CARD_W}px;
  height: {CARD_H}px;
  background: linear-gradient(160deg, #111827 0%, #0c1623 100%);
  font-family: 'Inter', 'Liberation Sans', 'DejaVu Sans', system-ui, sans-serif;
  color: {BRAND['white']};
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}}

body::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 500px;
  background: radial-gradient(ellipse at 20% 0%, rgba(201,162,85,0.06) 0%, transparent 65%);
  pointer-events: none;
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
  padding: 24px 52px 16px;
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
  margin-bottom: 14px;
  flex-shrink: 0;
}}

.steps-list {{
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0;
}}

.step-card {{
  background: {BRAND['surface']};
  border-radius: 8px;
  border-left: 4px solid {BRAND['gold']};
  padding: 0 22px 0 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-height: 72px;
}}

.step-num-wrap {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: rgba(201, 162, 85, 0.12);
  border: 1.5px solid rgba(201, 162, 85, 0.40);
  flex-shrink: 0;
}}

.step-num {{
  font-size: 18px;
  font-weight: 900;
  color: {BRAND['gold']};
  line-height: 1;
}}

.step-body {{
  flex: 1;
  min-width: 0;
}}

.step-label {{
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: {BRAND['white']};
  margin-bottom: 6px;
  line-height: 1.2;
}}

.step-desc {{
  font-size: 15px;
  font-weight: 400;
  color: {BRAND['gray']};
  line-height: 1.5;
}}

.step-arrow {{
  text-align: center;
  color: {BRAND['gold']};
  font-size: 18px;
  line-height: 1;
  opacity: 0.5;
  padding: 3px 0;
  flex-shrink: 0;
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

    steps_html = []
    for i, step in enumerate(steps):
        if i > 0:
            steps_html.append('<div class="step-arrow">↓</div>')
        label = _esc(step.get("label", ""))
        desc = _esc(step.get("description", ""))
        steps_html.append(f"""
        <div class="step-card">
          <div class="step-num-wrap"><div class="step-num">{i + 1:02d}</div></div>
          <div class="step-body">
            <div class="step-label">{label}</div>
            <div class="step-desc">{desc}</div>
          </div>
        </div>""")

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
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="format-detection" content="telephone=no,date=no,address=no,email=no,url=no">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head>
<body spellcheck="false">
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

    _launch_args = [
        "--disable-spell-checking",
        "--disable-features=SpellcheckAutoCorrect,SpellcheckAutoType,AutofillServerCommunication",
    ]

    def _find_headless_shell() -> Optional[str]:
        import os
        base = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
        if not base.exists():
            return None
        for name in ("headless_shell", "chrome-headless-shell", "chrome"):
            for binary in sorted(base.rglob(name), reverse=True):
                if binary.is_file() and os.access(binary, os.X_OK):
                    return str(binary)
        return None

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(args=_launch_args)
        except Exception:
            fallback = _find_headless_shell()
            if not fallback:
                raise
            browser = pw.chromium.launch(executable_path=fallback, args=_launch_args)

        page = browser.new_page(viewport={"width": CARD_W, "height": CARD_H})
        page.set_content(html, wait_until="networkidle")
        # Strip any auto-detected link styling Chromium applies to text
        page.evaluate("""() => {
            document.querySelectorAll('a').forEach(a => {
                a.style.color = 'inherit';
                a.style.textDecoration = 'none';
            });
        }""")
        page.screenshot(path=str(output_path), type="png", clip={
            "x": 0, "y": 0, "width": CARD_W, "height": CARD_H,
        })
        browser.close()

    return output_path
