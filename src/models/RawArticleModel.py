from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Union

# Helper for the nested category structure in your JSON
class SourceCategory(BaseModel):
    main_category: str = Field(..., alias="mainCategory")
    subcategories: List[str] = Field(default_factory=list)

class RawArticleModel(BaseModel):
    """
    Validates and parses the raw article data from the external API.
    """
    # --- Identifiers ---
    id: str
    source: str
    url: str
    
    # --- Content ---
    title: str
    summary: Optional[str] = None
    full_article: str = Field(..., alias="fullArticle")
    
    # --- Metadata ---
    # FIX: Allow more flexible input for categories
    categories: List[SourceCategory] = Field(default_factory=list)
    
    publication_date: Optional[str] = Field(None, alias="publicationDate")

    # Validator to handle "list of strings" vs "list of objects"
    @validator('categories', pre=True)
    def parse_categories(cls, v):
        # Case 1: Input is ["Business", "Tech"]
        if isinstance(v, list) and v and isinstance(v[0], str):
            return [{"mainCategory": cat} for cat in v]
        # Case 2: Input is None
        if v is None:
            return []
        return v
    
    class Config:
        extra = "ignore" 
        populate_by_name = True