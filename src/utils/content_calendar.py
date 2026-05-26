"""
Smart content rotation — avoids repeating topics/formats, respects posting schedule.
"""
import os
import random
from datetime import datetime, timedelta
from typing import Optional

from src.agent.persona import TOPIC_CATEGORIES, POST_FORMATS
from src.utils.storage import list_posts

DAY_MAP = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
DAY_NAMES = {v: k for k, v in DAY_MAP.items()}


def get_posting_days() -> list[int]:
    """Weekday numbers to post on. Reads POSTING_DAYS env var, default Mon-Fri."""
    raw = os.environ.get("POSTING_DAYS", "Mon,Tue,Wed,Thu,Fri")
    return [DAY_MAP[d.strip()] for d in raw.split(",") if d.strip() in DAY_MAP]


def is_posting_day(dt: Optional[datetime] = None) -> bool:
    dt = dt or datetime.now()
    return dt.weekday() in get_posting_days()


def next_posting_day(from_dt: Optional[datetime] = None) -> datetime:
    """Return the next scheduled posting day (including today if applicable)."""
    dt = from_dt or datetime.now()
    posting_days = get_posting_days()
    for i in range(7):
        candidate = dt + timedelta(days=i)
        if candidate.weekday() in posting_days:
            return candidate
    return dt


def _recent_posts(days: int) -> list[dict]:
    cutoff = datetime.now() - timedelta(days=days)
    posts = []
    for p in list_posts(limit=60):
        try:
            if datetime.fromisoformat(p.get("saved_at", "")) > cutoff:
                posts.append(p)
        except Exception:
            continue
    return posts


def get_recent_topics(days: int = 7) -> list[str]:
    return [p.get("topic", "") for p in _recent_posts(days)]


def get_recent_formats(days: int = 3) -> list[str]:
    return [p.get("format", "") for p in _recent_posts(days)]


def pick_todays_topic() -> str:
    """Pick a topic not used in the last 7 days. Falls back to least-recently-used."""
    recent = set(get_recent_topics(7))
    fresh = [t for t in TOPIC_CATEGORIES if t not in recent]
    if fresh:
        return random.choice(fresh)

    # All topics used recently — pick the oldest one
    all_posts = list_posts(limit=100)
    last_used: dict[str, str] = {}
    for p in reversed(all_posts):
        t = p.get("topic", "")
        if t:
            last_used[t] = p.get("saved_at", "")
    return min(TOPIC_CATEGORIES, key=lambda t: last_used.get(t, "1900-01-01"))


def pick_todays_formats(count: int = 3) -> list[str]:
    """Pick formats not used in the last 3 days for variety."""
    recent = set(get_recent_formats(3))
    all_fmts = list(POST_FORMATS.keys())
    fresh = [f for f in all_fmts if f not in recent]
    rest = [f for f in all_fmts if f in recent]
    random.shuffle(fresh)
    random.shuffle(rest)
    combined = (fresh + rest)[:count]
    return combined


def get_weekly_summary() -> dict:
    """Stats on posts from the last 7 days."""
    posts = _recent_posts(7)
    return {
        "total": len(posts),
        "scheduled": sum(1 for p in posts if p.get("status") == "scheduled"),
        "drafts": sum(1 for p in posts if p.get("status") == "draft"),
        "topics_used": sorted({p.get("topic", "") for p in posts if p.get("topic")}),
        "formats_used": sorted({p.get("format", "") for p in posts if p.get("format")}),
        "posts": posts,
    }


def get_upcoming_plan(days: int = 7) -> list[dict]:
    """
    Build a suggested content plan for the next N calendar days.
    Returns one entry per posting day with a suggested topic.
    """
    posting_days = get_posting_days()
    recent_topics = list(get_recent_topics(7))
    used_in_plan: list[str] = []
    plan = []

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(days):
        day = today + timedelta(days=i)
        if day.weekday() not in posting_days:
            continue

        # Pick a topic not recently used and not already in this plan
        excluded = set(recent_topics) | set(used_in_plan)
        available = [t for t in TOPIC_CATEGORIES if t not in excluded]
        if not available:
            available = [t for t in TOPIC_CATEGORIES if t not in used_in_plan] or TOPIC_CATEGORIES
        topic = random.choice(available)
        used_in_plan.append(topic)

        plan.append({
            "date": day.strftime("%Y-%m-%d"),
            "weekday": DAY_NAMES.get(day.weekday(), ""),
            "topic": topic,
            "is_today": i == 0,
        })

    return plan
