"""
Run this script from the backend/ directory to manually save your Meta
(Facebook / Instagram) account using a user access token.

Usage:
    cd backend
    python save_meta_token.py YOUR_USER_ACCESS_TOKEN
"""

import sys
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v25.0")

TOKENS_DIR = Path("tokens")
FB_TOKENS_DIR = TOKENS_DIR / "facebook"
IG_TOKENS_DIR = TOKENS_DIR / "instagram"
FB_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
IG_TOKENS_DIR.mkdir(parents=True, exist_ok=True)


def exchange_for_long_lived_token(short_token: str) -> str:
    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")
    if not app_id or not app_secret:
        print("⚠️  META_APP_ID / META_APP_SECRET not set — using token as-is.")
        return short_token

    r = requests.get(
        f"https://graph.facebook.com/{META_GRAPH_VERSION}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
        timeout=60,
    )
    data = r.json()
    if r.status_code >= 400 or "error" in data:
        print(f"⚠️  Could not exchange for long-lived token: {data}. Using original token.")
        return short_token

    long_token = data.get("access_token", short_token)
    print("✅ Exchanged for a long-lived user token.")
    return long_token


def fetch_and_save(access_token: str):
    print(f"\n📡 Fetching pages from Meta Graph API ({META_GRAPH_VERSION})...")

    r = requests.get(
        f"https://graph.facebook.com/{META_GRAPH_VERSION}/me/accounts",
        params={
            "access_token": access_token,
            "fields": "id,name,access_token,picture{url},fan_count,"
                      "instagram_business_account{id,username,profile_picture_url,name}",
            "limit": 100,
        },
        timeout=60,
    )
    data = r.json()

    if r.status_code >= 400 or "error" in data:
        print(f"❌ Error from Meta API: {data.get('error', data)}")
        sys.exit(1)

    pages = data.get("data", [])
    if not pages:
        print("⚠️  No Facebook Pages found for this token.")
        print("    Make sure the token has: pages_show_list, pages_read_engagement permissions.")
        sys.exit(1)

    fb_saved = []
    ig_saved = []

    for page in pages:
        # Save Facebook Page
        page_info = {
            "page_id": page["id"],
            "name": page["name"],
            "access_token": page["access_token"],
            "picture": page.get("picture", {}).get("data", {}).get("url", ""),
            "fan_count": str(page.get("fan_count", "0")),
        }
        token_path = FB_TOKENS_DIR / f"{page['id']}.json"
        with open(token_path, "w") as f:
            json.dump(page_info, f, indent=2)
        fb_saved.append(page_info["name"])
        print(f"  ✅ Facebook Page saved: {page_info['name']} (ID: {page['id']})")

        # Save Instagram Business Account (if linked)
        ig = page.get("instagram_business_account")
        if ig:
            ig_info = {
                "instagram_user_id": ig["id"],
                "username": ig.get("username") or ig.get("name") or page["name"],
                "name": ig.get("name") or ig.get("username") or page["name"],
                "picture": ig.get("profile_picture_url", ""),
                "page_id": page["id"],
                "page_name": page["name"],
                "access_token": page["access_token"],
            }
            ig_path = IG_TOKENS_DIR / f"{ig['id']}.json"
            with open(ig_path, "w") as f:
                json.dump(ig_info, f, indent=2)
            ig_saved.append(ig_info["username"])
            print(f"  ✅ Instagram account saved: @{ig_info['username']} (ID: {ig['id']})")

    print(f"\n🎉 Done!")
    print(f"   Facebook Pages saved : {len(fb_saved)} → {', '.join(fb_saved)}")
    print(f"   Instagram accounts   : {len(ig_saved)} → {', '.join(ig_saved) if ig_saved else 'none linked'}")
    print("\nYou can now refresh the app — your accounts will appear in the connected list.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python save_meta_token.py YOUR_USER_ACCESS_TOKEN")
        sys.exit(1)

    raw_token = sys.argv[1].strip()
    print("🔑 Token received. Attempting to exchange for long-lived token...")
    long_token = exchange_for_long_lived_token(raw_token)
    fetch_and_save(long_token)
