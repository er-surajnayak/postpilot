import os
import json
import pickle
import requests
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv(override=True)
import urllib.parse

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'      # allow http localhost
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'       # relax scope checking

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]

TOKENS_DIR = Path("tokens")
TOKENS_DIR.mkdir(exist_ok=True)

LI_TOKENS_DIR = TOKENS_DIR / "linkedin"
LI_TOKENS_DIR.mkdir(exist_ok=True)

FB_TOKENS_DIR = TOKENS_DIR / "facebook"
FB_TOKENS_DIR.mkdir(exist_ok=True)

IG_TOKENS_DIR = TOKENS_DIR / "instagram"
IG_TOKENS_DIR.mkdir(exist_ok=True)

# In-memory store for PKCE code_verifiers, keyed by OAuth state
_verifiers: dict[str, str] = {}

BACKEND_URL  = os.getenv("BACKEND_URL",  "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v23.0")

REDIRECT_URI     = f"{BACKEND_URL}/auth/callback"
LI_REDIRECT_URI  = f"{BACKEND_URL}/auth/linkedin/callback"
FB_REDIRECT_URI  = f"{BACKEND_URL}/auth/facebook/callback"
IG_REDIRECT_URI  = f"{BACKEND_URL}/auth/instagram/callback"



def get_flow() -> Flow:
    client_config = {
        "web": {
            "client_id":      os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret":  os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri":       "https://accounts.google.com/o/oauth2/auth",
            "token_uri":      "https://oauth2.googleapis.com/token",
            "redirect_uris":  [REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )


def get_auth_url() -> str:
    flow = get_flow()
    auth_url, state = flow.authorization_url(
        prompt="select_account",
        access_type="offline",
        include_granted_scopes="true",
    )
    _verifiers[state] = flow.code_verifier
    return auth_url


def exchange_code(code: str, state: str | None = None) -> dict:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    flow = get_flow()
    if state and state in _verifiers:
        flow.code_verifier = _verifiers.pop(state)

    flow.fetch_token(code=code)
    creds = flow.credentials

    yt = build("youtube", "v3", credentials=creds)
    r  = yt.channels().list(part="snippet,statistics", mine=True).execute()

    if not r.get("items"):
        raise ValueError("No YouTube channel found on this account.")

    channel      = r["items"][0]
    channel_id   = channel["id"]
    channel_name = channel["snippet"]["title"]
    thumb        = channel["snippet"]["thumbnails"].get("default", {}).get("url", "")
    subs         = channel.get("statistics", {}).get("subscriberCount", "0")

    token_path = TOKENS_DIR / f"{channel_id}.pickle"
    with open(token_path, "wb") as f:
        pickle.dump(creds, f)

    return {
        "channel_id":   channel_id,
        "channel_name": channel_name,
        "thumbnail":    thumb,
        "subscribers":  subs,
    }


def get_youtube_client(channel_id: str):
    token_path = TOKENS_DIR / f"{channel_id}.pickle"
    if not token_path.exists():
        raise FileNotFoundError(f"No token for channel {channel_id}. Please reconnect.")

    with open(token_path, "rb") as f:
        creds = pickle.load(f)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)

# ── LinkedIn OAuth ──────────────────────────────────────────────

def get_linkedin_auth_url() -> str:
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    if not client_id:
        raise ValueError("LINKEDIN_CLIENT_ID not found in .env")
    
    # Scopes: openid, profile, email, w_member_social
    # Note: w_member_social is needed for publishing
    scope    = "openid%20profile%20email%20w_member_social"
    encoded_uri = urllib.parse.quote(LI_REDIRECT_URI, safe='')
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&client_id={client_id}&"
        f"redirect_uri={encoded_uri}&scope={scope}&state=linkedin_auth"
    )
    print(f"Generated LinkedIn Auth URL: {auth_url}")
    return auth_url


def get_facebook_auth_url() -> str:
    client_id = os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID")
    if not client_id:
        raise ValueError("META_APP_ID not found in .env")

    scopes = ",".join([
        "public_profile",
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "business_management",
        "instagram_basic",
        "instagram_content_publish",
    ])
    encoded_uri = urllib.parse.quote(FB_REDIRECT_URI, safe="")
    return (
        f"https://www.facebook.com/{META_GRAPH_VERSION}/dialog/oauth?"
        f"client_id={client_id}&redirect_uri={encoded_uri}&"
        f"scope={scopes}&response_type=code&state=facebook_auth&"
        f"auth_type=reauthenticate"
    )


def get_instagram_auth_url() -> str:
    """Build OAuth URL for Instagram API with Instagram Login.
    Uses www.instagram.com/oauth/authorize (NOT facebook.com).
    """
    client_id = os.getenv("INSTAGRAM_APP_ID")
    if not client_id:
        raise ValueError("INSTAGRAM_APP_ID not found in .env")

    # These are the correct scopes for Instagram API with Instagram Login
    scopes = ",".join([
        "instagram_business_basic",
        "instagram_business_content_publish",
    ])
    encoded_uri = urllib.parse.quote(IG_REDIRECT_URI, safe="")
    return (
        f"https://www.instagram.com/oauth/authorize?"
        f"client_id={client_id}&redirect_uri={encoded_uri}&"
        f"scope={scopes}&response_type=code&state=instagram_auth"
    )


def exchange_instagram_code(code: str) -> dict:
    """Exchange OAuth code using Instagram Login flow.
    
    Correct endpoint chain:
    1. POST api.instagram.com/oauth/access_token  → short-lived token
    2. GET  graph.instagram.com/access_token      → long-lived token (60 days)
    3. GET  graph.instagram.com/me               → user ID + username
    """
    client_id = os.getenv("INSTAGRAM_APP_ID")
    client_secret = os.getenv("INSTAGRAM_APP_SECRET")
    if not client_id or not client_secret:
        raise ValueError("INSTAGRAM_APP_ID / INSTAGRAM_APP_SECRET must be set in .env")

    # Step 1: Exchange authorization code → short-lived Instagram user token
    # NOTE: Must use api.instagram.com, NOT graph.facebook.com
    response = requests.post(
        "https://api.instagram.com/oauth/access_token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": IG_REDIRECT_URI,
            "code": code,
        },
        timeout=60,
    )
    token_data = response.json()
    # The response can be nested under 'data' or flat
    if isinstance(token_data, dict) and "data" in token_data:
        token_data = token_data["data"][0]
    if response.status_code >= 400 or "access_token" not in token_data:
        raise ValueError(f"Instagram token exchange failed: {token_data}")

    short_lived_token = token_data["access_token"]
    ig_user_id = str(token_data.get("user_id", ""))

    # Step 2: Exchange short-lived → long-lived token (valid 60 days)
    # NOTE: Must use graph.instagram.com with grant_type=ig_exchange_token
    ll_response = requests.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": client_secret,
            "access_token": short_lived_token,
        },
        timeout=60,
    )
    ll_data = ll_response.json()
    access_token = ll_data.get("access_token", short_lived_token)

    # Step 3: Fetch user profile from graph.instagram.com/me
    me_resp = requests.get(
        "https://graph.instagram.com/me",
        params={
            "fields": "id,username,name,profile_picture_url,account_type",
            "access_token": access_token,
        },
        timeout=60,
    )
    me_data = me_resp.json()
    if me_resp.status_code >= 400 or ("id" not in me_data and "user_id" not in me_data):
        err_msg = me_data.get("error", {}).get("message") or str(me_data)
        raise ValueError(f"Failed to fetch Instagram info: {err_msg}")

    # Defensive ID extraction
    instagram_user_id = str(me_data.get("id") or me_data.get("user_id") or ig_user_id)
    if not instagram_user_id:
         raise ValueError("Instagram API did not return a valid User ID.")

    username = me_data.get("username", "instagram_user")
    name = me_data.get("name", username)
    picture = me_data.get("profile_picture_url", "")

    account_info = {
        "instagram_user_id": instagram_user_id,
        "username": username,
        "name": name,
        "picture": picture,
        "account_type": me_data.get("account_type", "Business"),
        "access_token": access_token,
        "token_type": "instagram_login",
    }
    _save_instagram_account(account_info)
    return {"instagram": [account_info]}


def _meta_graph_get(path: str, access_token: str, params: dict | None = None) -> dict:
    response = requests.get(
        f"https://graph.facebook.com/{META_GRAPH_VERSION}/{path.lstrip('/')}",
        params={**(params or {}), "access_token": access_token},
        timeout=60,
    )
    data = response.json()
    if response.status_code >= 400 or "error" in data:
        raise ValueError(data.get("error", {}).get("message") or str(data))
    return data


def _exchange_for_long_lived_meta_token(access_token: str) -> str:
    app_id = os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID")
    app_secret = os.getenv("META_APP_SECRET") or os.getenv("FACEBOOK_APP_SECRET")
    if not app_id or not app_secret:
        return access_token

    response = requests.get(
        f"https://graph.facebook.com/{META_GRAPH_VERSION}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": access_token,
        },
        timeout=60,
    )
    data = response.json()
    if response.status_code >= 400 or "error" in data:
        return access_token
    return data.get("access_token", access_token)


def _save_facebook_page(page: dict):
    page_id = page.get("page_id") or page.get("id")
    if not page_id:
        return
    token_path = FB_TOKENS_DIR / f"{page_id}.json"
    with open(token_path, "w") as f:
        json.dump(page, f, indent=2)


def _save_instagram_account(account: dict):
    token_path = IG_TOKENS_DIR / f"{account['instagram_user_id']}.json"
    with open(token_path, "w") as f:
        json.dump(account, f)


def exchange_facebook_code(code: str) -> dict:
    client_id = os.getenv("META_APP_ID") or os.getenv("FACEBOOK_APP_ID")
    client_secret = os.getenv("META_APP_SECRET") or os.getenv("FACEBOOK_APP_SECRET")
    if not client_id or not client_secret:
        raise ValueError("META_APP_ID / META_APP_SECRET must be set in .env")

    response = requests.get(
        f"https://graph.facebook.com/{META_GRAPH_VERSION}/oauth/access_token",
        params={
            "client_id": client_id,
            "redirect_uri": FB_REDIRECT_URI,
            "client_secret": client_secret,
            "code": code,
        },
        timeout=60,
    )
    token_data = response.json()
    if response.status_code >= 400 or "access_token" not in token_data:
        raise ValueError(f"Meta token exchange failed: {token_data}")

    access_token = _exchange_for_long_lived_meta_token(token_data["access_token"])
    return fetch_and_save_meta_accounts(access_token)


def fetch_and_save_meta_accounts(access_token: str) -> dict:
    pages_resp = _meta_graph_get(
        "me/accounts",
        access_token,
        params={
            "fields": "id,name,access_token,picture{url},fan_count,instagram_business_account{id,username,profile_picture_url,name}",
            "limit": 100,
        },
    )

    facebook_accounts = []
    instagram_accounts = []

    for page in pages_resp.get("data", []):
        if not isinstance(page, dict) or "id" not in page:
            continue

        page_info = {
            "page_id": page["id"],
            "name": page.get("name", "Facebook Page"),
            "access_token": page.get("access_token"),
            "picture": page.get("picture", {}).get("data", {}).get("url", ""),
            "fan_count": str(page.get("fan_count", "0")),
        }
        
        if page_info["access_token"]:
            _save_facebook_page(page_info)
            facebook_accounts.append(page_info)

        ig_account = page.get("instagram_business_account")
        if ig_account and isinstance(ig_account, dict) and "id" in ig_account:
            ig_info = {
                "instagram_user_id": ig_account["id"],
                "username": ig_account.get("username") or ig_account.get("name") or page.get("name"),
                "name": ig_account.get("name") or ig_account.get("username") or page.get("name"),
                "picture": ig_account.get("profile_picture_url", ""),
                "page_id": page["id"],
                "page_name": page.get("name"),
                "access_token": page.get("access_token"),
            }
            _save_instagram_account(ig_info)
            instagram_accounts.append(ig_info)

    if not facebook_accounts and not instagram_accounts:
        raise ValueError("No Facebook Pages or Instagram Business accounts found for this Meta account.")

    return {
        "facebook": facebook_accounts,
        "instagram": instagram_accounts,
    }


def exchange_linkedin_code(code: str) -> dict:
    client_id     = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    
    # 1. Exchange code for access token
    token_resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  LI_REDIRECT_URI,
            "client_id":     client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    ).json()

    if "access_token" not in token_resp:
        raise ValueError(f"LinkedIn Token Exchange failed: {token_resp}")

    access_token = token_resp["access_token"]
    
    # 2. Get user info
    return verify_and_save_linkedin_token(access_token)



def _save_linkedin_account(account_info: dict):
    """Save LinkedIn account info to tokens/linkedin/{sub}.json."""
    sub = account_info["person_urn"].split(":")[-1]
    token_path = LI_TOKENS_DIR / f"{sub}.json"
    with open(token_path, "w") as f:
        json.dump(account_info, f)


def verify_and_save_linkedin_token(token: str) -> dict:
    """Manual LinkedIn token verification."""
    from linkedin import fetch_linkedin_user
    person_data = fetch_linkedin_user(token)
    account_info = {
        "person_urn": person_data["id"],
        "name": person_data.get("name") or f"{person_data.get('given_name','')} {person_data.get('family_name','')}".strip() or person_data["id"],
        "picture": person_data.get("picture", ""),
        "email": person_data.get("email", ""),
        "access_token": token,
    }
    _save_linkedin_account(account_info)
    return account_info


def verify_and_save_instagram_token(token: str) -> dict:
    """Manual Instagram token verification using Instagram API flow."""
    client_secret = os.getenv("INSTAGRAM_APP_SECRET")
    
    # Try to exchange for long-lived if secret exists
    if client_secret:
        try:
            r = requests.get(
                "https://graph.instagram.com/access_token",
                params={
                    "grant_type": "ig_exchange_token",
                    "client_secret": client_secret,
                    "access_token": token,
                },
                timeout=30,
            )
            if r.status_code == 200:
                token = r.json().get("access_token", token)
        except Exception:
            pass

    # Fetch user profile
    r = requests.get(
        "https://graph.instagram.com/me",
        params={
            "fields": "user_id,username,name,profile_picture_url,account_type",
            "access_token": token,
        },
        timeout=30,
    )
    me_data = r.json()
    if r.status_code >= 400 or "id" not in me_data and "user_id" not in me_data:
        raise ValueError(f"Failed to verify Instagram token: {me_data.get('error', {}).get('message', 'Unknown error')}")

    ig_id = str(me_data.get("user_id") or me_data.get("id"))
    username = me_data.get("username", "instagram_user")
    
    account_info = {
        "instagram_user_id": ig_id,
        "username": username,
        "name": me_data.get("name", username),
        "picture": me_data.get("profile_picture_url", ""),
        "account_type": me_data.get("account_type", "Business"),
        "access_token": token,
        "token_type": "instagram_login",
    }
    _save_instagram_account(account_info)
    return account_info


def verify_and_save_facebook_token(token: str) -> dict:
    """Manual Facebook Page token verification."""
    # Use the token to get page details
    r = requests.get(
        f"https://graph.facebook.com/{META_GRAPH_VERSION}/me",
        params={
            "access_token": token,
            "fields": "id,name,picture{url},fan_count",
        },
        timeout=30,
    )
    data = r.json()
    if r.status_code >= 400 or "id" not in data:
        raise ValueError(f"Failed to verify Facebook token: {data.get('error', {}).get('message', 'Unknown error')}")

    account_info = {
        "page_id": data["id"],
        "name": data["name"],
        "access_token": token,
        "picture": data.get("picture", {}).get("data", {}).get("url", ""),
        "fan_count": str(data.get("fan_count", "0")),
    }
    
    # Save to Facebook tokens
    token_path = FB_TOKENS_DIR / f"{data['id']}.json"
    with open(token_path, "w") as f:
        json.dump(account_info, f, indent=2)
        
    return account_info


def get_linkedin_token(person_urn: str) -> str:
    sub = person_urn.split(":")[-1]
    token_path = LI_TOKENS_DIR / f"{sub}.json"
    if not token_path.exists():
        raise FileNotFoundError("LinkedIn account not found. Please reconnect.")
    
    with open(token_path, "r") as f:
        data = json.load(f)
    return data["access_token"]


def get_facebook_token(page_id: str) -> str:
    token_path = FB_TOKENS_DIR / f"{page_id}.json"
    if not token_path.exists():
        raise FileNotFoundError("Facebook Page not found. Please reconnect.")

    with open(token_path, "r") as f:
        data = json.load(f)
    return data["access_token"]


def get_instagram_account(instagram_user_id: str) -> dict:
    token_path = IG_TOKENS_DIR / f"{instagram_user_id}.json"
    if not token_path.exists():
        raise FileNotFoundError("Instagram account not found. Please reconnect.")

    with open(token_path, "r") as f:
        return json.load(f)


def list_connected_accounts() -> list:
    accounts = []
    
    # YouTube accounts
    for token_file in TOKENS_DIR.glob("*.pickle"):
        channel_id = token_file.stem
        try:
            yt = get_youtube_client(channel_id)
            r  = yt.channels().list(part="snippet,statistics", mine=True).execute()
            if r.get("items"):
                ch    = r["items"][0]
                stats = ch.get("statistics", {})
                accounts.append({
                    "platform":     "youtube",
                    "account_id":   channel_id,
                    "account_name": ch["snippet"]["title"],
                    "thumbnail":    ch["snippet"]["thumbnails"].get("default", {}).get("url", ""),
                    "subscribers":  stats.get("subscriberCount", "0"),
                    "video_count":  stats.get("videoCount", "0"),
                })
        except Exception:
            pass
            
    # LinkedIn accounts
    for token_file in LI_TOKENS_DIR.glob("*.json"):
        try:
            with open(token_file, "r") as f:
                data = json.load(f)
                accounts.append({
                    "platform":     "linkedin",
                    "account_id":   data["person_urn"],
                    "account_name": data["name"],
                    "thumbnail":    data.get("picture", ""),
                    "email":        data.get("email", ""),
                })
        except Exception:
            pass

    for token_file in FB_TOKENS_DIR.glob("*.json"):
        try:
            with open(token_file, "r") as f:
                data = json.load(f)
                accounts.append({
                    "platform": "facebook",
                    "account_id": data["page_id"],
                    "account_name": data["name"],
                    "thumbnail": data.get("picture", ""),
                    "followers": data.get("fan_count", "0"),
                })
        except Exception:
            pass

    for token_file in IG_TOKENS_DIR.glob("*.json"):
        try:
            with open(token_file, "r") as f:
                data = json.load(f)
                accounts.append({
                    "platform": "instagram",
                    "account_id": data["instagram_user_id"],
                    "account_name": data.get("username") or data.get("name"),
                    "thumbnail": data.get("picture", ""),
                    "page_name": data.get("page_name", ""),
                })
        except Exception:
            pass
            
    return accounts


def disconnect_account(platform: str, account_id: str) -> bool:
    if platform == "youtube":
        token_path = TOKENS_DIR / f"{account_id}.pickle"
    elif platform == "linkedin":
        sub = account_id.split(":")[-1]
        token_path = LI_TOKENS_DIR / f"{sub}.json"
    elif platform == "facebook":
        token_path = FB_TOKENS_DIR / f"{account_id}.json"
    elif platform == "instagram":
        token_path = IG_TOKENS_DIR / f"{account_id}.json"
        
        # Also clean up instagrapi session if it exists
        if token_path.exists():
            try:
                with open(token_path, "r") as f:
                    data = json.load(f)
                    username = data.get("username")
                    if username:
                        session_path = TOKENS_DIR / "instagram_sessions" / f"{username}.json"
                        if session_path.exists():
                            session_path.unlink()
            except Exception:
                pass
    else:
        return False
        
    if token_path.exists():
        token_path.unlink()
        return True
    return False
