from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class GenerateRequest(BaseModel):
    requirements: str
    include_system_context: bool = False  # Include C4 Level 1
    output_format: str = "mermaid"  # mermaid | d2
    patterns: List[str] = []  # Pattern IDs to auto-inject
    detail_level: str = "high"  # Add this field


class RefineRequest(BaseModel):
    """Request data for refining an existing architecture"""
    requirements: str  # Original requirements
    refinement: str  # What to change/add
    current_ir: Optional[Dict[str, Any]] = None  # Previous IR state
    diagram_id: Optional[str] = None  # Reference to stored diagram


class PatternInjectionRequest(BaseModel):
    """Request to inject a pattern into existing architecture"""
    pattern_id: str
    mappings: Dict[str, str]  # {"{{service}}": "svc_order_service"}
    current_ir: Optional[Dict[str, Any]] = None


class ExplainRequest(BaseModel):
    """Request explanation for architectural decisions"""
    question: str
    context: Optional[Dict[str, Any]] = None


class DiagramResponse(BaseModel):
    type: str
    source: str


class GenerateResponse(BaseModel):
    status: str
    ir: Dict[str, Optional[Dict[str, Any]]]
    diagram: DiagramResponse
    system_context: Optional[Dict[str, Any]] = None  # C4 L1 if requested
    suggested_patterns: List[str] = []  # Auto-suggested patterns
