import os
import time
from pathlib import Path
from urllib.parse import quote

import requests
from fastapi import HTTPException

API_VERSION = os.getenv("META_GRAPH_VERSION", "v23.0")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

# Instagram Login API uses graph.instagram.com, not graph.facebook.com
IG_GRAPH_BASE = "https://graph.instagram.com"
FB_GRAPH_BASE = f"https://graph.facebook.com/{API_VERSION}"


def _graph_url(path: str) -> str:
    return f"{FB_GRAPH_BASE}/{path.lstrip('/')}"


def _ig_url(path: str) -> str:
    """Build a graph.instagram.com URL for Instagram Login tokens."""
    return f"{IG_GRAPH_BASE}/{API_VERSION}/{path.lstrip('/')}"


def _parse_response(response, action: str) -> dict:
    try:
        data = response.json()
    except Exception:
        data = {"error": {"message": response.text}}

    if response.status_code >= 400 or "error" in data:
        message = data.get("error", {}).get("message") or str(data)
        raise HTTPException(status_code=400, detail=f"{action} failed: {message}")
    return data


def _is_video(media_path: str | None) -> bool:
    return bool(media_path) and Path(media_path).suffix.lower() in VIDEO_EXTENSIONS


def publish_facebook_post(page_id: str, access_token: str, message: str,
                          media_path: str | None = None, title: str = ""):
    if media_path and _is_video(media_path):
        with open(media_path, "rb") as media_file:
            response = requests.post(
                _graph_url(f"{page_id}/videos"),
                data={
                    "access_token": access_token,
                    "description": message or title or "",
                    "title": title or "Scheduled post",
                },
                files={"source": media_file},
                timeout=300,
            )
        data = _parse_response(response, "Facebook video upload")
        media_id = data.get("id", "")
        return media_id, f"https://www.facebook.com/{page_id}/videos/{media_id}"

    if media_path:
        with open(media_path, "rb") as media_file:
            response = requests.post(
                _graph_url(f"{page_id}/photos"),
                data={
                    "access_token": access_token,
                    "caption": message or title or "",
                    "published": "true",
                },
                files={"source": media_file},
                timeout=300,
            )
        data = _parse_response(response, "Facebook photo upload")
        post_id = data.get("post_id") or data.get("id", "")
        return post_id, f"https://www.facebook.com/{page_id}/posts/{post_id}"

    response = requests.post(
        _graph_url(f"{page_id}/feed"),
        data={
            "access_token": access_token,
            "message": message or title or "",
        },
        timeout=120,
    )
    data = _parse_response(response, "Facebook post publish")
    post_id = data.get("id", "")
    return post_id, f"https://www.facebook.com/{page_id}/posts/{post_id}"


def _public_media_url(media_path: str) -> str:
    host = BACKEND_URL.lower()
    if "localhost" in host or "127.0.0.1" in host:
        raise HTTPException(
            status_code=400,
            detail="Instagram publishing requires BACKEND_URL to be a public URL so Meta can fetch uploaded media.",
        )

    file_name = quote(Path(media_path).name)
    return f"{BACKEND_URL}/uploads/{file_name}"


def _poll_instagram_container(container_id: str, access_token: str, base_url: str):
    """Poll the IG media container until it's ready. Works for both graph hosts."""
    for _ in range(30):
        response = requests.get(
            f"{base_url}/{container_id}",
            params={
                "access_token": access_token,
                "fields": "status_code,status",
            },
            timeout=60,
        )
        data = _parse_response(response, "Instagram media status")
        status = data.get("status_code") or data.get("status")
        if status in {"FINISHED", "PUBLISHED"}:
            return
        if status in {"ERROR", "EXPIRED"}:
            raise HTTPException(status_code=400, detail=f"Instagram media processing failed with status: {status}")
        time.sleep(5)

    raise HTTPException(status_code=400, detail="Instagram media processing timed out.")


def publish_instagram_post(instagram_user_id: str, access_token: str, caption: str,
                           media_path: str, token_type: str = "instagram_login"):
    """Publish a post to Instagram.
    
    token_type='instagram_login' uses graph.instagram.com (Instagram API with Instagram Login).
    token_type='facebook_login'  uses graph.facebook.com  (Instagram API with Facebook Login, legacy).
    """
    if not media_path:
        raise HTTPException(status_code=400, detail="Instagram requires an image or video file.")

    media_url = _public_media_url(media_path)
    is_video = _is_video(media_path)

    # Choose the correct graph host based on how the token was obtained
    if token_type == "instagram_login":
        # Instagram API with Instagram Login → graph.instagram.com
        graph_base = f"{IG_GRAPH_BASE}/{API_VERSION}"
    else:
        # Legacy: Instagram API with Facebook Login → graph.facebook.com
        graph_base = FB_GRAPH_BASE

    create_payload = {
        "access_token": access_token,
        "caption": caption or "",
    }
    if is_video:
        create_payload["media_type"] = "REELS"
        create_payload["video_url"] = media_url
        create_payload["share_to_feed"] = "true"
    else:
        create_payload["image_url"] = media_url

    create_response = requests.post(
        f"{graph_base}/{instagram_user_id}/media",
        data=create_payload,
        timeout=120,
    )
    create_data = _parse_response(create_response, "Instagram media creation")
    creation_id = create_data.get("id")
    if not creation_id:
        raise HTTPException(status_code=400, detail="Instagram did not return a media creation id.")

    _poll_instagram_container(creation_id, access_token, graph_base)

    publish_response = requests.post(
        f"{graph_base}/{instagram_user_id}/media_publish",
        data={
            "access_token": access_token,
            "creation_id": creation_id,
        },
        timeout=120,
    )
    publish_data = _parse_response(publish_response, "Instagram media publish")
    media_id = publish_data.get("id", "")

    permalink_response = requests.get(
        f"{graph_base}/{media_id}",
        params={
            "access_token": access_token,
            "fields": "permalink",
        },
        timeout=60,
    )
    permalink_data = _parse_response(permalink_response, "Instagram permalink lookup")
    return media_id, permalink_data.get("permalink", "https://www.instagram.com/")
