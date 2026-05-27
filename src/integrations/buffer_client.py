"""
Buffer.com integration — schedule LinkedIn posts via the Buffer GraphQL API.
Docs: https://developers.buffer.com
Auth: Bearer API key (get from developers.buffer.com → API settings)
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import requests


BUFFER_API_BASE = "https://api.buffer.com"


class BufferClient:
    def __init__(self, access_token: Optional[str] = None):
        self.token = access_token or os.environ["BUFFER_ACCESS_TOKEN"]
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })

    def _query(self, query: str, variables: Optional[dict] = None) -> dict:
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = self.session.post(BUFFER_API_BASE, json=payload)
        if not resp.ok:
            print(f"[buffer] HTTP {resp.status_code}: {resp.text[:2000]}")
            resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise ValueError(f"GraphQL errors: {data['errors']}")
        return data.get("data", {})

    # ------------------------------------------------------------------ #
    # Channels
    # ------------------------------------------------------------------ #

    def get_profiles(self) -> list[dict]:
        """Return all connected social channels."""
        data = self._query("""
            query GetChannels {
              account {
                channels {
                  id
                  service
                  name
                }
              }
            }
        """)
        return data.get("account", {}).get("channels", [])

    def get_linkedin_profiles(self) -> list[dict]:
        """Return only LinkedIn channels."""
        return [p for p in self.get_profiles() if "linkedin" in p.get("service", "").lower()]

    def get_profile_ids(self) -> list[str]:
        """Return channel IDs from env, falling back to auto-detected LinkedIn channels."""
        all_channels = self.get_profiles()
        valid_ids = {c["id"] for c in all_channels}

        env_ids = os.environ.get("BUFFER_PROFILE_IDS", "")
        if env_ids:
            requested = [pid.strip() for pid in env_ids.split(",") if pid.strip()]
            if all(pid in valid_ids for pid in requested):
                return requested

        linkedin = [c for c in all_channels if "linkedin" in c.get("service", "").lower()]
        return [p["id"] for p in linkedin]

    # ------------------------------------------------------------------ #
    # Creating posts
    # ------------------------------------------------------------------ #

    def schedule_post(
        self,
        text: str,
        profile_ids: Optional[list[str]] = None,
        scheduled_at: Optional[datetime] = None,
        image_url: Optional[str] = None,
        now: bool = False,
    ) -> dict:
        ids = profile_ids or self.get_profile_ids()
        if not ids:
            raise ValueError("No LinkedIn channel IDs found. Set BUFFER_PROFILE_IDS secret.")

        results = []
        for channel_id in ids:
            if now:
                mode = "shareNow"
            elif scheduled_at:
                mode = "customScheduled"
            else:
                mode = "addToQueue"

            inp: dict = {
                "channelId": channel_id,
                "text": text,
                "schedulingType": "automatic",
                "mode": mode,
            }
            if scheduled_at:
                inp["dueAt"] = scheduled_at.strftime("%Y-%m-%dT%H:%M:%S+0000")
            if image_url:
                inp["assets"] = [{"image": {"url": image_url}}]

            data = self._query("""
                mutation CreatePost($input: CreatePostInput!) {
                  createPost(input: $input) {
                    ... on PostActionSuccess {
                      post { id status }
                    }
                  }
                }
            """, {"input": inp})

            result = data.get("createPost", {})
            if result.get("message"):
                raise ValueError(f"Buffer post error: {result['message']}")
            results.append(result.get("post", {}))

        return results[0] if len(results) == 1 else {"posts": results}

    def add_to_queue(
        self,
        text: str,
        profile_ids: Optional[list[str]] = None,
        image_url: Optional[str] = None,
    ) -> dict:
        return self.schedule_post(text, profile_ids=profile_ids, image_url=image_url)

    def schedule_for_tomorrow_morning(
        self,
        text: str,
        profile_ids: Optional[list[str]] = None,
        hour: int = 8,
        image_url: Optional[str] = None,
    ) -> dict:
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
        return self.schedule_post(
            text, profile_ids=profile_ids, scheduled_at=scheduled, image_url=image_url
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def validate_connection(self) -> bool:
        try:
            data = self._query("query { account { id } }")
            return bool(data.get("account", {}).get("id"))
        except Exception as e:
            print(f"[buffer] connection check failed: {e}")
            return False

    def get_queue_summary(self) -> list[dict]:
        try:
            profiles = self.get_linkedin_profiles()
            return [{"profile": p.get("name", p["id"]), "profile_id": p["id"]} for p in profiles]
        except Exception:
            return []
