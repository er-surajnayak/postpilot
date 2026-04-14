"""
Run this script from the backend/ directory to manually save your Instagram
account using an IGAAN access token from the Meta Developer Console.

Usage:
    cd backend
    python save_instagram_token.py YOUR_IGAAN_TOKEN
"""

import sys
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")

TOKENS_DIR = Path("tokens")
IG_TOKENS_DIR = TOKENS_DIR / "instagram"
IG_TOKENS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_instagram_user(token: str) -> dict | None:
    """
    Fetch user info using graph.instagram.com/me — correct for IGAAN tokens.
    No version number in the path for Instagram Login tokens.
    """
    r = requests.get(
        "https://graph.instagram.com/me",
        params={
            "fields": "user_id,id,username,name,profile_picture_url,account_type",
            "access_token": token,
        },
        timeout=60,
    )
    data = r.json()
    if r.status_code == 200 and ("id" in data or "user_id" in data):
        return data

    err = data.get("error", {}).get("message", str(data))
    print(f"❌ graph.instagram.com/me failed: {err}")
    return None


def exchange_long_lived(token: str) -> str:
    """Try to get a 60-day token. Skip silently on failure."""
    if not INSTAGRAM_APP_SECRET:
        return token

    r = requests.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": INSTAGRAM_APP_SECRET,
            "access_token": token,
        },
        timeout=60,
    )
    data = r.json()
    if r.status_code == 200 and "access_token" in data:
        days = int(data.get("expires_in", 0)) // 86400
        print(f"✅ Exchanged for long-lived token (~{days} days).")
        return data["access_token"]

    err = data.get("error", {}).get("message", "unknown")
    print(f"⚠️  Token exchange skipped ({err}) — using original token.")
    return token


def main():
    if len(sys.argv) < 2:
        print("Usage: python save_instagram_token.py YOUR_IGAAN_TOKEN")
        sys.exit(1)

    token = sys.argv[1].strip()
    print(f"🔑 Token: {token[:12]}...")

    print("\n🔄 Trying long-lived token exchange...")
    token = exchange_long_lived(token)

    print("\n📡 Fetching Instagram user info from graph.instagram.com/me ...")
    user_info = fetch_instagram_user(token)

    if not user_info:
        print("\n❌ Token could not be validated.")
        print("\n💡 To get a valid token:")
        print("   1. Go to developers.facebook.com → your app (1389341513221607)")
        print("   2. Use Cases → Instagram API → API setup with Instagram login")
        print("   3. Section '2. Generate access tokens' → click 'Generate token' next to your account")
        print("   4. Copy the token that appears and run this script again")
        sys.exit(1)

    ig_id = str(user_info.get("user_id") or user_info.get("id"))
    username = user_info.get("username") or user_info.get("name") or ig_id

    ig_info = {
        "instagram_user_id": ig_id,
        "username": username,
        "name": user_info.get("name") or username,
        "picture": user_info.get("profile_picture_url", ""),
        "account_type": user_info.get("account_type", "Business"),
        "page_id": None,
        "page_name": None,
        "access_token": token,
        "token_type": "instagram_login",
    }

    ig_path = IG_TOKENS_DIR / f"{ig_id}.json"
    with open(ig_path, "w") as f:
        json.dump(ig_info, f, indent=2)

    print(f"\n🎉 Done! Instagram account saved: @{username} (ID: {ig_id})")
    print("Refresh the app — your account will appear in the connected list.")


if __name__ == "__main__":
    main()
