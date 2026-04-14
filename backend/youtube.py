import os
import time
import pytz
from datetime import datetime
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from auth import get_youtube_client

CATEGORIES = {
    "Entertainment":        "24",
    "Education":            "27",
    "Science & Technology": "28",
    "People & Blogs":       "22",
    "Music":                "10",
    "Gaming":               "20",
    "Comedy":               "23",
    "News & Politics":      "25",
    "Howto & Style":        "26",
    "Sports":               "17",
}


def to_utc_string(dt_str: str, tz_name: str) -> str:
    tz = pytz.timezone(tz_name)
    # Accept ISO format string correctly
    if dt_str.endswith("Z"):
        aware = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    else:
        naive = datetime.fromisoformat(dt_str)
        if naive.tzinfo is None:
            aware = tz.localize(naive)
        else:
            aware = naive
    return aware.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def upload_video(
    channel_id:   str,
    file_path:    str,
    title:        str,
    description:  str  = "",
    tags:         list = None,
    privacy:      str  = "private",
    scheduled_at: str  = None,
    tz_name:      str  = "Asia/Kolkata",
    is_short:     bool = False,
    notify:       bool = False,
    on_progress=None,   # optional callback(pct: int)
) -> dict:

    yt = get_youtube_client(channel_id)

    # Shorts adjustments
    if is_short:
        if "#Shorts" not in title and "#shorts" not in title:
            title = title + " #Shorts"
        tags = list(set((tags or []) + ["Shorts", "YouTubeShorts", "Short"]))

    publish_at_str = None
    if scheduled_at:
        publish_at_str = to_utc_string(scheduled_at, tz_name)

    body = {
        "snippet": {
            "title":           title[:100],
            "description":     description[:5000],
            "tags":            tags or [],
            "categoryId":      "22",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus":           "private" if publish_at_str else privacy,
            "selfDeclaredMadeForKids": False,
            "notifySubscribers":       notify,
        },
    }

    if publish_at_str:
        body["status"]["publishAt"] = publish_at_str

    media   = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status and on_progress:
                on_progress(int(status.progress() * 100))
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                time.sleep(5)
            else:
                raise

    video_id  = response["id"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    return {
        "video_id":     video_id,
        "video_url":    video_url,
        "title":        title,
        "privacy":      body["status"]["privacyStatus"],
        "scheduled_at": publish_at_str,
        "is_short":     is_short,
    }


def upload_thumbnail(channel_id: str, video_id: str, image_path: str) -> bool:
    yt  = get_youtube_client(channel_id)
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    media = MediaFileUpload(image_path, mimetype=mime)
    yt.thumbnails().set(videoId=video_id, media_body=media).execute()
    return True


def list_videos(channel_id: str, max_results: int = 20) -> list:
    yt = get_youtube_client(channel_id)
    r  = yt.search().list(
        part="snippet", forMine=True, type="video",
        order="date", maxResults=max_results
    ).execute()
    videos = []
    for item in r.get("items", []):
        vid_id = item["id"]["videoId"]
        videos.append({
            "video_id":  vid_id,
            "title":     item["snippet"]["title"],
            "published": item["snippet"]["publishedAt"],
            "url":       f"https://www.youtube.com/watch?v={vid_id}",
            "thumbnail": item["snippet"]["thumbnails"].get("default", {}).get("url", ""),
        })
    return videos
