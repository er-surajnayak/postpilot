import os
import shutil
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from auth import (
    get_auth_url, exchange_code, list_connected_accounts,
    disconnect_account, verify_and_save_linkedin_token,
    get_linkedin_auth_url, exchange_linkedin_code,
    get_facebook_auth_url, exchange_facebook_code,
    get_instagram_auth_url, exchange_instagram_code,
    verify_and_save_instagram_token, verify_and_save_facebook_token,
)
from scheduler import add_job, get_all_jobs, get_job, delete_job, start_scheduler, stop_scheduler
from youtube import list_videos

load_dotenv(override=True)

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:3000",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Social Scheduler API", lifespan=lifespan)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth routes ───────────────────────────────────────────────

@app.get("/auth/login")
def auth_login():
    """Redirect user to Google OAuth consent screen."""
    url = get_auth_url()
    return RedirectResponse(url)


@app.get("/auth/callback")
def auth_callback(code: str = None, error: str = None, state: str = None):
    """Google redirects here after user approves."""
    if error or not code:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error=access_denied")
    try:
        account = exchange_code(code, state=state)
        name    = account["channel_name"].replace(" ", "%20")
        return RedirectResponse(
            f"{FRONTEND_URL}/connect?success=true&platform=youtube&channel={name}&id={account['channel_id']}"
        )
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error={str(e)}")


@app.get("/auth/linkedin/login")
def linkedin_login():
    """Redirect user to LinkedIn OAuth screen."""
    try:
        url = get_linkedin_auth_url()
        return RedirectResponse(url)
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error={str(e)}")


@app.get("/auth/linkedin/callback")
def linkedin_callback(code: str = None, error: str = None, state: str = None):
    """LinkedIn redirects here after user approves."""
    if error or not code:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error=access_denied")
    try:
        account = exchange_linkedin_code(code)
        name    = account["name"].replace(" ", "%20")
        return RedirectResponse(
            f"{FRONTEND_URL}/connect?success=true&platform=linkedin&channel={name}&id={account['person_urn']}"
        )
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error={str(e)}")


@app.get("/auth/facebook/login")
def facebook_login():
    """Redirect user to Meta OAuth screen."""
    try:
        url = get_facebook_auth_url()
        return RedirectResponse(url)
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error={str(e)}")


@app.get("/auth/facebook/callback")
def facebook_callback(code: str = None, error: str = None, state: str = None):
    """Meta redirects here after user approves."""
    if error or not code:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error=access_denied")
    try:
        accounts = exchange_facebook_code(code)
        display_name = None
        if accounts.get("facebook"):
            display_name = accounts["facebook"][0]["name"]
        elif accounts.get("instagram"):
            display_name = accounts["instagram"][0]["username"]
        display_name = (display_name or "Meta account").replace(" ", "%20")
        return RedirectResponse(
            f"{FRONTEND_URL}/connect?success=true&platform=facebook&channel={display_name}"
        )
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error={str(e)}")



@app.get("/auth/instagram/login")
def instagram_login():
    """Redirect user to Meta OAuth screen using the Instagram app."""
    try:
        url = get_instagram_auth_url()
        return RedirectResponse(url)
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error={str(e)}")


@app.get("/auth/instagram/callback")
def instagram_callback(code: str = None, error: str = None, state: str = None):
    """Meta redirects here after user approves Instagram permissions."""
    if error or not code:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error=access_denied")
    try:
        accounts = exchange_instagram_code(code)
        display_name = None
        if accounts.get("instagram"):
            display_name = accounts["instagram"][0].get("username")
        elif accounts.get("facebook"):
            display_name = accounts["facebook"][0]["name"]
        display_name = (display_name or "Instagram account").replace(" ", "%20")
        return RedirectResponse(
            f"{FRONTEND_URL}/connect?success=true&platform=instagram&channel={display_name}"
        )
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error={str(e)}")


@app.post("/auth/instagram/connect")
def instagram_connect(
    username: str = Form(...),
    password: str = Form(...),
    verification_code: str = Form(""),
):
    """Connect Instagram account via username + password (instagrapi)."""
    try:
        from instagram_private import login_with_credentials
        account = login_with_credentials(username.strip(), password, verification_code.strip())
        return {
            "success": True,
            "account_id": account["instagram_user_id"],
            "username": account["username"],
            "name": account.get("name", account["username"]),
            "thumbnail": account.get("picture", ""),
            "requires_2fa": False,
        }
    except ValueError as e:
        if str(e) == "2FA_REQUIRED":
            return {"success": False, "requires_2fa": True, "detail": "2FA code required"}
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login failed: {str(e)}")


@app.post("/auth/instagram/verify")
def instagram_verify(token: str = Form(...)):
    """Verify and save an Instagram access token entered manually."""
    try:
        account = verify_and_save_instagram_token(token)
        return {
            "success": True,
            "account_id": account["instagram_user_id"],
            "username": account["username"],
            "name": account.get("name", account["username"]),
            "thumbnail": account.get("picture", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/linkedin/connect")
def linkedin_connect(
    email: str = Form(...),
    password: str = Form(...),
):
    """Connect LinkedIn account via email + password (linkedin-api)."""
    try:
        from linkedin_private import login_with_credentials
        account = login_with_credentials(email.strip(), password)
        return {
            "success": True,
            "account_id": account["person_urn"],
            "name": account.get("name", email),
            "thumbnail": account.get("picture", ""),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login failed: {str(e)}")


@app.post("/auth/facebook/verify")
def facebook_verify(token: str = Form(...)):
    """Verify and save a Facebook Page access token entered manually."""
    try:
        account = verify_and_save_facebook_token(token)
        return {
            "success": True,
            "account_id": account["page_id"],
            "name": account["name"],
            "thumbnail": account["picture"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/linkedin/verify")
def linkedin_verify(token: str = Form(...)):
    """Verify and save LinkedIn manual access token."""
    try:
        account = verify_and_save_linkedin_token(token)
        return {
            "success": True,
            "account_id": account["person_urn"],
            "name": account["name"],
            "thumbnail": account["picture"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/accounts")
def get_accounts():
    """List all connected social accounts."""
    return list_connected_accounts()


@app.delete("/auth/accounts/{platform}/{account_id}")
def remove_account(platform: str, account_id: str):
    if disconnect_account(platform, account_id):
        return {"message": "Account disconnected"}
    raise HTTPException(status_code=404, detail="Account not found")


# ── Post routes ───────────────────────────────────────────────

@app.post("/posts/upload")
async def schedule_post(
    platform:     str        = Form("youtube"),
    account_id:   str        = Form(...),
    title:        str        = Form(""),          # YT: Title, LI: fallback message
    message:      str        = Form(""),          # LI: Message
    description:  str        = Form(""),          # YT: Description
    tags:         str        = Form(""),          # YT: comma-separated
    privacy:      str        = Form("private"),   # YT: privacy
    is_short:     bool       = Form(False),       # YT: is_short
    scheduled_at: str        = Form(None),        # ISO datetime string (local)
    timezone:     str        = Form("Asia/Kolkata"),
    notify:       bool       = Form(False),
    video:        UploadFile = File(None),
    image:        UploadFile = File(None),
):
    # Determine the file to save
    media_file = video or image
    media_path = None
    if media_file and media_file.filename:
        safe_name = Path(media_file.filename).name.replace(" ", "_")
        media_path = UPLOADS_DIR / f"{uuid.uuid4().hex}_{safe_name}"
        with open(media_path, "wb") as f:
            shutil.copyfileobj(media_file.file, f)

    post_data = {
        "platform":     platform,
        "account_id":   account_id,
        "title":        title,
        "message":      message,
        "description":  description,
        "tags":         [t.strip() for t in tags.split(",") if t.strip()],
        "privacy":      privacy,
        "is_short":     is_short,
        "scheduled_at": scheduled_at if (scheduled_at and scheduled_at != "null") else None,
        "timezone":     timezone,
        "notify":       notify,
    }

    job_id = add_job(post_data, str(media_path) if media_path else None)

    return {
        "job_id":  job_id,
        "message": "Scheduled" if (scheduled_at and scheduled_at != "null") else "Upload started",
        "status":  "queued",
    }


@app.get("/posts")
def get_posts():
    """Get all scheduled/published posts."""
    return get_all_jobs()


@app.get("/posts/{job_id}")
def get_post_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Post not found")
    return job


@app.delete("/posts/{job_id}")
def cancel_post(job_id: str):
    if delete_job(job_id):
        return {"message": "Post cancelled"}
    raise HTTPException(status_code=404, detail="Post not found")


# ── Internal YT data ──────────────────────────────────────────

@app.get("/youtube/{channel_id}/videos")
def get_channel_videos(channel_id: str, max_results: int = 20):
    try:
        return list_videos(channel_id, max_results)
    except FileNotFoundError:
        raise HTTPException(status_code=401, detail="Account not connected")


@app.get("/health")
def health():
    return {"status": "ok"}
