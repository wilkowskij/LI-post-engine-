"""
Cloudinary integration — upload and manage images for LinkedIn posts.
Cloud: drum3eekm
"""
import os
import io
from pathlib import Path
from typing import Optional, Union
from datetime import datetime


def get_cloudinary():
    """Lazy import and configure Cloudinary."""
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api

    cloudinary.config(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "drum3eekm"),
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    return cloudinary


def upload_post_image(
    image_path: Union[str, Path],
    topic: str,
    post_date: Optional[str] = None,
) -> dict:
    """
    Upload an image to Cloudinary under the li-posts folder.
    Returns the secure URL and public_id.
    """
    cloudinary = get_cloudinary()
    import cloudinary.uploader

    date_str = post_date or datetime.now().strftime("%Y-%m-%d")
    safe_topic = topic.lower().replace(" ", "_").replace("/", "-")[:40]
    folder = f"li-posts/{date_str}"
    public_id = f"{folder}/{safe_topic}"

    result = cloudinary.uploader.upload(
        str(image_path),
        public_id=public_id,
        overwrite=True,
        resource_type="image",
        tags=["linkedin", "post", safe_topic],
        context={"topic": topic, "post_date": date_str},
    )

    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "width": result.get("width"),
        "height": result.get("height"),
        "format": result.get("format"),
    }


def upload_image_from_url(image_url: str, topic: str, post_date: Optional[str] = None) -> dict:
    """Fetch an image from a URL and upload to Cloudinary."""
    cloudinary = get_cloudinary()
    import cloudinary.uploader

    date_str = post_date or datetime.now().strftime("%Y-%m-%d")
    safe_topic = topic.lower().replace(" ", "_").replace("/", "-")[:40]
    folder = f"li-posts/{date_str}"
    public_id = f"{folder}/{safe_topic}"

    result = cloudinary.uploader.upload(
        image_url,
        public_id=public_id,
        overwrite=True,
        resource_type="image",
        tags=["linkedin", "post", safe_topic],
    )

    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "width": result.get("width"),
        "height": result.get("height"),
    }


def get_optimized_url(public_id: str, width: int = 1200, height: int = 627) -> str:
    """
    Return a Cloudinary URL optimized for LinkedIn's recommended OG image size (1200x627).
    """
    cloudinary = get_cloudinary()
    from cloudinary import CloudinaryImage

    img = CloudinaryImage(public_id)
    return img.build_url(
        width=width,
        height=height,
        crop="fill",
        gravity="auto",
        fetch_format="auto",
        quality="auto",
    )


def list_recent_post_images(days: int = 7) -> list[dict]:
    """List images uploaded in the last N days."""
    cloudinary = get_cloudinary()
    import cloudinary.api

    result = cloudinary.api.resources(
        type="upload",
        prefix="li-posts/",
        max_results=50,
        tags=True,
    )
    return [
        {
            "public_id": r["public_id"],
            "url": r["secure_url"],
            "created_at": r.get("created_at"),
        }
        for r in result.get("resources", [])
    ]


def delete_post_image(public_id: str) -> bool:
    """Delete an image by public_id."""
    cloudinary = get_cloudinary()
    import cloudinary.uploader

    result = cloudinary.uploader.destroy(public_id)
    return result.get("result") == "ok"
