"""
Storage tests — save, load, list, and status-update round-trips.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from src.utils.storage import save_post, load_post, list_posts, update_post_status

SAMPLE_POST = {
    "text": "Test post content for unit testing.",
    "topic": "Product-led growth tactics",
    "format": "trend_prediction",
    "hashtags": ["#PLG", "#SaaS"],
    "word_count": 6,
    "char_count": 35,
}


@pytest.fixture()
def tmp_output(tmp_path, monkeypatch):
    """Redirect OUTPUT_DIR to a temp directory for every test."""
    import src.utils.storage as storage_mod
    monkeypatch.setattr(storage_mod, "OUTPUT_DIR", tmp_path)
    return tmp_path


def test_save_post_creates_file(tmp_output):
    path = save_post(SAMPLE_POST.copy())
    assert path.exists()
    assert path.suffix == ".json"


def test_save_post_content(tmp_output):
    path = save_post(SAMPLE_POST.copy())
    data = json.loads(path.read_text())
    assert data["text"] == SAMPLE_POST["text"]
    assert data["status"] == "draft"
    assert "saved_at" in data


def test_load_post_roundtrip(tmp_output):
    path = save_post(SAMPLE_POST.copy())
    loaded = load_post(path)
    assert loaded["topic"] == SAMPLE_POST["topic"]


def test_list_posts_returns_drafts(tmp_output):
    save_post(SAMPLE_POST.copy())
    save_post(SAMPLE_POST.copy())
    posts = list_posts(status="draft")
    assert len(posts) == 2


def test_list_posts_filters_by_status(tmp_output):
    save_post(SAMPLE_POST.copy(), status="draft")
    save_post(SAMPLE_POST.copy(), status="scheduled")
    drafts = list_posts(status="draft")
    scheduled = list_posts(status="scheduled")
    assert len(drafts) == 1
    assert len(scheduled) == 1


def test_list_posts_limit(tmp_output):
    for _ in range(5):
        save_post(SAMPLE_POST.copy())
    posts = list_posts(limit=3)
    assert len(posts) == 3


def test_list_posts_empty_dir(tmp_output):
    posts = list_posts()
    assert posts == []


def test_list_posts_missing_dir(tmp_path, monkeypatch):
    import src.utils.storage as storage_mod
    monkeypatch.setattr(storage_mod, "OUTPUT_DIR", tmp_path / "nonexistent")
    assert list_posts() == []


def test_update_post_status(tmp_output):
    path = save_post(SAMPLE_POST.copy())
    update_post_status(str(path), "scheduled")
    # Old file should be gone, new one should exist with updated status
    assert not path.exists()
    posts = list_posts(status="scheduled")
    assert len(posts) == 1
    assert posts[0]["status"] == "scheduled"
    assert "updated_at" in posts[0]


def test_update_post_status_with_extra(tmp_output):
    path = save_post(SAMPLE_POST.copy())
    update_post_status(str(path), "scheduled", extra={"buffer_id": "abc123"})
    posts = list_posts(status="scheduled")
    assert posts[0]["buffer_id"] == "abc123"
