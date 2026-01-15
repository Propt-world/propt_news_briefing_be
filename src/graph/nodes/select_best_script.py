from src.models.BriefingState import BriefingState

def select_best_script(state: BriefingState) -> dict:
    """
    Node: Select Best Fallback
    Runs if the loop exhausts retries without a perfect pass.
    Selects the attempt with the highest accuracy score.
    """
    print("[NODE: SELECT BEST] ⚠️ Max retries reached. Selecting best available draft.")
    
    attempts = state.script_attempts
    if not attempts:
        return {"error": "No script attempts generated."}
        
    # Sort by: 1. Hallucinations (Low is good) 2. Accuracy (High is good)
    # Tuple sorting: (Hallucination Count Ascending, Accuracy Descending)
    best_attempt = sorted(
        attempts, 
        key=lambda x: (x.validation.hallucination_count, -x.validation.accuracy_score)
    )[0]
    
    print(f"[NODE: SELECT BEST] Selected attempt with Accuracy: {best_attempt.validation.accuracy_score} and {best_attempt.validation.hallucination_count} hallucinations.")
    
    return {
        "final_script_text": best_attempt.script_content.full_script
    }