#backend\app\pipeline\structure_detector.py

import re

STRUCTURE_KEYWORDS = [
    "frontend", "backend", "edge", "identity", "data layer",
    "api gateway", "load balancer", "oauth", "authentication",
    "authorization", "microservice", "database", "cache",
    "request flow", "response", "layer", "tier"
]

def detect_structure_mode(user_prompt: str) -> str:
    text = user_prompt.lower()

    hits = sum(1 for k in STRUCTURE_KEYWORDS if k in text)

    # ≥2 strong signals → STRUCTURED MODE
    return "STRUCTURED" if hits >= 2 else "AUTO"
