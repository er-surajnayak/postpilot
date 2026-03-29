from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SchedulePost(BaseModel):
    channel_id:   str
    title:        str
    description:  str             = ""
    tags:         List[str]       = []
    privacy:      str             = "private"   # private | unlisted | public
    is_short:     bool            = False
    scheduled_at: Optional[str]   = None        # ISO string e.g. "2026-03-29T14:50:00"
    timezone:     str             = "Asia/Kolkata"
    notify:       bool            = False


class PostStatus(BaseModel):
    post_id:      str
    channel_id:   str
    title:        str
    status:       str             # queued | uploading | scheduled | published | failed
    video_id:     Optional[str]   = None
    video_url:    Optional[str]   = None
    scheduled_at: Optional[str]   = None
    error:        Optional[str]   = None
    created_at:   str
