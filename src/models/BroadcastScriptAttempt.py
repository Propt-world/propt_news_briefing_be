from pydantic import BaseModel
from src.models.FinalBroadcastScript import FinalBroadcastScript
from src.models.ScriptValidationResult import ScriptValidationResult

class BroadcastScriptAttempt(BaseModel):
    """
    Wrapper to store a generation attempt and its corresponding validation.
    Used for history tracking and selecting the best fallback.
    """
    script_content: FinalBroadcastScript
    validation: ScriptValidationResult