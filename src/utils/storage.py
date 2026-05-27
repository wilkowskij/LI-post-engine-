"""
Local post storage — saves generated posts to JSON for review and history.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "posts"


def save_post(post: dict, status: str = "draft") -> Path:
    """Save a generated post to disk."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    slug = post.get("topic", "post").lower().replace(" ", "_")[:30]
    fmt = post.get("format", "post")
    stamp = now.strftime("%H%M%S%f")  # HHMMSS + 6 microsecond digits — unique per call
    filename = OUTPUT_DIR / f"{date_str}_{slug}_{fmt}_{stamp}_{status}.json"

    record = {
        **post,
        "status": status,
        "saved_at": now.isoformat(),
    }

    with open(filename, "w") as f:
        json.dump(record, f, indent=2)

    return filename


def load_post(filepath: Path) -> dict:
    with open(filepath) as f:
        return json.load(f)


def list_posts(status: Optional[str] = None, limit: int = 10) -> list[dict]:
    """List saved posts, optionally filtered by status."""
    if not OUTPUT_DIR.exists():
        return []

    posts = []
    for f in sorted(OUTPUT_DIR.glob("*.json"), reverse=True):
        try:
            record = load_post(f)
            if status is None or record.get("status") == status:
                record["_filepath"] = str(f)
                posts.append(record)
        except Exception:
            continue

    return posts[:limit]


def update_post_status(filepath: str, status: str, extra: Optional[dict] = None) -> None:
    """Update the status of a saved post."""
    path = Path(filepath)
    record = load_post(path)
    record["status"] = status
    record["updated_at"] = datetime.now().isoformat()
    if extra:
        record.update(extra)

    # Rename file to reflect new status
    new_name = path.stem.rsplit("_", 1)[0] + f"_{status}.json"
    new_path = path.parent / new_name

    with open(new_path, "w") as f:
        json.dump(record, f, indent=2)

    if path != new_path:
        path.unlink()
