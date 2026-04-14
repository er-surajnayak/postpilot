from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SchedulePost(BaseModel):
    platform:     str             # youtube | linkedin | facebook | instagram
    account_id:   str             # channel_id, urn, page_id, or instagram_user_id
    title:        Optional[str]   = ""  # YT title / fallback caption
    description:  Optional[str]   = ""  # YT description
    message:      Optional[str]   = ""  # LI/FB/IG caption
    tags:         List[str]       = []
    privacy:      str             = "private"
    is_short:     bool            = False
    scheduled_at: Optional[str]   = None
    timezone:     str             = "Asia/Kolkata"
    notify:       bool            = False
    media_url:    Optional[str]   = None # For LinkedIn video URL or similar


class PostStatus(BaseModel):
    post_id:      str
    platform:     str
    account_id:   str
    account_name: Optional[str]   = None
    title:        str
    status:       str             # queued | uploading | scheduled | published | failed
    media_id:     Optional[str]   = None # platform-specific media/post id
    media_url:    Optional[str]   = None # video_url/post_url/permalink
    scheduled_at: Optional[str]   = None
    error:        Optional[str]   = None
    created_at:   str
