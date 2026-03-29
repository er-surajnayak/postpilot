import os
import shutil
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv

from auth import get_auth_url, exchange_code, list_connected_accounts, disconnect_account
from models import SchedulePost
from scheduler import add_job, get_all_jobs, get_job, delete_job, start_scheduler, stop_scheduler
from youtube import list_videos

load_dotenv()

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Social Scheduler API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
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
            f"{FRONTEND_URL}/connect?success=true&channel={name}&id={account['channel_id']}"
        )
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/connect?error={str(e)}")


@app.get("/auth/accounts")
def get_accounts():
    """List all connected YouTube accounts."""
    return list_connected_accounts()


@app.delete("/auth/accounts/{channel_id}")
def remove_account(channel_id: str):
    if disconnect_account(channel_id):
        return {"message": "Account disconnected"}
    raise HTTPException(status_code=404, detail="Account not found")


# ── Post routes ───────────────────────────────────────────────

@app.post("/posts/upload")
async def schedule_post(
    channel_id:   str        = Form(...),
    title:        str        = Form(...),
    description:  str        = Form(""),
    tags:         str        = Form(""),          # comma-separated
    privacy:      str        = Form("private"),
    is_short:     bool       = Form(False),
    scheduled_at: str        = Form(None),        # ISO datetime string or empty
    timezone:     str        = Form("Asia/Kolkata"),
    notify:       bool       = Form(False),
    video:        UploadFile = File(...),
    thumbnail:    UploadFile = File(None),
):
    # Save video file
    video_path = UPLOADS_DIR / video.filename
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    # Save thumbnail if provided
    thumb_path = None
    if thumbnail and thumbnail.filename:
        thumb_path = UPLOADS_DIR / thumbnail.filename
        with open(thumb_path, "wb") as f:
            shutil.copyfileobj(thumbnail.file, f)

    post_data = {
        "channel_id":   channel_id,
        "title":        title,
        "description":  description,
        "tags":         [t.strip() for t in tags.split(",") if t.strip()],
        "privacy":      privacy,
        "is_short":     is_short,
        "scheduled_at": scheduled_at or None,
        "timezone":     timezone,
        "notify":       notify,
    }

    job_id = add_job(post_data, str(video_path), str(thumb_path) if thumb_path else None)

    return {
        "job_id":  job_id,
        "message": "Scheduled" if scheduled_at else "Upload started",
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


# ── YouTube data routes ───────────────────────────────────────

@app.get("/youtube/{channel_id}/videos")
def get_channel_videos(channel_id: str, max_results: int = 20):
    try:
        return list_videos(channel_id, max_results)
    except FileNotFoundError:
        raise HTTPException(status_code=401, detail="Account not connected")


@app.get("/health")
def health():
    return {"status": "ok"}
