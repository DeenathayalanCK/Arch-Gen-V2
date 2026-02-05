from pydantic import BaseModel
from typing import Optional, Dict, Any


class GenerateRequest(BaseModel):
    requirements: str


class DiagramResponse(BaseModel):
    type: str
    source: str


class GenerateResponse(BaseModel):
    status: str
    ir: Dict[str, Optional[Dict[str, Any]]]
    diagram: DiagramResponse
