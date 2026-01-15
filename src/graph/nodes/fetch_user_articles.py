import httpx
import traceback
from pprint import pprint
from typing import List, Dict, Any

from src.models.BriefingState import BriefingState
from src.models.RawArticleModel import RawArticleModel
from src.config.settings import settings

async def fetch_user_articles(state: BriefingState) -> dict:
    """
    Node 1: Fetch Articles
    
    Responsibilities:
    1. Call the external Articles Service API for the given user_id.
    2. Validate the response using Pydantic (RawArticleModel).
    3. Update the state with the list of valid article objects.
    """
    user_id = state.user_id
    
    print(f"[NODE: FETCH ARTICLES] 📥 Fetching feed for User: {user_id}")

    # Construct URL (Adjust path based on your actual API spec)
    # Assuming: GET /articles?user_id=xyz OR /user/{id}/feed
    # Using a generic pattern here based on your settings
    url = f"{settings.ARTICLES_SERVICE_URL}/user/{user_id}/feed"
    
    # Headers (API Key if needed)
    headers = {}
    if settings.ARTICLES_SERVICE_API_KEY:
        headers["Authorization"] = f"Bearer {settings.ARTICLES_SERVICE_API_KEY}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15.0)
            response.raise_for_status()
            
            data = response.json()
            
            # The API returns: { "articles": [ ... ], "pagination": { ... } }
            # We strictly need the list under "articles"
            raw_list = data.get("articles", [])
            
            if not raw_list:
                pprint(f"[NODE: FETCH ARTICLES] ⚠️ No articles found for user.")
                return {"error": "No articles returned from API."}

            # --- Validation & Parsing ---
            valid_articles: List[RawArticleModel] = []
            
            for item in raw_list:
                try:
                    # Parse into our strict Pydantic model
                    # This filters out unused SEO/Hyperlink blobs automatically
                    article_model = RawArticleModel(**item)
                    valid_articles.append(article_model)
                except Exception as parse_err:
                    # If one article is malformed, we skip it rather than crashing the whole job
                    pprint(f"[NODE: FETCH ARTICLES] ⚠️ Skipping malformed article: {parse_err}")
                    # Optional: Log the ID of the bad article for debugging
                    # print(f"Bad Item ID: {item.get('id')}")

            pprint(f"[NODE: FETCH ARTICLES] ✅ Successfully parsed {len(valid_articles)} articles.")

            # Return the dictionary to update the State
            # LangGraph merges this return value into the existing state
            return {
                "raw_articles": valid_articles,
                "error": None # Clear any previous errors
            }

    except httpx.HTTPStatusError as e:
        error_msg = f"API Error: {e.response.status_code} - {e.response.text}"
        pprint(f"[NODE: FETCH ARTICLES] ❌ {error_msg}")
        return {"error": error_msg}
        
    except Exception as e:
        pprint(f"[NODE: FETCH ARTICLES] 💥 Critical Failure: {e}")
        traceback.print_exc()
        return {"error": str(e)}