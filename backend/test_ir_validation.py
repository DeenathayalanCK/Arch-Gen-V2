from app.ir.architecture import ArchitectureIR

example_ir = {
    "actors": [
        {
            "id": "citizen",
            "role": "Data Owner",
            "channels": ["browser"]
        }
    ],
    "capabilities": [
        {
            "id": "consent_management",
            "purpose": "Manage user consent lifecycle",
            "state": "persistent",
            "constraints": ["regulated"],
            "audience": ["citizen"]
        }
    ],
    "interactions": [
        {
            "source": "citizen",
            "target": "consent_management",
            "semantics": "command",
            "trust_crossing": True
        }
    ]
}

ir = ArchitectureIR.model_validate(example_ir)
print("✅ Architecture IR is valid")
print(ir)
