from dataclasses import dataclass


@dataclass
class ValidationError:
    level: str
    message: str
    object_id: str
