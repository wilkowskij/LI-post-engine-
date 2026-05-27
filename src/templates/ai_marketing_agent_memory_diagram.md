# AI Marketing Agent Memory System — Diagram Specification

Use this spec to generate the visual in Mermaid.ai, Gamma, Beautiful.ai,
or any AI design tool. Describes a four-section memory architecture diagram
for a marketing-specific AI agent.

---

## Prompt for Design Tool

```
Create a visual architecture diagram for an AI Marketing Agent Memory System.

CONCEPT: AI Marketing Agent Memory System
A diagram showing how a marketing AI agent captures, stores, consolidates,
and retrieves information to produce smarter, more consistent marketing output
over time.

LAYOUT: Four directional sections around a central memory store.
Left → Center → Bottom → Right flow. Not a linear step diagram —
this is an interconnected system architecture.

---

SECTION 1 — CAPTURE (left side)
Label: CAPTURE
What flows in from the outside world into the agent's memory.

Content Sources:
- URLs scraped
- PDFs ingested
- Social posts pulled
- Campaign briefs uploaded

---

SECTION 2 — MEMORY STORE (center, grid layout)
Label: MEMORY STORE
Four memory types arranged as a 2×2 grid:

Top-left:    EPISODIC     — Past campaigns run
Top-right:   SEMANTIC     — Brand voice, audience insights
Bottom-left: PROCEDURAL   — Proven workflows
Bottom-right: GRAPH       — Brand → Audience → Channel relationships

---

SECTION 3 — CONSOLIDATE (bottom)
Label: CONSOLIDATE
A horizontal processing pipeline beneath the memory store.

Steps (left to right):
Summarize → Compress → Decay → Learn

---

SECTION 4 — RETRIEVE & USE (right side)
Label: RETRIEVE & USE
What the agent produces when memory is queried.

Outputs:
- Brief Generation
- Copy Suggestions
- Smarter Targeting
- Cross-campaign Learning

---

WHY IT MATTERS (separate callout box, can sit in a corner or below)
Label: WHY IT MATTERS

✓ Remembers what worked last quarter
✓ Maintains brand voice consistency
✓ Reduces repetitive setup
✓ Scales across campaigns

---

FORMAT: Landscape or square orientation works. Professional, technical
but not overly complex. The MEMORY STORE grid should be the visual
centerpiece. Arrows should show directionality: input flows in from
the left (CAPTURE), consolidation happens below, retrieval exits to
the right (RETRIEVE & USE).

AUDIENCE: Senior marketers, marketing ops leaders, and product managers
evaluating AI agent architectures. Tone is clear and credible.
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
