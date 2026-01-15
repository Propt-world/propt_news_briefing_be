from pydantic import BaseModel, Field

class ScriptValidationResult(BaseModel):
    """
    Structured output for the Script Validator (Critic).
    """
    accuracy_score: float = Field(..., ge=0, le=10, description="Score (0-10) for contextual accuracy against source scripts.")
    hallucination_count: int = Field(..., ge=0, description="Count of hallucinated facts (must be 0).")
    feedback: str = Field(..., description="Specific, actionable feedback to fix issues.")
    
    # Derived field (calculated by LLM or logic)
    is_valid: bool = Field(..., description="True ONLY if accuracy >= 8.5 AND hallucination_count == 0.")