from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


class ParseQueryResponse(BaseModel):
    raw_query: str
    location: Optional[dict]
    categories: Optional[List[str]]


class RecommendResponse(BaseModel):
    query: str
    parsed: dict
    results: List[dict]


class MultilevelResponse(BaseModel):
    level: str
    explanation: dict
    parsed: dict
    data: dict

