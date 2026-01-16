import asyncio
import traceback
from pprint import pprint
from typing import List, Optional
from langchain_core.prompts import PromptTemplate

from src.models.BriefingState import BriefingState
from src.models.ArticleScript import ArticleScript
from src.models.RawArticleModel import RawArticleModel
from src.config.settings import settings
from src.prompts.ReporterPrompts import SYSTEM_PROMPT, USER_PROMPT
from src.models.ReporterOutput import ReporterOutput

async def news_room_editors(state: BriefingState) -> dict:
    """
    Node 2: The Reporters (Parallel Processing with Rate Limiting)
    
    Responsibilities:
    1. Iterate through 'state.raw_articles'.
    2. Spawn an LLM agent for EACH article to write a script segment.
    3. Aggregate the results into 'drafted_scripts'.
    """
    pprint(f"[NODE: REPORTERS] 🎤 Starting editorial process for {len(state.raw_articles)} articles...")
    
    # This uses settings.get_model() -> settings.MODEL_NAME (gpt-4o-mini)
    model = settings.get_model().with_structured_output(ReporterOutput)
    
    # FIX: Limit concurrency to 5 agents at a time to respect OpenAI Rate Limits
    semaphore = asyncio.Semaphore(5)

    async def process_article(article: RawArticleModel) -> Optional[ArticleScript]:
        async with semaphore:  # <--- Acquire lock
            try:
                # Format categories for context (e.g., "Business, Technology")
                cat_str = ", ".join([c.main_category for c in article.categories]) if article.categories else "General"
                
                # Prepare Prompt
                prompt_template = PromptTemplate.from_template(USER_PROMPT)
                formatted_user_prompt = prompt_template.format(
                    title=article.title,
                    source=article.source,
                    categories=cat_str,
                    content=article.full_article[:4000] # Truncate to save tokens if extremely long
                )
                
                messages = [
                    ("system", SYSTEM_PROMPT),
                    ("user", formatted_user_prompt)
                ]
                
                # Invoke LLM (Async)
                llm_res: ReporterOutput = await model.ainvoke(messages)
                
                # Merge LLM output with original metadata to create the full ArticleScript
                return ArticleScript(
                    source_article_id=article.id,
                    source_name=article.source,
                    source_url=article.url,
                    headline=llm_res.headline,
                    script_segment=llm_res.script_segment,
                    importance_score=llm_res.importance_score,
                    reasoning=llm_res.reasoning
                )
                
            except Exception as e:
                pprint(f"[NODE: REPORTERS] ⚠️ Failed to process article {article.id}: {e}")
                return None

    # Execute in Parallel
    tasks = [process_article(article) for article in state.raw_articles]
    results = await asyncio.gather(*tasks)
    
    # Filter failures
    valid_scripts = [r for r in results if r is not None]
    
    pprint(f"[NODE: REPORTERS] ✅ Generated {len(valid_scripts)} scripts.")
    
    return {"drafted_scripts": valid_scripts}