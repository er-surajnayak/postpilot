"""
Instagram private API integration using instagrapi.
Handles username/password login, session persistence, and posting.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("tokens/instagram_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

IG_META_DIR = Path("tokens/instagram")
IG_META_DIR.mkdir(parents=True, exist_ok=True)


def _get_client():
    """Return a fresh instagrapi Client instance."""
    from instagrapi import Client
    cl = Client()
    cl.delay_range = [1, 3]
    return cl


def _session_path(username: str) -> Path:
    return SESSIONS_DIR / f"{username}.json"


def _meta_path(user_id: str) -> Path:
    """Save by numeric user_id so get_instagram_account() can find it."""
    return IG_META_DIR / f"{user_id}.json"


def login_with_credentials(username: str, password: str, verification_code: str = "") -> dict:
    """
    Log in to Instagram with username + password.
    Saves session to disk so future calls skip re-login.
    Returns account info dict.
    """
    from instagrapi import Client

    # Import only exceptions that exist — vary by instagrapi version
    _exceptions = {}
    try:
        import instagrapi.exceptions as _exc
        for _name in ["BadPassword", "TwoFactorRequired", "ChallengeRequired",
                      "SelectContactPointRecoveryForm", "RecaptchaChallengeForm",
                      "LoginRequired", "InvalidUser", "UserNotFound"]:
            if hasattr(_exc, _name):
                _exceptions[_name] = getattr(_exc, _name)
    except Exception:
        pass

    cl = _get_client()
    sess_path = _session_path(username)

    # Try to reuse an existing session first
    if sess_path.exists():
        try:
            cl.load_settings(sess_path)
            cl.login(username, password)
            cl.dump_settings(sess_path)
            logger.info(f"Reused existing session for @{username}")
            return _build_account_info(cl, username)
        except Exception:
            pass  # Session stale — fall through to fresh login

    try:
        if verification_code:
            cl.login(username, password, verification_code=verification_code)
        else:
            cl.login(username, password)

    except Exception as e:
        err_type = type(e).__name__
        err_msg  = str(e).lower()

        if err_type in ("TwoFactorRequired",) or "two factor" in err_msg or "2fa" in err_msg:
            raise ValueError("2FA_REQUIRED")

        if err_type in ("BadPassword",) or "bad password" in err_msg or "wrong password" in err_msg:
            raise ValueError("Incorrect password. Please check and try again.")

        if err_type in ("InvalidUser", "UserNotFound") or "user not found" in err_msg or "invalid user" in err_msg:
            raise ValueError(f"Username '@{username}' not found on Instagram.")

        if err_type in ("ChallengeRequired", "SelectContactPointRecoveryForm", "RecaptchaChallengeForm") \
                or "challenge" in err_msg or "checkpoint" in err_msg:
            raise ValueError(
                "Instagram requires account verification. "
                "Please open the Instagram app, complete any security check, then try again."
            )

        if err_type == "LoginRequired" or "login required" in err_msg:
            raise ValueError("Instagram rejected the login. Please try again in a few minutes.")

        raise ValueError(f"Login failed: {str(e)}")

    cl.dump_settings(sess_path)
    logger.info(f"Fresh login successful for @{username}")
    return _build_account_info(cl, username)


def _build_account_info(cl, username: str) -> dict:
    """Fetch profile info and save to tokens/instagram/{username}.json."""
    try:
        user_info = cl.user_info_by_username(username)
        pic = str(user_info.profile_pic_url) if user_info.profile_pic_url else ""
        name = user_info.full_name or username
        user_id = str(user_info.pk)
    except Exception:
        user_id = str(cl.user_id) if cl.user_id else username
        name = username
        pic = ""

    account = {
        "instagram_user_id": user_id,
        "username": username,
        "name": name,
        "picture": pic,
        "page_id": None,
        "page_name": None,
        "access_token": None,
        "token_type": "instagrapi",   # tells scheduler to use instagrapi, not Graph API
    }

    # Save as {user_id}.json so auth.get_instagram_account(user_id) finds it correctly
    meta_path = _meta_path(user_id)
    with open(meta_path, "w") as f:
        json.dump(account, f, indent=2)

    return account


def _load_session_client(username: str):
    """Load saved session for username. Raises if no session found."""
    sess_path = _session_path(username)
    if not sess_path.exists():
        raise FileNotFoundError(
            f"No saved session for @{username}. "
            "Please reconnect the Instagram account."
        )
    cl = _get_client()
    cl.load_settings(sess_path)
    return cl


def publish_photo(username: str, image_path: str, caption: str = "") -> tuple[str, str]:
    """Upload a photo post. Returns (media_id, permalink)."""
    cl = _load_session_client(username)
    media = cl.photo_upload(image_path, caption=caption)
    media_id = str(media.pk)
    permalink = f"https://www.instagram.com/p/{media.code}/"
    return media_id, permalink


def publish_video(username: str, video_path: str, caption: str = "") -> tuple[str, str]:
    """Upload a video post. Returns (media_id, permalink)."""
    cl = _load_session_client(username)
    media = cl.video_upload(video_path, caption=caption)
    media_id = str(media.pk)
    permalink = f"https://www.instagram.com/p/{media.code}/"
    return media_id, permalink


def disconnect(username: str, user_id: str = ""):
    """Remove saved session and meta files for this account."""
    paths = [_session_path(username)]
    if user_id:
        paths.append(_meta_path(user_id))
    for p in paths:
        if p.exists():
            p.unlink()
