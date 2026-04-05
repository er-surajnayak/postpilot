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

# In-memory store for PKCE code_verifiers, keyed by OAuth state
_verifiers: dict[str, str] = {}

BACKEND_URL  = os.getenv("BACKEND_URL",  "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

REDIRECT_URI     = f"{BACKEND_URL}/auth/callback"
LI_REDIRECT_URI  = f"{BACKEND_URL}/auth/linkedin/callback"



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



def verify_and_save_linkedin_token(access_token: str) -> dict:
    r = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    if "error" in r or "sub" not in r:
        raise ValueError(f"LinkedIn Auth failed: {r}")

    person_urn = f"urn:li:person:{r['sub']}"
    account_info = {
        "access_token": access_token,
        "person_urn": person_urn,
        "name": r.get("name"),
        "email": r.get("email"),
        "picture": r.get("picture"),
    }

    token_path = LI_TOKENS_DIR / f"{r['sub']}.json"
    with open(token_path, "w") as f:
        json.dump(account_info, f)

    return account_info


def get_linkedin_token(person_urn: str) -> str:
    sub = person_urn.split(":")[-1]
    token_path = LI_TOKENS_DIR / f"{sub}.json"
    if not token_path.exists():
        raise FileNotFoundError("LinkedIn account not found. Please reconnect.")
    
    with open(token_path, "r") as f:
        data = json.load(f)
    return data["access_token"]


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
            
    return accounts


def disconnect_account(platform: str, account_id: str) -> bool:
    if platform == "youtube":
        token_path = TOKENS_DIR / f"{account_id}.pickle"
    else:
        # account_id for LinkedIn is the person_urn
        sub = account_id.split(":")[-1]
        token_path = LI_TOKENS_DIR / f"{sub}.json"
        
    if token_path.exists():
        token_path.unlink()
        return True
    return False