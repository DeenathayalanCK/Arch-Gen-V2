from typing import List
from .errors import ValidationError
from .service_ir import ServiceIR
from .data_ir import DataIR


def validate_service_data_links(
    service_ir: ServiceIR, data_ir: DataIR
) -> List[ValidationError]:
    errors = []

    service_ids = {s.id for s in service_ir.services}

    for access in data_ir.access_patterns:
        if access.service_id not in service_ids:
            errors.append(
                ValidationError(
                    level="cross",
                    message="data access references unknown service",
                    object_id=access.service_id,
                )
            )

    return errors
