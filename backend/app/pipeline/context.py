from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

from app.ir.business_ir import BusinessIR
from app.ir.service_ir import ServiceIR
from app.ir.data_ir import DataIR
from app.ir.infra_ir import InfraIR
from app.ir.decomposition_ir import DecomposedRequirements
from app.ir.responsibility_ir import ServiceResponsibilities, ResponsibilityDependency, ResponsibilityDataAccess

@dataclass
class PipelineContext:
    """Context object that flows through the pipeline stages."""
    
    # Requirements text (can be set after init)
    requirements_text: str = ""
    
    # Core IR fields
    business_ir: Any = None
    service_ir: Any = None
    data_ir: Any = None
    infra_ir: Any = None
    
    # Visual IR
    visual_ir: Any = None
    
    # System context (C4 L1)
    system_context_ir: Any = None
    
    # Pattern tracking
    applied_patterns: List[str] = field(default_factory=list)
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    
    # Domain adapter context
    domain_context: Any = None
    
    # Domain enrichment result
    enrichment_result: Any = None
    
    # Domain validation result
    domain_validation: Any = None

    # Decomposition
    decomposed: DecomposedRequirements | None = None
    #decomposed: Optional[DecomposedRequirements] = None
    # IR layers
    business_ir: Optional[BusinessIR] = None
    service_ir: Optional[ServiceIR] = None
    responsibility_map: Dict[str, ServiceResponsibilities] = field(default_factory=dict)
    data_ir: Optional[DataIR] = None
    infra_ir: Optional[InfraIR] = None

    @property
    def requirements(self) -> str:
        return self.requirements_text
    
    def add_error(self, message: str):
        self.errors.append(message)