from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import time
import pytz
import os
import shutil
import tempfile
from datetime import datetime

app = FastAPI(title="LinkedIn Poster API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ────────────────────────────────────────────────────────────────────

class TokenVerifyRequest(BaseModel):
    access_token: str

class PostRequest(BaseModel):
    access_token: str
    person_urn: str
    message: str
    post_type: str  # "text" | "image" | "video"
    scheduled_at: Optional[str] = None  # ISO format datetime string
    tz_name: Optional[str] = "Asia/Kolkata"
    image_base64: Optional[str] = None
    video_url: Optional[str] = None

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def upload_image(token: str, person_urn: str, image_bytes: bytes) -> str:
    headers = get_headers(token)

    reg = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers,
        json={
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": person_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }
    ).json()

    if "value" not in reg:
        raise HTTPException(status_code=400, detail=f"Image registration failed: {reg}")

    upload_url = reg["value"]["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    image_urn = reg["value"]["asset"]

    requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {token}"},
        data=image_bytes
    )

    return image_urn


def publish_post(token: str, person_urn: str, message: str,
                 image_urn: str = None, video_urn: str = None):
    headers = get_headers(token)

    if image_urn:
        media_category = "IMAGE"
        media_block = [{
            "status": "READY",
            "description": {"text": ""},
            "media": image_urn,
            "title": {"text": ""}
        }]
    elif video_urn:
        media_category = "VIDEO"
        media_block = [{
            "status": "READY",
            "description": {"text": ""},
            "media": video_urn,
            "title": {"text": ""}
        }]
    else:
        media_category = "NONE"
        media_block = []

    body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": message},
                "shareMediaCategory": media_category,
                **( {"media": media_block} if media_block else {})
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    r = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=body
    ).json()

    if "errorDetailType" in r or ("message" in r and "id" not in r):
        raise HTTPException(status_code=400, detail=f"Post failed: {r}")

    post_id = r.get("id", "")
    post_url = f"https://www.linkedin.com/feed/update/{post_id}"
    return post_id, post_url


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "LinkedIn Poster API is running"}


@app.post("/auth/verify")
def verify_token(body: TokenVerifyRequest):
    r = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {body.access_token}"}
    ).json()

    if "error" in r or "sub" not in r:
        raise HTTPException(status_code=401, detail=f"Auth failed: {r}")

    return {
        "success": True,
        "name": r.get("name"),
        "email": r.get("email"),
        "picture": r.get("picture"),
        "person_urn": f"urn:li:person:{r['sub']}"
    }


@app.post("/post/text")
def post_text(
    access_token: str = Form(...),
    person_urn: str = Form(...),
    message: str = Form(...),
    scheduled_at: Optional[str] = Form(None),
    tz_name: str = Form("Asia/Kolkata"),
):
    if scheduled_at:
        try:
            tz = pytz.timezone(tz_name)
            naive_dt = datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M")
            local_dt = tz.localize(naive_dt)
            wait_secs = local_dt.astimezone(pytz.utc).timestamp() - datetime.utcnow().timestamp()
            if wait_secs > 0:
                time.sleep(wait_secs)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid schedule time: {e}")

    post_id, post_url = publish_post(access_token, person_urn, message)
    return {"success": True, "post_id": post_id, "post_url": post_url}


@app.post("/post/image")
async def post_image(
    access_token: str = Form(...),
    person_urn: str = Form(...),
    message: str = Form(...),
    image: UploadFile = File(...),
    scheduled_at: Optional[str] = Form(None),
    tz_name: str = Form("Asia/Kolkata"),
):
    if scheduled_at:
        try:
            tz = pytz.timezone(tz_name)
            naive_dt = datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M")
            local_dt = tz.localize(naive_dt)
            wait_secs = local_dt.astimezone(pytz.utc).timestamp() - datetime.utcnow().timestamp()
            if wait_secs > 0:
                time.sleep(wait_secs)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid schedule time: {e}")

    image_bytes = await image.read()

    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image exceeds 5MB LinkedIn limit")

    image_urn = upload_image(access_token, person_urn, image_bytes)
    post_id, post_url = publish_post(access_token, person_urn, message, image_urn=image_urn)
    return {"success": True, "post_id": post_id, "post_url": post_url}


@app.post("/post/video")
async def post_video(
    access_token: str = Form(...),
    person_urn: str = Form(...),
    message: str = Form(...),
    video: UploadFile = File(...),
    scheduled_at: Optional[str] = Form(None),
    tz_name: str = Form("Asia/Kolkata"),
):
    headers = get_headers(access_token)
    video_bytes = await video.read()

    if len(video_bytes) > 200 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Video exceeds 200MB LinkedIn limit")

    reg = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers,
        json={
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                "owner": person_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }
    ).json()

    if "value" not in reg:
        raise HTTPException(status_code=400, detail=f"Video registration failed: {reg}")

    upload_url = reg["value"]["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    video_urn = reg["value"]["asset"]

    CHUNK_SIZE = 4 * 1024 * 1024
    offset = 0
    while offset < len(video_bytes):
        chunk = video_bytes[offset:offset + CHUNK_SIZE]
        requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/octet-stream"},
            data=chunk
        )
        offset += len(chunk)

    # Poll for processing
    for _ in range(30):
        time.sleep(5)
        status = requests.get(
            f"https://api.linkedin.com/v2/assets/{video_urn.split(':')[-1]}",
            headers=headers
        ).json()
        state = status.get("recipes", [{}])[0].get("status", "")
        if state == "AVAILABLE":
            break
        elif state == "PROCESSING_FAILED":
            raise HTTPException(status_code=500, detail="Video processing failed on LinkedIn's end")

    if scheduled_at:
        try:
            tz = pytz.timezone(tz_name)
            naive_dt = datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M")
            local_dt = tz.localize(naive_dt)
            wait_secs = local_dt.astimezone(pytz.utc).timestamp() - datetime.utcnow().timestamp()
            if wait_secs > 0:
                time.sleep(wait_secs)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid schedule time: {e}")

    post_id, post_url = publish_post(access_token, person_urn, message, video_urn=video_urn)
    return {"success": True, "post_id": post_id, "post_url": post_url}
