import requests
import time
import os
from fastapi import HTTPException

def get_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def upload_image(token: str, person_urn: str, image_path: str) -> str:
    headers = get_headers(token)
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()

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

def upload_video(token: str, person_urn: str, video_path: str) -> str:
    headers = get_headers(token)
    
    with open(video_path, "rb") as f:
        video_bytes = f.read()

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
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
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
            
    return video_urn


def publish_linkedin_post(token: str, person_urn: str, message: str,
                 image_path: str = None, video_path: str = None):
    headers = get_headers(token)

    image_urn = None
    if image_path:
        image_urn = upload_image(token, person_urn, image_path)
        
    video_urn = None
    if video_path:
        video_urn = upload_video(token, person_urn, video_path)

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
