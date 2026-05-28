# LinkedIn Post Engine — Claude Code Session Guide

Use this document to onboard a new Claude Code session to this project.
It covers the full architecture, key files, pipeline flow, and exactly
where to make changes to alter the research style or content strategy.

---

## What This Project Does

Fully autonomous LinkedIn content engine for **Jeff Wilkowski** — Senior PM
in the SaaS/PLG/DaaS space. Runs on a cron schedule (Tue/Wed/Thu 9am EST),
researches trending topics, generates posts in Jeff's voice, produces an
AI-generated infographic image, and queues everything to Buffer automatically.

**Full pipeline:**
```
Cron trigger → Research (Tavily) → Post generation (Claude) →
Diagram spec → OpenAI image (gpt-image-1 / DALL-E 3) →
Cloudinary upload → Buffer queue
```

---

## Repository Structure

```
LI-post-engine-/
├── main.py                          # CLI entry point (generate, schedule, run-daily, etc.)
├── scheduler.py                     # Local cron scheduler (alternative to GitHub Actions)
├── requirements.txt
├── .env                             # Local secrets (never committed)
│
├── src/
│   ├── agent/
│   │   ├── persona.py               # ★ Jeff's voice, POST_FORMATS, HASHTAG_MAP, TOPIC_CATEGORIES
│   │   ├── writer.py                # ★ Post generation via Claude API
│   │   └── researcher.py            # ★ Research pipeline (Tavily + Claude brief)
│   │
│   ├── integrations/
│   │   ├── buffer_client.py         # Buffer GraphQL API — schedule posts
│   │   ├── cloudinary_client.py     # Cloudinary — image hosting
│   │   └── openai_image_gen.py      # ★ OpenAI image generation (gpt-image-1 / DALL-E 3)
│   │
│   ├── utils/
│   │   ├── image_gen.py             # Image renderer priority chain (OpenAI → Playwright → Pillow)
│   │   ├── html_renderer.py         # Playwright HTML→PNG fallback renderer (dark card style)
│   │   ├── content_calendar.py      # Topic rotation and posting day logic
│   │   ├── storage.py               # Save/load post JSON drafts
│   │   └── display.py               # Rich terminal output
│   │
│   └── templates/
│       ├── mermaid_diagram_prompt.md        # Master prompt for external design tools
│       └── ai_marketing_agent_memory_diagram.md  # AI memory system diagram spec
│
├── output/
│   ├── posts/          # Saved post drafts as JSON
│   └── images/         # Generated card images
│
└── .github/workflows/
    ├── daily-post.yml       # ★ Main autonomous workflow (cron + manual trigger)
    └── schedule-post.yml    # Manual workflow to push a specific draft to Buffer
```

---

## Key Files — What Each One Controls

### `src/agent/persona.py`
Controls **who Jeff is** and **what he writes about**.

- `PERSONA_SYSTEM_PROMPT` — Jeff's full voice and tone instructions sent to Claude
- `POST_FORMATS` — 7 post formats with structure and length guidance:
  `visual_framework`, `framework`, `trend_prediction`, `hot_take`,
  `breakdown`, `myth_busting`, `data_insight`
- `TOPIC_CATEGORIES` — 15 topics Jeff rotates through (PLG, GTM, DaaS, AI, etc.)
- `HASHTAG_MAP` — 8 hashtags per topic; writer picks 5-8 per post

### `src/agent/researcher.py`
Controls **how topics are researched**.

- `research_trending_topics(category)` — calls Tavily API to find current signals
- `build_research_brief(research, client)` — passes findings to Claude to synthesize
  into a structured brief that the writer uses
- **This is the primary file to change if you want a different research style**

### `src/agent/writer.py`
Controls **how posts are written**.

- `generate_post()` — main function, builds the user prompt and calls Claude
- `_VISUAL_FRAMEWORK_SUFFIX` — JSON schema instructions for visual_framework posts
- `generate_diagram_spec()` — generates diagram spec for non-visual posts
- Prompt line to change hashtag count: `"HASHTAGS — pick 5-8..."`

### `src/integrations/openai_image_gen.py`
Controls **how the image is generated**.

- `_BASE_PROMPT` — the full style prompt sent to OpenAI (light lavender/white
  infographic style, purple/blue/yellow/teal palette, hand-drawn icons,
  numbered pill badges, robot mascot, JW initials badge)
- `format_image_prompt(diagram, post_text)` — fills the CONTENT TO VISUALIZE
  section from the diagram spec
- Tries `gpt-image-1` first (ChatGPT's model), falls back to `dall-e-3`

### `.github/workflows/daily-post.yml`
Controls **when and how the pipeline runs**.

- Cron: `0 14 * * 2,3,4` = 9am EST, Tue/Wed/Thu
- Always runs `--auto-schedule` (fully autonomous, no review step)
- Required secrets: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- Optional secrets: `CLOUDINARY_*`, `BUFFER_ACCESS_TOKEN`, `TAVILY_API_KEY`
- Includes an explicit OpenAI test step before the main run

---

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...        # Claude API — post generation
OPENAI_API_KEY=sk-proj-...          # Image generation (gpt-image-1 / DALL-E 3)

# Image hosting
CLOUDINARY_CLOUD_NAME=drum3eekm
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

# Scheduling
BUFFER_ACCESS_TOKEN=...
BUFFER_PROFILE_IDS=...              # LinkedIn channel ID from Buffer

# Research
TAVILY_API_KEY=tvly-...             # Web research — falls back to Claude knowledge if missing

# Post identity
AUTHOR_NAME=Jeff Wilkowski
AUTHOR_HEADLINE=Senior Product Manager | SaaS & Data-as-a-Service
POST_SCHEDULE_TIME=08:00
POST_TIMEZONE=America/Chicago
POSTING_DAYS=Mon,Wed,Fri
```

---

## How to Change the Research Style

The research pipeline lives in `src/agent/researcher.py`. To change how
topics are researched, modify one or both of these functions:

### 1. Change what Tavily searches for
```python
def research_trending_topics(category: str) -> dict:
    # Tavily is called here — modify the search query construction
    # to target different sources, time ranges, or content types
```

### 2. Change how the brief is synthesized
```python
def build_research_brief(research: dict, client) -> str:
    # Claude synthesizes Tavily results into a brief here
    # Change the system prompt or user prompt to alter the brief format
    # e.g. focus on contrarian angles, case studies, data signals, etc.
```

### 3. Change the topics researched
In `src/agent/persona.py`, edit `TOPIC_CATEGORIES` to add, remove, or
replace the 15 topic areas. The content calendar rotates through these
automatically, weighting topics Jeff hasn't covered recently.

### 4. Change the post formats
In `src/agent/persona.py`, edit `POST_FORMATS`. Each format has:
- `description` — what it is
- `structure` — how it should flow
- `length` — target word count

---

## How to Change the Image Style

The image prompt is in `src/integrations/openai_image_gen.py` in `_BASE_PROMPT`.

Current style: light lavender/white background, purple/blue/yellow/teal
palette, hand-drawn icons, numbered pill badges, robot mascot, JW badge.

To change it: edit `_BASE_PROMPT` — the STYLE, LAYOUT, and OUTPUT sections.
The CONTENT TO VISUALIZE section is always auto-filled from the diagram spec.

The master prompt template (for use in external tools like Mermaid.ai, Gamma,
Beautiful.ai) is saved at `src/templates/mermaid_diagram_prompt.md`.

---

## CLI Commands

```bash
# Generate a post (research + write)
python main.py generate --format visual_framework --topic "PLG tactics"

# Generate with a specific angle
python main.py generate --angle "focus on AI agent implications"

# Generate 3 variants
python main.py generate --variants 3

# Run the full daily pipeline manually
python main.py run-daily --auto-schedule

# Generate only (no Buffer push)
python main.py run-daily --generate-only

# Refine an existing draft
python main.py refine --feedback "make it more contrarian"

# Push a specific draft to Buffer
python main.py schedule --file output/posts/2026-05-27_...json --yes

# Check Buffer queue
python main.py queue

# List saved posts
python main.py list

# Show upcoming content calendar
python main.py calendar

# Verify all integrations
python main.py setup
```

---

## GitHub Actions Secrets Required

Add these under **Settings → Secrets and variables → Actions**:

| Secret | Required | Purpose |
|--------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes | Claude post generation |
| `OPENAI_API_KEY` | Yes | Image generation |
| `CLOUDINARY_CLOUD_NAME` | Yes | Image hosting |
| `CLOUDINARY_API_KEY` | Yes | Image hosting |
| `CLOUDINARY_API_SECRET` | Yes | Image hosting |
| `BUFFER_ACCESS_TOKEN` | Yes | Post scheduling |
| `BUFFER_PROFILE_IDS` | Yes | LinkedIn channel ID |
| `TAVILY_API_KEY` | Optional | Web research |
| `AUTHOR_NAME` | Optional | Byline on images |

---

## Branches

- `main` — production branch, CI runs from here
- `claude/focused-heisenberg-NWocV` — dev branch for this session

All changes should be committed to the dev branch and merged to `main`
via `git push origin <dev-branch>:main`.

---

## Post Output Format

Each generated post is saved as JSON in `output/posts/`:

```json
{
  "text": "The full LinkedIn post text...",
  "topic": "Product-led growth tactics",
  "format": "visual_framework",
  "hashtags": ["#PLG", "#ProductStrategy", ...],
  "diagram": {
    "title": "FRAMEWORK NAME",
    "subtitle": "One line description",
    "steps": [
      {"label": "STEP LABEL", "description": "One sentence description"},
      ...
    ],
    "foundation_title": "OPTIONAL FOUNDATION HEADER",
    "foundation_items": ["ITEM 1", "ITEM 2", ...]
  },
  "word_count": 172,
  "char_count": 891,
  "status": "draft",
  "saved_at": "2026-05-27T22:00:00",
  "image_url": "https://res.cloudinary.com/..."
}
```
