import json
import traceback
from pprint import pprint
from typing import List

from src.models.BriefingState import BriefingState
from src.models.FinalBroadcastScript import FinalBroadcastScript
from src.models.ArticleScript import ArticleScript
from src.config.settings import settings
from src.prompts.ChiefEditorPrompts import SYSTEM_PROMPT, USER_PROMPT, RETRY_INSTRUCTION
from langchain_core.prompts import PromptTemplate

def chief_editor(state: BriefingState) -> dict:
    """
    Node 3: Editor-in-Chief
    
    Responsibilities:
    1. Select the best stories from 'drafted_scripts' to fit the user's duration.
    2. Prompt the LLM to compile them into a cohesive broadcast script.
    3. If this is a retry (feedback exists), incorporate the Critic's notes.
    """
    # Debug log to show which attempt loop we are in
    pprint(f"[NODE: CHIEF EDITOR] 📰 Compiling final broadcast (Attempt {state.script_validation_count + 1})...")
    
    try:
        # 1. Config & Inputs
        target_duration = state.config.get("duration", 5) # Default to 5 minutes if missing
        available_scripts = state.drafted_scripts
        
        if not available_scripts:
            return {"error": "No scripts available for compilation."}

        # 2. Heuristic Selection (Pre-filtering)
        # We sort by the 'importance_score' assigned by the Reporters (10 is highest).
        sorted_scripts = sorted(available_scripts, key=lambda x: x.importance_score, reverse=True)
        
        # Budgeting: Assume ~150 words/min. Average script segment is ~100-120 words.
        # We allow a small buffer (+2) so the LLM has some flexibility in what it weaves together.
        max_segments = int((target_duration * 150) / 100) + 2
        
        selected_pool = sorted_scripts[:max_segments]
        
        # 3. Prepare Context for LLM
        # We minimize the JSON payload to save tokens, only sending what's needed for the script.
        context_data = [
            {
                "headline": s.headline,
                "script": s.script_segment,
                "score": s.importance_score,
                "source": s.source_name
            } 
            for s in selected_pool
        ]

        # 4. Handle Feedback (Loop Logic)
        feedback_text = ""
        
        # We check if 'script_validation_count' > 0 (meaning we've run before) 
        # AND if there are history items in 'script_attempts'.
        if state.script_validation_count > 0 and state.script_attempts:
            last_attempt = state.script_attempts[-1]
            
            # If the last attempt failed validation, we inject the feedback
            if not last_attempt.validation.is_valid:
                feedback_text = RETRY_INSTRUCTION.format(feedback=last_attempt.validation.feedback)
                pprint(f"[NODE: CHIEF EDITOR] ⚠️ Applying Quality Control feedback: {last_attempt.validation.feedback}")
        
        # 5. LLM Generation
        # We use 'with_structured_output' to ensure we get the FinalBroadcastScript object back
        model = settings.get_model().with_structured_output(FinalBroadcastScript)
        
        # Append feedback to the user prompt if it exists
        full_user_prompt = USER_PROMPT + feedback_text
        
        prompt_template = PromptTemplate.from_template(full_user_prompt)
        formatted_prompt = prompt_template.format(
            duration=target_duration,
            segments_json=json.dumps(context_data, indent=2)
        )
        
        messages = [
            ("system", SYSTEM_PROMPT),
            ("user", formatted_prompt)
        ]
        
        result: FinalBroadcastScript = model.invoke(messages)
        
        pprint(f"[NODE: CHIEF EDITOR] ✅ Script compiled. Estimated Duration: {result.estimated_duration_minutes}m")

        # 6. Return Updates
        # CRITICAL FIX: We return the result into 'current_script_draft'.
        # The 'validate_broadcast_script' node explicitly looks for 'state.current_script_draft'.
        return {
            "current_script_draft": result
        }

    except Exception as e:
        pprint(f"[NODE: CHIEF EDITOR] 💥 Error: {e}")
        traceback.print_exc()
        # Return error so the graph handles it (or moves to End)
        return {"error": str(e)}