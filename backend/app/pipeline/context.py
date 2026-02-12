from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

from app.ir.business_ir import BusinessIR
from app.ir.service_ir import ServiceIR
from app.ir.data_ir import DataIR
from app.ir.infra_ir import InfraIR
from app.ir.decomposition_ir import DecomposedRequirements
from app.ir.responsibility_ir import (
    ServiceResponsibilities,
    ResponsibilityDependency,
    ResponsibilityDataAccess,
)


@dataclass
class PipelineContext:
    """Context object that flows through the pipeline stages."""

    # ============================
    # Input
    # ============================
    requirements_text: str = ""

    # ============================
    # Decomposition
    # ============================
    decomposed: Optional[DecomposedRequirements] = None

    # ============================
    # IR Layers
    # ============================
    business_ir: Optional[BusinessIR] = None
    service_ir: Optional[ServiceIR] = None
    data_ir: Optional[DataIR] = None
    infra_ir: Optional[InfraIR] = None

    # Responsibility mapping
    responsibility_map: Dict[str, ServiceResponsibilities] = field(default_factory=dict)

    # ============================
    # Visual IR
    # ============================
    visual_ir: Any = None

    # ============================
    # System Context (C4 L1)
    # ============================
    system_context_ir: Any = None

    # ============================
    # Pattern tracking
    # ============================
    applied_patterns: List[str] = field(default_factory=list)

    # ============================
    # Domain fields (Step 3 fix)
    # ============================
    domain_context: Any = None
    enrichment_result: Any = None
    domain_validation: Any = None

    # ============================
    # Error tracking
    # ============================
    errors: List[str] = field(default_factory=list)

    # ============================
    # Helpers
    # ============================
    @property
    def requirements(self) -> str:
        return self.requirements_text

    def add_error(self, message: str):
        self.errors.append(message)
