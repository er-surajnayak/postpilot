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


def add_job(post_data: dict, video_path: str, thumbnail_path: str = None) -> str:
    """Queue an upload job. Returns job_id."""
    job_id = str(uuid.uuid4())[:8]
    jobs   = load_jobs()

    jobs[job_id] = {
        "job_id":         job_id,
        "channel_id":     post_data["channel_id"],
        "title":          post_data["title"],
        "status":         "queued",
        "video_path":     video_path,
        "thumbnail_path": thumbnail_path,
        "post_data":      post_data,
        "video_id":       None,
        "video_url":      None,
        "error":          None,
        "created_at":     datetime.now(timezone.utc).isoformat(),
    }
    save_jobs(jobs)

    # If scheduled, add to APScheduler
    scheduled_at = post_data.get("scheduled_at")
    if scheduled_at:
        tz      = pytz.timezone(post_data.get("timezone", "Asia/Kolkata"))
        run_dt  = datetime.fromisoformat(scheduled_at.replace("Z", ""))
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

    jobs = load_jobs()
    if job_id not in jobs:
        return

    job = jobs[job_id]
    job["status"] = "uploading"
    save_jobs(jobs)

    try:
        pd = job["post_data"]
        result = upload_video(
            channel_id   = pd["channel_id"],
            file_path    = job["video_path"],
            title        = pd["title"],
            description  = pd.get("description", ""),
            tags         = pd.get("tags", []),
            privacy      = pd.get("privacy", "private"),
            scheduled_at = pd.get("scheduled_at"),
            tz_name      = pd.get("timezone", "Asia/Kolkata"),
            is_short     = pd.get("is_short", False),
            notify       = pd.get("notify", False),
        )

        job["video_id"]  = result["video_id"]
        job["video_url"] = result["video_url"]
        job["status"]    = "scheduled" if pd.get("scheduled_at") else "published"

        # Upload thumbnail if provided
        if job.get("thumbnail_path"):
            try:
                upload_thumbnail(pd["channel_id"], result["video_id"], job["thumbnail_path"])
            except Exception as e:
                job["error"] = f"Video uploaded but thumbnail failed: {e}"

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
            run_dt  = datetime.fromisoformat(scheduled_at.replace("Z", ""))
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
