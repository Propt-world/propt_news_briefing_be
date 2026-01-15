import json
import traceback
from pprint import pprint
from src.models.BriefingState import BriefingState
from src.models.ScriptValidationResult import ScriptValidationResult
from src.models.BroadcastScriptAttempt import BroadcastScriptAttempt
from src.config.settings import settings
from src.prompts.ScriptValidationPrompts import SYSTEM_PROMPT, USER_PROMPT
from langchain_core.prompts import PromptTemplate

def validate_broadcast_script(state: BriefingState) -> dict:
    """
    Node: Script Validator
    """
    pprint("[NODE: VALIDATOR] 🧐 Checking script quality...")
    
    try:
        current_draft = state.current_script_draft
        sources = state.drafted_scripts
        
        if not current_draft:
            return {"error": "No draft to validate."}

        # 1. Prepare Context (Flatten sources for the LLM to read easily)
        source_text = "\n\n".join([f"ID: {s.source_article_id}\nTEXT: {s.script_segment}" for s in sources])
        
        # 2. Invoke LLM
        model = settings.get_model().with_structured_output(ScriptValidationResult)
        prompt = PromptTemplate.from_template(USER_PROMPT)
        formatted_prompt = prompt.format(
            source_segments=source_text[:15000], # Truncate if massive
            draft_script=current_draft.full_script
        )
        
        messages = [("system", SYSTEM_PROMPT), ("user", formatted_prompt)]
        validation_res: ScriptValidationResult = model.invoke(messages)
        
        pprint(f"[NODE: VALIDATOR] Score: {validation_res.accuracy_score}/10 | Hallucinations: {validation_res.hallucination_count}")
        pprint(f"[NODE: VALIDATOR] Valid: {validation_res.is_valid}")

        # 3. Record Attempt
        attempt = BroadcastScriptAttempt(
            script_content=current_draft,
            validation=validation_res
        )
        
        new_history = state.script_attempts + [attempt]
        
        return {
            "script_attempts": new_history,
            "script_validation_count": state.script_validation_count + 1
        }

    except Exception as e:
        pprint(f"[NODE: VALIDATOR] 💥 Error: {e}")
        traceback.print_exc()
        return {"error": str(e)}