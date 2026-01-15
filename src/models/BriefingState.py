from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from src.models.ArticleScript import ArticleScript
from src.models.RawArticleModel import RawArticleModel
from src.models.FinalBroadcastScript import FinalBroadcastScript
from src.models.BroadcastScriptAttempt import BroadcastScriptAttempt

class BriefingState(BaseModel):
    """
    The main state object for the NewsCast audio generation workflow.
    """
    # --- Input Context ---
    user_id: str
    config: Dict[str, Any] = Field(default_factory=dict)

    # --- Data Layer ---
    raw_articles: List[RawArticleModel] = Field(default_factory=list)

    # --- Editorial Layer ---
    drafted_scripts: List[ArticleScript] = Field(default_factory=list)

    # --- Script Generation Loop ---
    current_script_draft: Optional[FinalBroadcastScript] = None # Holds the latest draft being validated
    script_attempts: List[BroadcastScriptAttempt] = Field(default_factory=list) # History of all tries
    script_validation_count: int = 0

    # --- Final Outputs ---
    final_script_text: Optional[str] = None
    translated_script_text: Optional[str] = None
    audio_s3_url: Optional[str] = None
    final_audio_transcript: Optional[str] = None

    error: Optional[str] = None