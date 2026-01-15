import traceback
from pprint import pprint
from langchain_core.prompts import PromptTemplate

from src.models.BriefingState import BriefingState
from src.config.settings import settings
from src.prompts.TranslationPrompts import SYSTEM_PROMPT, USER_PROMPT

async def translate_script(state: BriefingState) -> dict:
    """
    Node 4 (Conditional): Translator
    
    Responsibilities:
    1. Check if translation is actually needed (double-check).
    2. Invoke the LLM to translate the 'final_script_text' to Arabic.
    3. Update 'translated_script_text' in the state.
    """
    pprint("[NODE: TRANSLATOR] 🌍 Starting translation to Arabic...")
    
    try:
        # 1. Verification
        if state.config.get("language") != "ar":
            pprint("[NODE: TRANSLATOR] Language is not Arabic. Skipping.")
            return {}

        script_to_translate = state.final_script_text
        if not script_to_translate:
            return {"error": "No script available to translate."}

        # 2. Setup LLM
        # We use the standard model (gpt-4o-mini) for text translation
        model = settings.get_model()

        # 3. Prepare Prompt
        prompt_template = PromptTemplate.from_template(USER_PROMPT)
        formatted_user_prompt = prompt_template.format(
            final_script=script_to_translate
        )
        
        messages = [
            ("system", SYSTEM_PROMPT),
            ("user", formatted_user_prompt)
        ]
        
        # 4. Invoke
        response = await model.ainvoke(messages)
        translated_text = response.content
        
        pprint("[NODE: TRANSLATOR] ✅ Translation complete.")

        # 5. Return Update
        return {
            "translated_script_text": translated_text
        }

    except Exception as e:
        pprint(f"[NODE: TRANSLATOR] 💥 Error: {e}")
        traceback.print_exc()
        return {"error": str(e)}