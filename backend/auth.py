import os
import json
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'      # allow http localhost
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'       # relax scope checking

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]

TOKENS_DIR = Path("tokens")
TOKENS_DIR.mkdir(exist_ok=True)

# In-memory store for PKCE code_verifiers, keyed by OAuth state
_verifiers: dict[str, str] = {}

BACKEND_URL  = os.getenv("BACKEND_URL",  "https://postpilot-4tud.onrender.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://postpilot-red-tau.vercel.app")
REDIRECT_URI = f"{BACKEND_URL}/auth/callback"


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
    # Save the PKCE code_verifier so exchange_code can use it
    _verifiers[state] = flow.code_verifier
    return auth_url


def exchange_code(code: str, state: str | None = None) -> dict:
    """Exchange auth code for credentials, save token, return channel info."""
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    flow = get_flow()

    # Restore the PKCE code_verifier from the original auth request
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


def list_connected_accounts() -> list:
    accounts = []
    for token_file in TOKENS_DIR.glob("*.pickle"):
        channel_id = token_file.stem
        try:
            yt = get_youtube_client(channel_id)
            r  = yt.channels().list(part="snippet,statistics", mine=True).execute()
            if r.get("items"):
                ch    = r["items"][0]
                stats = ch.get("statistics", {})
                accounts.append({
                    "channel_id":   channel_id,
                    "channel_name": ch["snippet"]["title"],
                    "thumbnail":    ch["snippet"]["thumbnails"].get("default", {}).get("url", ""),
                    "subscribers":  stats.get("subscriberCount", "0"),
                    "video_count":  stats.get("videoCount", "0"),
                })
        except Exception:
            pass
    return accounts


def disconnect_account(channel_id: str) -> bool:
    token_path = TOKENS_DIR / f"{channel_id}.pickle"
    if token_path.exists():
        token_path.unlink()
        return True
    return False