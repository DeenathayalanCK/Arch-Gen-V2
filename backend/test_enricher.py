from app.pipeline.enricher import enrich_architecture_ir
from app.ir.architecture import ArchitectureIR

example_ir = ArchitectureIR(
    actors=[{"id": "Citizen User", "role": "Data Owner"}],
    capabilities=[
        {
            "id": "Consent Management",
            "purpose": "Manage and store user consent records",
            "state": "none",
            "constraints": [],
            "audience": ["citizen_user"],
        }
    ],
    data_entities=[
        {
            "id": "Health Records",
            "description": "Personal health information",
            "sensitivity": "internal",
        }
    ],
    interactions=[
        {
            "source": "citizen_user",
            "target": "consent_management",
            "semantics": "command",
            "trust_crossing": False,
        }
    ],
)

enriched = enrich_architecture_ir(example_ir)
print("✅ Enriched Architecture IR")
import json
print(json.dumps(enriched.dict(), indent=2))

