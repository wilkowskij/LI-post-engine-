"""
Content calendar tests — rotation logic, posting schedule, topic/format recency.
"""
import os
import pytest
from unittest.mock import patch
from datetime import datetime

from src.utils.content_calendar import (
    get_posting_days,
    is_posting_day,
    next_posting_day,
    pick_todays_topic,
    pick_todays_formats,
    get_upcoming_plan,
    DAY_MAP,
    DAY_NAMES,
)
from src.agent.persona import TOPIC_CATEGORIES, POST_FORMATS


# ── posting schedule ────────────────────────────────────────────────────────

def test_default_posting_days():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("POSTING_DAYS", None)
        days = get_posting_days()
    assert days == [DAY_MAP["Mon"], DAY_MAP["Wed"], DAY_MAP["Fri"]]


def test_custom_posting_days():
    with patch.dict(os.environ, {"POSTING_DAYS": "Tue,Thu"}):
        days = get_posting_days()
    assert days == [DAY_MAP["Tue"], DAY_MAP["Thu"]]


def test_is_posting_day_true():
    monday = datetime(2026, 6, 1)  # a Monday
    with patch.dict(os.environ, {"POSTING_DAYS": "Mon,Wed,Fri"}):
        assert is_posting_day(monday) is True


def test_is_posting_day_false():
    tuesday = datetime(2026, 6, 2)  # a Tuesday
    with patch.dict(os.environ, {"POSTING_DAYS": "Mon,Wed,Fri"}):
        assert is_posting_day(tuesday) is False


def test_next_posting_day_today():
    monday = datetime(2026, 6, 1)
    with patch.dict(os.environ, {"POSTING_DAYS": "Mon,Wed,Fri"}):
        result = next_posting_day(monday)
    assert result.weekday() == DAY_MAP["Mon"]


def test_next_posting_day_skips_non_posting():
    tuesday = datetime(2026, 6, 2)
    with patch.dict(os.environ, {"POSTING_DAYS": "Mon,Wed,Fri"}):
        result = next_posting_day(tuesday)
    assert result.weekday() == DAY_MAP["Wed"]


# ── topic rotation ───────────────────────────────────────────────────────────

def test_pick_topic_returns_valid():
    with patch("src.utils.content_calendar.get_recent_topics", return_value=[]):
        topic = pick_todays_topic()
    assert topic in TOPIC_CATEGORIES


def test_pick_topic_avoids_recent():
    # Mark all but one topic as recently used
    all_but_last = TOPIC_CATEGORIES[:-1]
    with patch("src.utils.content_calendar.get_recent_topics", return_value=all_but_last):
        topic = pick_todays_topic()
    assert topic == TOPIC_CATEGORIES[-1]


def test_pick_topic_falls_back_when_all_recent():
    # When every topic is recent, falls back to least-recently-used
    with patch("src.utils.content_calendar.get_recent_topics", return_value=TOPIC_CATEGORIES):
        with patch("src.utils.storage.list_posts", return_value=[]):
            topic = pick_todays_topic()
    assert topic in TOPIC_CATEGORIES


# ── format rotation ──────────────────────────────────────────────────────────

def test_pick_formats_returns_valid():
    with patch("src.utils.content_calendar.get_recent_formats", return_value=[]):
        formats = pick_todays_formats(3)
    for f in formats:
        assert f in POST_FORMATS, f"Unknown format returned: {f!r}"


def test_pick_formats_no_duplicates():
    with patch("src.utils.content_calendar.get_recent_formats", return_value=[]):
        formats = pick_todays_formats(3)
    assert len(formats) == len(set(formats))


def test_pick_formats_prefers_trend_prediction():
    # trend_prediction should appear in top picks when not recently used
    with patch("src.utils.content_calendar.get_recent_formats", return_value=[]):
        formats = pick_todays_formats(3)
    assert "trend_prediction" in formats or "framework" in formats


def test_pick_formats_count():
    with patch("src.utils.content_calendar.get_recent_formats", return_value=[]):
        for n in [1, 2, 3]:
            formats = pick_todays_formats(n)
            assert len(formats) == n


# ── upcoming plan ────────────────────────────────────────────────────────────

def test_upcoming_plan_only_posting_days():
    with patch.dict(os.environ, {"POSTING_DAYS": "Mon,Wed,Fri"}):
        plan = get_upcoming_plan(14)
    for entry in plan:
        dt = datetime.strptime(entry["date"], "%Y-%m-%d")
        assert dt.weekday() in [DAY_MAP["Mon"], DAY_MAP["Wed"], DAY_MAP["Fri"]]


def test_upcoming_plan_unique_topics():
    with patch("src.utils.content_calendar.get_recent_topics", return_value=[]):
        plan = get_upcoming_plan(14)
    topics = [e["topic"] for e in plan]
    assert len(topics) == len(set(topics)), "Duplicate topics in upcoming plan"


def test_upcoming_plan_entries_have_required_keys():
    plan = get_upcoming_plan(7)
    for entry in plan:
        for key in ("date", "weekday", "topic", "is_today"):
            assert key in entry, f"Entry missing key {key!r}"
