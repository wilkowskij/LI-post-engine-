"""
Buffer.com integration — schedule LinkedIn posts via the Buffer API.
Docs: https://api.buffer.com
Auth: OAuth 2.0 Bearer token (BUFFER_ACCESS_TOKEN)
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import requests


BUFFER_API_BASE = "https://api.bufferapp.com/1"


class BufferClient:
    def __init__(self, access_token: Optional[str] = None):
        self.token = access_token or os.environ["BUFFER_ACCESS_TOKEN"]
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _get(self, path: str, **kwargs) -> dict:
        params = kwargs.pop("params", {})
        params["access_token"] = self.token
        resp = self.session.get(f"{BUFFER_API_BASE}/{path}", params=params, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, **kwargs) -> dict:
        data = kwargs.pop("data", {})
        data["access_token"] = self.token
        resp = self.session.post(f"{BUFFER_API_BASE}/{path}", data=data, **kwargs)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    # Channels (profiles)
    # ------------------------------------------------------------------ #

    def get_profiles(self) -> list[dict]:
        """Return all connected social channels."""
        result = self._get("profiles.json")
        return result if isinstance(result, list) else result.get("data", [])

    def get_linkedin_profiles(self) -> list[dict]:
        """Return only LinkedIn channels."""
        return [p for p in self.get_profiles() if "linkedin" in p.get("service", "").lower()]

    def get_profile_ids(self) -> list[str]:
        """Return channel IDs from env or auto-detect LinkedIn channels."""
        env_ids = os.environ.get("BUFFER_PROFILE_IDS", "")
        if env_ids:
            return [pid.strip() for pid in env_ids.split(",") if pid.strip()]
        linkedin = self.get_linkedin_profiles()
        return [p["id"] for p in linkedin]

    # ------------------------------------------------------------------ #
    # Creating updates (posts)
    # ------------------------------------------------------------------ #

    def schedule_post(
        self,
        text: str,
        profile_ids: Optional[list[str]] = None,
        scheduled_at: Optional[datetime] = None,
        image_url: Optional[str] = None,
        now: bool = False,
    ) -> dict:
        """
        Schedule a post to LinkedIn via Buffer.

        Args:
            text: Post body text.
            profile_ids: List of Buffer channel IDs. Auto-detects LinkedIn if None.
            scheduled_at: When to post. Uses Buffer's optimal timing if None.
            image_url: Optional image URL (Cloudinary URL recommended).
            now: If True, post immediately.
        """
        ids = profile_ids or self.get_profile_ids()
        if not ids:
            raise ValueError("No LinkedIn channel IDs found. Set BUFFER_PROFILE_IDS in .env")

        payload: dict = {
            "text": text,
            "shorten": False,
        }

        for i, pid in enumerate(ids):
            payload[f"profile_ids[{i}]"] = pid

        if now:
            payload["now"] = True
        elif scheduled_at:
            payload["scheduled_at"] = scheduled_at.strftime("%Y-%m-%dT%H:%M:%S+0000")

        if image_url:
            payload["media[photo]"] = image_url
            payload["media[thumbnail]"] = image_url

        return self._post("updates/create.json", data=payload)

    def add_to_queue(
        self,
        text: str,
        profile_ids: Optional[list[str]] = None,
        image_url: Optional[str] = None,
    ) -> dict:
        """Add post to the Buffer queue using optimal timing."""
        return self.schedule_post(text, profile_ids=profile_ids, image_url=image_url)

    def schedule_for_tomorrow_morning(
        self,
        text: str,
        profile_ids: Optional[list[str]] = None,
        hour: int = 8,
        image_url: Optional[str] = None,
    ) -> dict:
        """Schedule a post for tomorrow at the specified hour (UTC)."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
        return self.schedule_post(
            text, profile_ids=profile_ids, scheduled_at=scheduled, image_url=image_url
        )

    # ------------------------------------------------------------------ #
    # Viewing scheduled content
    # ------------------------------------------------------------------ #

    def get_pending_updates(self, profile_id: str) -> list[dict]:
        result = self._get(f"profiles/{profile_id}/updates/pending.json")
        return result.get("updates", [])

    def get_sent_updates(self, profile_id: str, count: int = 10) -> list[dict]:
        result = self._get(
            f"profiles/{profile_id}/updates/sent.json",
            params={"count": count},
        )
        return result.get("updates", [])

    def get_queue_summary(self) -> list[dict]:
        """Return a summary of the queue across all LinkedIn channels."""
        profiles = self.get_linkedin_profiles()
        summary = []
        for p in profiles:
            try:
                pending = self.get_pending_updates(p["id"])
            except Exception:
                pending = []
            summary.append(
                {
                    "profile": p.get("formatted_username", p["id"]),
                    "profile_id": p["id"],
                    "pending_count": len(pending),
                    "next_post": pending[0].get("scheduled_at") if pending else None,
                }
            )
        return summary

    # ------------------------------------------------------------------ #
    # Schedule management
    # ------------------------------------------------------------------ #

    def get_posting_schedule(self, profile_id: str) -> dict:
        return self._get(f"profiles/{profile_id}/schedules.json")

    def set_daily_schedule(self, profile_id: str, times: list[str]) -> dict:
        """Set posting times for every day. times: ["HH:MM", ...] in UTC."""
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        payload: dict = {}
        for i, day in enumerate(days):
            payload[f"schedules[{i}][days][]"] = day
            for j, t in enumerate(times):
                h, _ = t.split(":")
                payload[f"schedules[{i}][times][{j}]"] = f"{h}:00"
        return self._post(f"profiles/{profile_id}/schedules/update.json", data=payload)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def validate_connection(self) -> bool:
        """Check that the access token works."""
        try:
            self.get_profiles()
            return True
        except Exception as e:
            print(f"[buffer] channels.json failed: {e}")
        try:
            user = self._get("user.json")
            return bool(user.get("id"))
        except Exception as e:
            print(f"[buffer] user.json failed: {e}")
        return False
