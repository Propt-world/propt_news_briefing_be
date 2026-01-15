from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserBriefingSchedule(BaseModel):
    """
    MongoDB Document Schema.
    """
    id: str = Field(alias="_id")
    user_id: str
    duration: int
    is_active: bool
    voice: str
    scheduled_time_utc: str
    language: str
    last_run_date: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True