"""
LinkedIn private API integration using linkedin-api (unofficial).
Handles username/password login, session persistence, and posting.
"""

import json
import logging
import os
import time
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("tokens/linkedin_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

LI_TOKENS_DIR = Path("tokens/linkedin")
LI_TOKENS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(username: str) -> Path:
    return SESSIONS_DIR / f"{username}.json"


def login_with_credentials(username: str, password: str) -> dict:
    """
    Log in to LinkedIn with email + password using linkedin-api.
    Saves session cookies to disk for reuse.
    Returns account info dict.
    """
    try:
        from linkedin_api import Linkedin
    except ImportError:
        raise ValueError(
            "linkedin-api package is not installed. "
            "Run: pip install linkedin-api"
        )

    sess_path = _session_path(username)

    try:
        # authenticate=True forces a fresh login
        api = Linkedin(username, password, authenticate=True, cookies_dir=str(SESSIONS_DIR))
        logger.info(f"LinkedIn login successful for {username}")
    except Exception as e:
        err = str(e).lower()
        if "challenge" in err or "verification" in err or "pin" in err:
            raise ValueError(
                "LinkedIn sent a security challenge. "
                "Please log in at linkedin.com in your browser to verify, then try again."
            )
        if "bad credentials" in err or "invalid" in err or "unauthorized" in err or "401" in err:
            raise ValueError("Incorrect email or password. Please check and try again.")
        raise ValueError(f"LinkedIn login failed: {str(e)}")

    return _build_account_info(api, username)


def _build_account_info(api, email: str) -> dict:
    """Fetch profile and save to tokens/linkedin/{sub}.json."""
    try:
        profile = api.get_user_profile()
        urn_id  = profile.get("plainId") or profile.get("miniProfile", {}).get("entityUrn", "").split(":")[-1]
        name    = (
            profile.get("miniProfile", {}).get("firstName", {}).get("text", "")
            + " "
            + profile.get("miniProfile", {}).get("lastName", {}).get("text", "")
        ).strip() or email
        pic_root = profile.get("miniProfile", {}).get("picture", {})
        pic      = ""
        artifacts = pic_root.get("rootUrl", "")
        if not pic and artifacts:
            pic = artifacts  # fallback
    except Exception:
        urn_id = email.replace("@", "_").replace(".", "_")
        name   = email
        pic    = ""

    person_urn = f"urn:li:person:{urn_id}"

    account = {
        "access_token": None,
        "person_urn": person_urn,
        "name": name,
        "email": email,
        "picture": pic,
        "token_type": "linkedin_private",
    }

    token_path = LI_TOKENS_DIR / f"{urn_id}.json"
    with open(token_path, "w") as f:
        json.dump(account, f, indent=2)

    return account


def _get_api(email: str, password: str = "") -> "Linkedin":
    """Return an authenticated Linkedin API client using saved cookies."""
    try:
        from linkedin_api import Linkedin
    except ImportError:
        raise RuntimeError("linkedin-api not installed. Run: pip install linkedin-api")

    return Linkedin(email, password or "", authenticate=bool(password), cookies_dir=str(SESSIONS_DIR))


def publish_text_post(email: str, text: str) -> tuple[str, str]:
    """Publish a plain-text post to LinkedIn feed."""
    api = _get_api(email)
    result = api.post(text)
    post_id = result if isinstance(result, str) else str(result)
    return post_id, f"https://www.linkedin.com/feed/"


def publish_post_with_media(person_urn: str, email: str, text: str,
                            media_path: str | None = None) -> tuple[str, str]:
    """
    Publish a LinkedIn post with optional image/video.
    Falls back to official upload API with session cookies for media.
    """
    sess_path = _session_path(email)
    if not sess_path.exists():
        raise FileNotFoundError(f"No saved session for {email}. Please reconnect.")

    # Load cookies from saved session
    with open(sess_path) as f:
        cookies_data = json.load(f)

    # Build a requests session with LinkedIn cookies
    session = requests.Session()
    for cookie in cookies_data if isinstance(cookies_data, list) else cookies_data.get("cookies", []):
        if isinstance(cookie, dict):
            session.cookies.set(cookie.get("name", ""), cookie.get("value", ""))

    csrf = session.cookies.get("JSESSIONID", "ajax:0").strip('"')
    headers = {
        "csrf-token": csrf,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
        "X-Li-Lang": "en_US",
    }

    media_asset = None
    if media_path:
        ext = media_path.rsplit(".", 1)[-1].lower()
        is_video = ext in {"mp4", "mov", "avi", "mkv", "webm"}

        recipe = "urn:li:digitalmediaRecipe:feedshare-video" if is_video else "urn:li:digitalmediaRecipe:feedshare-image"

        reg_resp = session.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers=headers,
            json={
                "registerUploadRequest": {
                    "recipes": [recipe],
                    "owner": person_urn,
                    "serviceRelationships": [{
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }]
                }
            }
        )

        if reg_resp.status_code == 200:
            reg_data    = reg_resp.json()
            upload_url  = reg_data["value"]["uploadMechanism"][
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
            ]["uploadUrl"]
            media_asset = reg_data["value"]["asset"]

            with open(media_path, "rb") as mf:
                session.put(upload_url, data=mf,
                            headers={"Content-Type": "application/octet-stream"})

    # Build UGC post payload
    if media_asset:
        ext      = media_path.rsplit(".", 1)[-1].lower()
        is_video = ext in {"mp4", "mov", "avi", "mkv", "webm"}
        media_category = "VIDEO" if is_video else "IMAGE"
        media_block = [{
            "status": "READY",
            "description": {"text": ""},
            "media": media_asset,
            "title": {"text": ""},
        }]
    else:
        media_category = "NONE"
        media_block    = []

    post_body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": media_category,
                **( {"media": media_block} if media_block else {} )
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    post_resp = session.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=post_body,
    )

    if post_resp.status_code not in (200, 201):
        raise RuntimeError(f"LinkedIn post failed: {post_resp.text}")

    post_id  = post_resp.json().get("id", "")
    post_url = f"https://www.linkedin.com/feed/update/{post_id}"
    return post_id, post_url


def disconnect(email: str, urn_id: str = ""):
    """Remove saved session and token files."""
    paths = [_session_path(email)]
    if urn_id:
        paths.append(LI_TOKENS_DIR / f"{urn_id}.json")
    for p in paths:
        if p.exists():
            p.unlink()
