"""
HTML-based LinkedIn card renderer using Playwright.

Layout (1080 × 1350 portrait):
  ─ gold accent bar
  ─ hook text zone  (first sentence from the post)
  ─ diagram zone    (numbered step cards, space distributed evenly between them)
  ─ foundation row  (optional pills)
  ─ byline
"""
from pathlib import Path
from typing import Optional


BRAND = {
    "bg":      "#111827",
    "surface": "#1C2A3A",
    "deep":    "#0D1520",
    "gold":    "#C9A255",
    "white":   "#F8FAFC",
    "gray":    "#94A3B8",
    "muted":   "#64748B",
    "border":  "#1E2D3D",
}

CARD_W, CARD_H = 1080, 1350


def _extract_hook(post_text: str, max_chars: int = 160) -> str:
    lines = [ln.strip() for ln in post_text.strip().splitlines() if ln.strip()]
    first = lines[0] if lines else ""
    if len(first) <= max_chars:
        return first
    cut = first[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + " …"


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


_CSS = f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; text-decoration: none !important; }}
a {{ color: inherit !important; text-decoration: none !important; }}

body {{
  width: {CARD_W}px;
  height: {CARD_H}px;
  background: linear-gradient(175deg, #131f2e 0%, #0d1520 100%);
  font-family: 'Inter', 'Liberation Sans', 'DejaVu Sans', system-ui, sans-serif;
  color: {BRAND['white']};
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

.accent-bar {{
  height: 4px;
  background: linear-gradient(90deg, {BRAND['gold']} 0%, #e8c97a 50%, {BRAND['gold']} 100%);
  flex-shrink: 0;
}}

/* ── hook zone ── */
.hook-zone {{
  padding: 40px 56px 32px;
  flex-shrink: 0;
  border-bottom: 1px solid {BRAND['border']};
}}

.author-label {{
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: {BRAND['gold']};
  margin-bottom: 18px;
}}

.hook-text {{
  font-size: 32px;
  font-weight: 800;
  line-height: 1.22;
  color: {BRAND['white']};
  margin-bottom: 14px;
  letter-spacing: -0.02em;
}}

.hook-sub {{
  font-size: 16px;
  font-weight: 400;
  line-height: 1.55;
  color: {BRAND['gray']};
}}

/* ── diagram zone ── */
.diagram-zone {{
  flex: 1;
  padding: 28px 56px 20px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}}

.framework-label {{
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: {BRAND['gold']};
  margin-bottom: 20px;
  flex-shrink: 0;
}}

.steps-list {{
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
}}

/* ── step card ── */
.step-card {{
  display: flex;
  align-items: center;
  gap: 20px;
  background: {BRAND['surface']};
  border-radius: 10px;
  border-left: 4px solid {BRAND['gold']};
  padding: 22px 26px 22px 20px;
}}

.step-badge {{
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: rgba(201,162,85,0.10);
  border: 1.5px solid rgba(201,162,85,0.35);
  flex-shrink: 0;
}}

.step-num {{
  font-size: 17px;
  font-weight: 900;
  color: {BRAND['gold']};
  line-height: 1;
}}

.step-body {{
  flex: 1;
  min-width: 0;
}}

.step-label {{
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: {BRAND['white']};
  margin-bottom: 5px;
  line-height: 1.2;
}}

.step-desc {{
  font-size: 14px;
  color: {BRAND['gray']};
  line-height: 1.5;
}}

/* ── foundation ── */
.foundation {{
  padding: 0 56px;
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
  padding: 6px 16px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: {BRAND['gray']};
}}

/* ── byline ── */
.byline {{
  padding: 14px 56px 20px;
  text-align: right;
  font-size: 12px;
  color: {BRAND['muted']};
  letter-spacing: 0.05em;
  flex-shrink: 0;
}}
"""


def build_card_html(diagram: dict, post_text: str, author_name: str = "Jeff Wilkowski") -> str:
    hook     = _esc(_extract_hook(post_text))
    subtitle = _esc(diagram.get("subtitle", ""))
    title    = _esc(diagram.get("title", "Framework").upper())
    steps    = diagram.get("steps", [])[:6]
    f_title  = diagram.get("foundation_title", "")
    f_items  = (diagram.get("foundation_items") or [])[:8]

    steps_html = []
    for i, step in enumerate(steps):
        label = _esc(step.get("label", ""))
        desc  = _esc(step.get("description", ""))
        steps_html.append(f"""
        <div class="step-card">
          <div class="step-badge"><span class="step-num">{i + 1:02d}</span></div>
          <div class="step-body">
            <div class="step-label">{label}</div>
            <div class="step-desc">{desc}</div>
          </div>
        </div>""")

    foundation_html = ""
    if f_items:
        pills = "".join(f'<div class="pill">{_esc(it.upper())}</div>' for it in f_items)
        ft = f'<div class="foundation-title">{_esc(f_title.upper())}</div>' if f_title else ""
        foundation_html = f"""
  <div class="foundation">
    <div class="foundation-divider"></div>
    {ft}
    <div class="pills">{pills}</div>
  </div>"""

    subtitle_html = f'<div class="hook-sub">{subtitle}</div>' if subtitle else ""

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
    {subtitle_html}
  </div>

  <div class="diagram-zone">
    <div class="framework-label">{title}</div>
    <div class="steps-list">{''.join(steps_html)}
    </div>
  </div>

  {foundation_html}
  <div class="byline">{_esc(author_name)}</div>
</body>
</html>"""


def render_card(
    diagram: dict,
    post_text: str,
    author_name: str = "Jeff Wilkowski",
    output_path: Optional[Path] = None,
) -> Path:
    if output_path is None:
        from datetime import datetime
        out_dir = Path(__file__).parent.parent.parent / "output" / "images"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"card_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = build_card_html(diagram, post_text, author_name=author_name)

    _args = [
        "--disable-spell-checking",
        "--disable-features=SpellcheckAutoCorrect,SpellcheckAutoType,AutofillServerCommunication",
    ]

    def _find_browser() -> Optional[str]:
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
            browser = pw.chromium.launch(args=_args)
        except Exception:
            fb = _find_browser()
            if not fb:
                raise
            browser = pw.chromium.launch(executable_path=fb, args=_args)

        page = browser.new_page(viewport={"width": CARD_W, "height": CARD_H})
        page.set_content(html, wait_until="networkidle")
        page.evaluate("() => document.querySelectorAll('a').forEach(a => { a.style.color='inherit'; a.style.textDecoration='none'; })")
        page.screenshot(path=str(output_path), type="png",
                        clip={"x": 0, "y": 0, "width": CARD_W, "height": CARD_H})
        browser.close()

    return output_path
