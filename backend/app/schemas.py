from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Block(BaseModel):
    block_id: str
    block_type: str
    text: str
    confidence: float
    bbox: List[float]
    bbox_rel: List[float]
    page: int
    reading_order: int
    tokens: Optional[List[Dict[str, Any]]] = None


class Page(BaseModel):
    page_number: int
    text: str
    width: int
    height: int
    blocks: List[Block]


class OCRResult(BaseModel):
    filename: str
    pages: List[Page]
    raw_response: Optional[Dict[str, Any]] = Field(default=None, alias="rawResponse")

    model_config = {"populate_by_name": True}


class SampleList(BaseModel):
    samples: List[str]



