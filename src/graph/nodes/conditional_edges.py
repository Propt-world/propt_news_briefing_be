from src.models.BriefingState import BriefingState

def check_script_quality(state: BriefingState) -> str:
    """
    Conditional edge for the Audio Briefing Workflow.
    Decides if the broadcast script needs revision based on the Critic's output.
    """
    # 1. Immediate Fail on System Error (Prevents Loops)
    if state.error:
        print(f"[EDGE] System Error Detected: {state.error}. Stopping.")
        return "error" # Maps to END in the graph

    attempts = state.script_attempts
    
    # 2. Safety: If no attempts exist (e.g. initial generation failed silently), 
    # we must prevent an infinite loop.
    if not attempts:
        if state.script_validation_count >= 3:
             print("[EDGE] No attempts generated after 3 tries. Stopping.")
             return "error"
        return "retry"
        
    last_result = attempts[-1].validation
    
    # 3. Perfect Pass
    if last_result.is_valid:
        print("[EDGE] Script Passed Validation.")
        return "pass"
        
    # 4. Max Retries Reached -> Force Selection
    if state.script_validation_count >= 3:
        print("[EDGE] Max retries reached. Forcing selection.")
        return "force_end"
        
    # 5. Fail -> Retry
    print(f"[EDGE] Script Failed (Attempt {state.script_validation_count}). Retrying.")
    return "retry"


def check_briefing_language(state: BriefingState) -> str:
    """
    Conditional edge for Language Routing.
    """
    lang = state.config.get("language", "eng")
    
    if lang == "ar":
        print("[EDGE] Language is Arabic -> Translating.")
        return "translate"
    else:
        print("[EDGE] Language is English -> Producing Audio.")
        return "generate_audio"