from dataclasses import dataclass, field
from typing import Optional, Dict

from app.ir.business_ir import BusinessIR
from app.ir.service_ir import ServiceIR
from app.ir.data_ir import DataIR
from app.ir.infra_ir import InfraIR
from app.ir.decomposition_ir import DecomposedRequirements
from app.ir.responsibility_ir import ServiceResponsibilities

@dataclass
class PipelineContext:
    # Raw input (authoritative)
    requirements_text: str

    # Decomposition
    decomposed: DecomposedRequirements | None = None

    # IR layers
    business_ir: Optional[BusinessIR] = None
    service_ir: Optional[ServiceIR] = None
    responsibility_map: Dict[str, ServiceResponsibilities] = field(default_factory=dict)
    data_ir: Optional[DataIR] = None
    infra_ir: Optional[InfraIR] = None

    errors: list[str] = field(default_factory=list)

    @property
    def requirements(self) -> str:
        return self.requirements_text
