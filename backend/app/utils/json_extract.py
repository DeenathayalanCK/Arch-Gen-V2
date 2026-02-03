import json
import re


def extract_json(text: str) -> dict:
    """
    Extract first valid JSON object from LLM output.
    Returns {} if parsing fails.
    """
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to extract JSON block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}

    try:
        return json.loads(match.group(0))
    except Exception:
        return {}