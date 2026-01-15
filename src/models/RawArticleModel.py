from pydantic import BaseModel, Field
from typing import List, Optional, Any

# Helper for the nested category structure in your JSON
class SourceCategory(BaseModel):
    main_category: str = Field(..., alias="mainCategory")
    subcategories: List[str] = Field(default_factory=list)

class RawArticleModel(BaseModel):
    """
    Validates and parses the raw article data from the external API.
    Only strictly validates fields required for the Script Writing process.
    """
    # --- Identifiers ---
    id: str
    source: str
    url: str
    
    # --- Content ---
    title: str
    summary: Optional[str] = None
    # This maps 'fullArticle' from JSON to 'content' for internal consistency, 
    # or keeps it as fullArticle if you prefer. 
    full_article: str = Field(..., alias="fullArticle")
    
    # --- Metadata ---
    # We map the complex list of dicts to a clean Pydantic list
    categories: List[SourceCategory] = Field(default_factory=list)
    publication_date: Optional[str] = Field(None, alias="publicationDate")
    
    # --- Fallback ---
    # This ensures that if the API sends 'qualityMetrics' or 'seo', 
    # we don't crash, but we also don't bloat our object with them.
    class Config:
        extra = "ignore" 
        populate_by_name = True