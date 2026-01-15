from pydantic import BaseModel, Field

class BriefingScheduleRequest(BaseModel):
    """
    Input payload for creating/updating a schedule.
    """
    user_id: str = Field(..., description="Unique identifier for the user")
    duration: int = Field(..., gt=0, description="Target duration in minutes")
    enable_daily_briefing: bool
    voice: str = Field("marin", description="Voice ID")
    time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="UTC time in HH:MM format")
    language: str = Field("eng", pattern="^(eng|ar)$", description="Language: 'eng' or 'ar'")