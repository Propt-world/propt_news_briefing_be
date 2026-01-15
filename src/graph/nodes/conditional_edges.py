from src.models.BriefingState import BriefingState

def check_script_quality(state: BriefingState) -> str:
    """
    Conditional edge for the Audio Briefing Workflow.
    Decides if the broadcast script needs revision based on the Critic's output.
    
    Returns:
        - "pass": If validation succeeded.
        - "force_end": If max retries (3) reached (goes to fallback).
        - "retry": If validation failed and retries remain.
    """
    attempts = state.script_attempts
    
    # Safety check: if no attempts exist yet, retry (should not happen in normal flow)
    if not attempts:
        return "retry"
        
    last_result = attempts[-1].validation
    
    # 1. Perfect Pass
    if last_result.is_valid:
        print("[EDGE] Script Passed Validation.")
        return "pass"
        
    # 2. Max Retries Reached -> Force Selection
    # We allow 3 attempts (0, 1, 2). If count is 3, we stop.
    if state.script_validation_count >= 3:
        print("[EDGE] Max retries reached. Forcing selection.")
        return "force_end"
        
    # 3. Fail -> Retry
    print(f"[EDGE] Script Failed (Attempt {state.script_validation_count}). Retrying.")
    return "retry"


def check_briefing_language(state: BriefingState) -> str:
    """
    Conditional edge for Language Routing.
    Decides whether to translate text or proceed directly to audio generation.
    
    Returns:
        - "translate": If language is Arabic ('ar').
        - "generate_audio": If language is English ('eng').
    """
    lang = state.config.get("language", "eng")
    
    if lang == "ar":
        print("[EDGE] Language is Arabic -> Translating.")
        return "translate"
    else:
        print("[EDGE] Language is English -> Producing Audio.")
        return "generate_audio"