# AI Marketing Agent Memory System — Diagram Specification

Use this spec to generate the visual in Mermaid.ai, Gamma, Beautiful.ai,
or any AI design tool. Describes a four-section memory architecture diagram
for a marketing-specific AI agent.

---

## Prompt for Design Tool

```
Create a professional explainer infographic in the style of a LinkedIn
thought-leadership visual with the following specs:

STYLE:
- Light lavender/white background (#f5f0ff or white)
- Primary colors: purple (#7B5EA7), blue (#4A90D9), yellow (#F5C842),
  teal (#4ECDC4)
- Hand-drawn/sketch-style icons (not photorealistic)
- Rounded rectangle boxes with soft drop shadows
- Bold sans-serif title (large, dark navy)
- Subtitle in lighter italic or regular weight
- Dashed and solid arrows showing flow/direction
- Small emoji-style or outline icons inside each box
- Numbered section labels in colored pill/badge shapes

LAYOUT:
- 1080x1350px portrait for LinkedIn
- 4-section flow: [Left column] → [Center grid] → [Right column]
- Bottom strip for sub-process steps (horizontal icon chain)
- "Why It Matters" callout box with checklist bullets

CONTENT TO VISUALIZE:

CONCEPT: AI Marketing Agent Memory System
How a marketing AI agent captures, stores, consolidates, and retrieves
information to produce smarter, more consistent marketing output over time.

SECTION 1 (left) — CAPTURE:
Content flowing into the agent:
- URLs scraped
- PDFs ingested
- Social posts pulled
- Campaign briefs uploaded

SECTION 2 (center grid) — MEMORY STORE (2×2 grid):
Top-left:    EPISODIC     — Past campaigns run
Top-right:   SEMANTIC     — Brand voice, audience insights
Bottom-left: PROCEDURAL   — Proven workflows
Bottom-right: GRAPH       — Brand → Audience → Channel relationships

SECTION 3 (bottom strip) — CONSOLIDATE PIPELINE:
Summarize → Compress → Decay → Learn

SECTION 4 (right) — RETRIEVE & USE:
- Brief Generation
- Copy Suggestions
- Smarter Targeting
- Cross-campaign Learning

WHY IT MATTERS (callout box):
✓ Remembers what worked last quarter
✓ Maintains brand voice consistency
✓ Reduces repetitive setup
✓ Scales across campaigns

OUTPUT:
- Label each section with numbers (1, 2, 3, 4)
- Use short 2-4 word headers per box
- Add 1-line subtitles under each header
- Include a small robot/AI mascot character in bottom-left corner
- Add creator initials "JW" badge (circle) in top-left
```

---

## Raw Spec (for programmatic use or internal reference)

```json
{
  "title": "AI MARKETING AGENT MEMORY SYSTEM",
  "sections": {
    "capture": {
      "position": "left",
      "label": "CAPTURE",
      "items": [
        "URLs scraped",
        "PDFs ingested",
        "Social posts pulled",
        "Campaign briefs uploaded"
      ]
    },
    "memory_store": {
      "position": "center",
      "label": "MEMORY STORE",
      "layout": "2x2 grid",
      "cells": [
        { "type": "EPISODIC",   "description": "Past campaigns run" },
        { "type": "SEMANTIC",   "description": "Brand voice, audience insights" },
        { "type": "PROCEDURAL", "description": "Proven workflows" },
        { "type": "GRAPH",      "description": "Brand → Audience → Channel relationships" }
      ]
    },
    "consolidate": {
      "position": "bottom",
      "label": "CONSOLIDATE",
      "pipeline": ["Summarize", "Compress", "Decay", "Learn"]
    },
    "retrieve": {
      "position": "right",
      "label": "RETRIEVE & USE",
      "outputs": [
        "Brief Generation",
        "Copy Suggestions",
        "Smarter Targeting",
        "Cross-campaign Learning"
      ]
    }
  },
  "callout": {
    "label": "WHY IT MATTERS",
    "points": [
      "Remembers what worked last quarter",
      "Maintains brand voice consistency",
      "Reduces repetitive setup",
      "Scales across campaigns"
    ]
  }
}
```
