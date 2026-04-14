import uuid
import json
import pytz
from pathlib import Path
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

JOBS_FILE = Path("jobs.json")
scheduler = BackgroundScheduler(
    timezone="UTC",
    job_defaults={"misfire_grace_time": 86400},  # allow up to 24h late
)


def load_jobs() -> dict:
    if JOBS_FILE.exists():
        return json.loads(JOBS_FILE.read_text())
    return {}


def save_jobs(jobs: dict):
    JOBS_FILE.write_text(json.dumps(jobs, indent=2, default=str))


def add_job(post_data: dict, media_path: str = None, thumbnail_path: str = None) -> str:
    """Queue an upload job. Returns job_id."""
    job_id = str(uuid.uuid4())[:8]
    jobs   = load_jobs()

    jobs[job_id] = {
        "job_id":         job_id,
        "platform":       post_data["platform"],
        "account_id":     post_data["account_id"],
        "title":          post_data.get("title") or post_data.get("message")[:100],
        "status":         "queued",
        "media_path":     media_path,
        "thumbnail_path": thumbnail_path,
        "post_data":      post_data,
        "media_id":       None,
        "media_url":      None,
        "error":          None,
        "created_at":     datetime.now(timezone.utc).isoformat(),
    }
    save_jobs(jobs)

    # If scheduled, add to APScheduler
    scheduled_at = post_data.get("scheduled_at")
    if scheduled_at:
        tz_name = post_data.get("timezone", "Asia/Kolkata")
        tz = pytz.timezone(tz_name)
        
        # Parse ISO format string correctly
        if scheduled_at.endswith("Z"):
            # It's UTC from frontend
            run_dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        else:
            try:
                run_dt = datetime.fromisoformat(scheduled_at)
            except ValueError:
                # fallback for older formats
                run_dt = datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M")
            
            if run_dt.tzinfo is None:
                run_dt = tz.localize(run_dt)

        scheduler.add_job(
            run_upload_job,
            trigger=DateTrigger(run_date=run_dt),
            args=[job_id],
            id=job_id,
            replace_existing=True,
        )
    else:
        # Upload immediately in background
        scheduler.add_job(run_upload_job, args=[job_id], id=job_id, replace_existing=True)

    return job_id


def run_upload_job(job_id: str):
    """Called by scheduler — does the actual upload."""
    from youtube import upload_video, upload_thumbnail
    from linkedin import publish_linkedin_post
    from meta import publish_facebook_post, publish_instagram_post
    from auth import get_linkedin_token, get_facebook_token, get_instagram_account

    jobs = load_jobs()
    if job_id not in jobs:
        return

    job = jobs[job_id]
    job["status"] = "uploading"
    save_jobs(jobs)

    try:
        pd = job["post_data"]
        platform = pd.get("platform", "youtube")
        
        if platform == "youtube":
            result = upload_video(
                channel_id   = pd["account_id"],
                file_path    = job["media_path"],
                title        = pd["title"],
                description  = pd.get("description", ""),
                tags         = pd.get("tags", []),
                privacy      = pd.get("privacy", "private"),
                scheduled_at = pd.get("scheduled_at"),
                tz_name      = pd.get("timezone", "Asia/Kolkata"),
                is_short     = pd.get("is_short", False),
                notify       = pd.get("notify", False),
            )
            job["media_id"]  = result["video_id"]
            job["media_url"] = result["video_url"]
            
            # Upload thumbnail if provided
            if job.get("thumbnail_path"):
                try:
                    upload_thumbnail(pd["account_id"], result["video_id"], job["thumbnail_path"])
                except Exception as e:
                    job["error"] = f"Video uploaded but thumbnail failed: {e}"
                    
        elif platform == "linkedin":
            from pathlib import Path as _Path
            li_account   = json.loads((_Path("tokens/linkedin") / f"{pd['account_id'].split(':')[-1]}.json").read_text()) \
                           if (_Path("tokens/linkedin") / f"{pd['account_id'].split(':')[-1]}.json").exists() else {}
            token_type   = li_account.get("token_type", "oauth")
            email        = li_account.get("email", "")
            session_file = _Path(f"tokens/linkedin_sessions/{email}.json")
            use_private  = (token_type == "linkedin_private") or session_file.exists()

            if use_private and email:
                from linkedin_private import publish_post_with_media
                post_id, post_url = publish_post_with_media(
                    person_urn = pd["account_id"],
                    email      = email,
                    text       = pd.get("message") or pd.get("title") or "",
                    media_path = job["media_path"],
                )
            else:
                token = get_linkedin_token(pd["account_id"])
                img_path = None
                vid_path = None
                if job["media_path"]:
                    ext = job["media_path"].split(".")[-1].lower()
                    if ext in ["mp4", "mov", "avi"]:
                        vid_path = job["media_path"]
                    else:
                        img_path = job["media_path"]
                post_id, post_url = publish_linkedin_post(
                    token      = token,
                    person_urn = pd["account_id"],
                    message    = pd.get("message") or pd.get("title"),
                    image_path = img_path,
                    video_path = vid_path,
                )
            job["media_id"]  = post_id
            job["media_url"] = post_url

        elif platform == "facebook":
            token = get_facebook_token(pd["account_id"])
            post_id, post_url = publish_facebook_post(
                page_id = pd["account_id"],
                access_token = token,
                message = pd.get("message") or pd.get("title"),
                media_path = job["media_path"],
                title = pd.get("title", ""),
            )
            job["media_id"] = post_id
            job["media_url"] = post_url

        elif platform == "instagram":
            from pathlib import Path as _Path
            account    = get_instagram_account(pd["account_id"])
            username   = account.get("username", "")
            token_type = account.get("token_type")

            # Detection logic:
            # 1. Does an active instagrapi session file exist for this username?
            # 2. Is the token_type explicitly set to "instagrapi"?
            session_file = _Path(f"tokens/instagram_sessions/{username}.json")
            use_instagrapi = (username and session_file.exists()) or (token_type == "instagrapi")

            if use_instagrapi:
                # Username/password connected — use instagrapi (no public URL needed)
                from instagram_private import publish_photo, publish_video
                media_path = job["media_path"]
                caption    = pd.get("message") or pd.get("title") or ""
                ext        = (media_path or "").rsplit(".", 1)[-1].lower()
                if ext in {"mp4", "mov", "avi", "mkv", "webm"}:
                    post_id, post_url = publish_video(username, media_path, caption)
                else:
                    post_id, post_url = publish_photo(username, media_path, caption)
            else:
                # Token-based — use Meta Graph API
                post_id, post_url = publish_instagram_post(
                    instagram_user_id = pd["account_id"],
                    access_token      = account["access_token"],
                    caption           = pd.get("message") or pd.get("title"),
                    media_path        = job["media_path"],
                    token_type        = token_type,
                )
            job["media_id"]  = post_id
            job["media_url"] = post_url

        else:
            raise ValueError(f"Unsupported platform: {platform}")

        job["status"]    = "scheduled" if pd.get("scheduled_at") else "published"

    except Exception as e:
        job["status"] = "failed"
        job["error"]  = str(e)

    jobs[job_id] = job
    save_jobs(jobs)



def get_all_jobs() -> list:
    return list(load_jobs().values())


def get_job(job_id: str) -> dict:
    return load_jobs().get(job_id)


def delete_job(job_id: str) -> bool:
    jobs = load_jobs()
    if job_id in jobs:
        del jobs[job_id]
        save_jobs(jobs)
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
        return True
    return False


def reload_pending_jobs():
    """Re-register queued jobs from jobs.json after a server restart."""
    jobs = load_jobs()
    now  = datetime.now(timezone.utc)

    for job_id, job in jobs.items():
        if job["status"] != "queued":
            continue

        scheduled_at = job["post_data"].get("scheduled_at")
        if scheduled_at:
            tz_name = job["post_data"].get("timezone", "Asia/Kolkata")
            tz      = pytz.timezone(tz_name)
            
            if scheduled_at.endswith("Z"):
                run_dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
            else:
                run_dt = datetime.fromisoformat(scheduled_at)
                if run_dt.tzinfo is None:
                    run_dt = tz.localize(run_dt)

            # If the time has passed, run it immediately
            if run_dt <= now:
                scheduler.add_job(run_upload_job, args=[job_id], id=job_id, replace_existing=True)
            else:
                scheduler.add_job(
                    run_upload_job,
                    trigger=DateTrigger(run_date=run_dt),
                    args=[job_id],
                    id=job_id,
                    replace_existing=True,
                )
        else:
            # Immediate job that was never executed — run now
            scheduler.add_job(run_upload_job, args=[job_id], id=job_id, replace_existing=True)


def check_scheduled_jobs():
    """Periodically transition 'scheduled' → 'published' once the publish time passes."""
    jobs = load_jobs()
    now  = datetime.now(timezone.utc)
    changed = False

    for job_id, job in jobs.items():
        if job["status"] != "scheduled":
            continue
        scheduled_at = job["post_data"].get("scheduled_at")
        if not scheduled_at:
            continue
        run_dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        if run_dt.tzinfo is None:
            run_dt = run_dt.replace(tzinfo=timezone.utc)
        if now >= run_dt:
            job["status"] = "published"
            changed = True

    if changed:
        save_jobs(jobs)


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        reload_pending_jobs()
        # Check every minute if scheduled posts have gone live
        scheduler.add_job(
            check_scheduled_jobs,
            trigger=IntervalTrigger(minutes=1),
            id="__check_scheduled__",
            replace_existing=True,
        )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
