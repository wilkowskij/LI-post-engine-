"""
Persona consistency tests — catch mismatches between TOPIC_CATEGORIES,
HASHTAG_MAP, and POST_FORMATS so a rename in one place surfaces immediately.
"""
import pytest
from src.agent.persona import (
    PERSONA_SYSTEM_PROMPT,
    POST_FORMATS,
    TOPIC_CATEGORIES,
    HASHTAG_MAP,
)


def test_topic_categories_non_empty():
    assert len(TOPIC_CATEGORIES) >= 10


def test_every_topic_has_hashtags():
    missing = [t for t in TOPIC_CATEGORIES if t not in HASHTAG_MAP]
    assert not missing, f"Topics missing from HASHTAG_MAP: {missing}"


def test_no_extra_hashtag_entries():
    extra = [k for k in HASHTAG_MAP if k not in TOPIC_CATEGORIES]
    assert not extra, f"HASHTAG_MAP has keys not in TOPIC_CATEGORIES: {extra}"


def test_all_hashtags_start_with_hash():
    for topic, tags in HASHTAG_MAP.items():
        for tag in tags:
            assert tag.startswith("#"), f"{topic!r} → {tag!r} doesn't start with #"


def test_post_formats_have_required_keys():
    required = {"description", "structure", "length"}
    for name, fmt in POST_FORMATS.items():
        missing = required - fmt.keys()
        assert not missing, f"Format {name!r} missing keys: {missing}"


def test_known_formats_present():
    expected = {"framework", "trend_prediction", "hot_take", "breakdown", "myth_busting", "data_insight"}
    assert expected == set(POST_FORMATS.keys()), (
        f"Format mismatch.\nExpected: {sorted(expected)}\nActual:   {sorted(POST_FORMATS.keys())}"
    )


def test_persona_prompt_non_empty():
    assert len(PERSONA_SYSTEM_PROMPT) > 200


def test_persona_prompt_no_banned_phrases():
    import re
    # Old format names must not appear as standalone words anywhere in the persona
    for phrase in ["trend_analysis"]:
        assert not re.search(r'\b' + re.escape(phrase) + r'\b', PERSONA_SYSTEM_PROMPT, re.IGNORECASE), (
            f"Old format name {phrase!r} still referenced in PERSONA_SYSTEM_PROMPT"
        )

    # Banned output phrases must not appear OUTSIDE of a "Never use" instruction block.
    # They may legitimately appear inside "Never use: X, Y" to tell Claude what to avoid.
    # Check that the persona is not *endorsing* them (i.e., they don't appear as advice).
    prompt_lower = PERSONA_SYSTEM_PROMPT.lower()
    for phrase in ["delve into", "revolutionize", "synergy"]:
        idx = prompt_lower.find(phrase)
        if idx == -1:
            continue  # not present at all — fine
        # It must appear within a "never/avoid/not" section (look back up to 300 chars)
        context = prompt_lower[max(0, idx - 300):idx]
        assert "never" in context or "avoid" in context or "not" in context, (
            f"Banned phrase {phrase!r} found in PERSONA_SYSTEM_PROMPT outside a 'never use' rule"
        )


def test_no_duplicate_topics():
    assert len(TOPIC_CATEGORIES) == len(set(TOPIC_CATEGORIES)), "Duplicate topics found"
