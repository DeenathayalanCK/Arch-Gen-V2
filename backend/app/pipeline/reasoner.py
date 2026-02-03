import json
import re
from app.ir.architecture import ArchitectureIR
from app.inference.chat_completions_client import ChatCompletionsClient


SYSTEM_PROMPT = """
You are an ARCHITECTURE REASONING SYSTEM.

Output ONLY valid JSON.
Do NOT include markdown or explanations.

Identify:
- actors
- capabilities
- data_entities
- interactions
- assumptions
- constraints
"""


# ----------------------------
# Helpers
# ----------------------------

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")


def normalize_capability_state(state: str) -> str:
    return {
        "async": "persistent",
        "event": "persistent",
        "stream": "persistent",
        "temporary": "local",
        "cached": "local",
        "remote": "shared",
    }.get(state, "none")


def normalize_semantics(value: str) -> str:
    mapping = {
        "initiate": "command",
        "request": "query",
        "transfer": "event",
        "send": "command",
        "call": "command",
        "read": "query",
        "write": "command",
    }
    return mapping.get(value.lower(), "command")


def normalize_notes(items: list) -> list[str]:
    """
    Converts:
      ["text"]
      [{ "assumption": "text" }]
      [{ "constraint": "text" }]
    → ["text"]
    """
    normalized = []
    for item in items:
        if isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, dict):
            normalized.extend(item.values())
    return normalized


# ----------------------------
# Main
# ----------------------------

def run_architecture_reasoner(
    user_prompt: str,
    client: ChatCompletionsClient,
) -> ArchitectureIR:
    """
    Runs LLM-1 to extract Architecture IR from raw user input.
    Fully defensive against mixed / partial model outputs.
    """

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    raw = client.generate(messages)

    try:
        data = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Invalid JSON from reasoner:\n{raw}") from e

    # =========================
    # ACTORS
    # =========================
    normalized_actors = []
    actor_id_map = {}

    for a in data.get("actors", []):
        if isinstance(a, str):
            name = a
            role = "external actor"
            description = None
            channels = []
        elif isinstance(a, dict):
            name = a.get("id") or a.get("name")
            role = a.get("role") or a.get("description") or "external actor"
            description = a.get("description")
            channels = a.get("channels", [])
        else:
            continue

        if not name:
            continue

        aid = slugify(name)
        actor_id_map[name] = aid

        normalized_actors.append({
            "id": aid,
            "role": role,
            "description": description,
            "channels": channels,
        })

    # =========================
    # CAPABILITIES
    # =========================
    normalized_caps = []
    cap_id_map = {}

    for c in data.get("capabilities", []):
        if isinstance(c, str):
            name = c
            purpose = "system responsibility"
            state = "none"
            constraints = []
            audience = []
        elif isinstance(c, dict):
            name = c.get("id") or c.get("name")
            purpose = c.get("purpose") or c.get("description") or "system responsibility"
            state = normalize_capability_state(c.get("state", "none"))
            constraints = c.get("constraints", [])
            audience = c.get("audience", [])
        else:
            continue

        if not name:
            continue

        cid = slugify(name)
        cap_id_map[name] = cid

        normalized_caps.append({
            "id": cid,
            "purpose": purpose,
            "state": state,
            "constraints": constraints,
            "audience": [
                actor_id_map.get(a, slugify(a)) for a in audience
            ],
        })

    # =========================
    # DATA ENTITIES
    # =========================
    normalized_data = []

    for d in data.get("data_entities", []):
        if isinstance(d, str):
            name = d
            description = ""
            sensitivity = "internal"
        elif isinstance(d, dict):
            name = d.get("id") or d.get("name")
            description = d.get("description", "")
            sensitivity = d.get("sensitivity", "internal")
        else:
            continue

        if not name:
            continue

        normalized_data.append({
            "id": slugify(name),
            "description": description,
            "sensitivity": sensitivity,
        })

    # =========================
    # INTERACTIONS
    # =========================
    normalized_interactions = []

    for i in data.get("interactions", []):
        if not isinstance(i, dict):
            continue

        src = i.get("source") or i.get("actor1")
        tgt = i.get("target") or i.get("actor2")

        if not src or not tgt:
            continue

        normalized_interactions.append({
            "source": actor_id_map.get(src, cap_id_map.get(src, slugify(src))),
            "target": actor_id_map.get(tgt, cap_id_map.get(tgt, slugify(tgt))),
            "semantics": normalize_semantics(
                i.get("semantics") or i.get("interaction_type", "")
            ),
            "trust_crossing": bool(i.get("trust_crossing", False)),
        })

    # =========================
    # FINAL NORMALIZED OBJECT
    # =========================
    normalized = {
        "actors": normalized_actors,
        "capabilities": normalized_caps,
        "data_entities": normalized_data,
        "interactions": normalized_interactions,
        "assumptions": normalize_notes(data.get("assumptions", [])),
        "constraints": normalize_notes(data.get("constraints", [])),
    }

    # =========================
    # STRICT VALIDATION
    # =========================
    try:
        return ArchitectureIR.model_validate(normalized)
    except Exception as e:
        raise ValueError(
            "Architecture IR validation failed.\n"
            "Normalized output:\n"
            + json.dumps(normalized, indent=2)
        ) from e
