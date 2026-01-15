from pydantic import BaseModel, Field
from typing import Optional

class ReporterOutput(BaseModel):
    headline: str = Field(..., description="A punchy, broadcast-style headline")
    script_segment: str = Field(..., description="The summarized news script written for the ear")
    importance_score: int = Field(..., ge=1, le=10, description="News value score (1-10)")
    reasoning: Optional[str] = Field(None, description="Reasoning for the score")