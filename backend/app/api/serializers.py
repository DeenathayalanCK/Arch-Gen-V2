from typing import Any


PRIMITIVE_TYPES = (str, int, float, bool, type(None))


def serialize_ir(obj: Any):
    """
    Safely serialize IR objects into JSON-compatible structures.
    Deterministic.
    Tolerant to primitives.
    """

    # ✅ Primitive values pass through
    if isinstance(obj, PRIMITIVE_TYPES):
        return obj

    # ✅ Lists: serialize each element
    if isinstance(obj, list):
        return [serialize_ir(item) for item in obj]

    # ✅ Dicts: serialize values
    if isinstance(obj, dict):
        return {k: serialize_ir(v) for k, v in obj.items()}

    # ✅ IR / dataclass-like objects
    if hasattr(obj, "__dict__"):
        return {
            key: serialize_ir(value)
            for key, value in obj.__dict__.items()
            if not key.startswith("_")
        }

    # 🔴 Fallback (should rarely happen)
    return str(obj)
