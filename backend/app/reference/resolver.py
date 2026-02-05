from app.reference.registry import REFERENCE_ARCHITECTURES


def resolve_reference_architecture(service_name: str):
    name = service_name.lower()

    for ref in REFERENCE_ARCHITECTURES.values():
        for keyword in ref["service_keywords"]:
            if keyword in name:
                return ref

    return None
