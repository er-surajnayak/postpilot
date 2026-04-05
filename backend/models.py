from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SchedulePost(BaseModel):
    platform:     str             # youtube | linkedin
    account_id:   str             # channel_id for YT, person_urn for LI
    title:        Optional[str]   = ""  # YT Title / LI Message (if message is empty)
    description:  Optional[str]   = ""  # YT Description
    message:      Optional[str]   = ""  # LI Message
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
    media_id:     Optional[str]   = None # video_id for YT, urn for LI
    media_url:    Optional[str]   = None # video_url for YT, post_url for LI
    scheduled_at: Optional[str]   = None
    error:        Optional[str]   = None
    created_at:   str

