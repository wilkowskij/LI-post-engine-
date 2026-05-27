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
    """Weekday numbers to post on. Reads POSTING_DAYS env var, default Mon/Wed/Fri."""
    raw = os.environ.get("POSTING_DAYS", "Mon,Wed,Fri")
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
    """Pick a topic not used in the last 14 days (5-6 posts at 3x/week). Falls back to least-recently-used."""
    recent = set(get_recent_topics(14))
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
    """
    Pick formats not used in the last 7 days (2 posts at 3x/week).
    trend_prediction and framework are preferred — they match the educator/trends voice.
    """
    recent = set(get_recent_formats(7))
    # Preferred formats get double weight
    preferred = ["visual_framework", "trend_prediction", "framework", "hot_take"]
    others = ["breakdown", "myth_busting", "data_insight"]
    pool = [f for f in preferred if f not in recent] * 2 + \
           [f for f in others if f not in recent] + \
           [f for f in (preferred + others) if f in recent]
    seen: list[str] = []
    result: list[str] = []
    for f in pool:
        if f not in seen:
            seen.append(f)
            result.append(f)
        if len(result) == count:
            break
    return result


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
