import json
import re
from app.ir.diagram import DiagramIR
from app.ir.architecture import ArchitectureIR
from app.inference.chat_completions_client import ChatCompletionsClient


SYSTEM_PROMPT = """
You are a diagram planning assistant.

Input: Architecture IR (JSON).
Output: Planning hints ONLY in JSON.

You MAY optionally suggest architectural layers as "groups".

Rules:
- Do NOT invent new components
- Reuse only given actors, capabilities, data_entities, interactions
- Do NOT output nodes/edges directly
- Do NOT explain
- Output JSON ONLY
"""


# ------------------------------------------------
# Helpers
# ------------------------------------------------

def _clean_json(text: str) -> str:
    return re.sub(r"```(?:json)?|```", "", text).strip()


def _ref_id(obj) -> str | None:
    if isinstance(obj, str):
        return obj.strip().lower().replace(" ", "_")
    if isinstance(obj, dict):
        val = obj.get("id") or obj.get("name")
        if isinstance(val, str):
            return val.strip().lower().replace(" ", "_")
    return None


def _normalize_notes(items: list) -> list[str]:
    out: list[str] = []
    for item in items:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            for v in item.values():
                if isinstance(v, str):
                    out.append(v)
    return out


def has_minimum_structure(plan: dict) -> bool:
    return (
        len(plan.get("actors", []))
        + len(plan.get("capabilities", []))
        + len(plan.get("data_entities", []))
    ) >= 2


# ------------------------------------------------
# STEP 10 fallback: layer inference
# ------------------------------------------------

LAYER_RULES = {
    "frontend": ("Frontend Layer", ["ui", "web", "spa", "portal", "browser"]),
    "edge": ("Edge Layer", ["gateway", "router", "load", "balancer", "edge"]),
    "identity": ("Identity Layer", ["auth", "oauth", "identity", "login"]),
    "backend": ("Backend Layer", ["service", "process", "logic", "server"]),
    "data": ("Data Layer", ["data", "db", "database", "cache", "store"]),
}


def _infer_groups_fallback(nodes: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}

    for node in nodes:
        if node["kind"] == "actor":
            continue

        nid = node["id"]
        lname = nid.lower()

        for gid, (label, keywords) in LAYER_RULES.items():
            if any(k in lname for k in keywords):
                groups.setdefault(gid, {
                    "id": gid,
                    "label": label,
                    "nodes": []
                })
                groups[gid]["nodes"].append(nid)
                break

    return list(groups.values())


# ------------------------------------------------
# STEP 13 FIX — group normalization
# ------------------------------------------------

def _normalize_groups(groups: list) -> list[dict]:
    """
    Ensures planner groups always satisfy DiagramIR schema
    """
    normalized: list[dict] = []

    for g in groups:
        if not isinstance(g, dict):
            continue

        gid = g.get("id")
        nodes = g.get("nodes", [])

        if not gid or not isinstance(nodes, list):
            continue

        label = g.get("label")
        if not label:
            label = gid.replace("_", " ").title()

        normalized.append({
            "id": gid,
            "label": label,
            "nodes": nodes,
        })

    return normalized


# ------------------------------------------------
# Main
# ------------------------------------------------

def run_diagram_planner(
    architecture_ir: ArchitectureIR,
    client: ChatCompletionsClient,
) -> DiagramIR:

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": architecture_ir.model_dump_json()},
    ]

    # ---------- Planner LLM ----------
    raw_text = _clean_json(client.generate(messages))

    try:
        planning = json.loads(raw_text)
    except Exception as e:
        raise ValueError(f"Planner returned invalid JSON:\n{raw_text}") from e

    # ---------- Retry if weak ----------
    if not has_minimum_structure(planning):
        messages.append({
            "role": "system",
            "content": (
                "Your previous output was incomplete. "
                "Return planning JSON with actors, capabilities, "
                "data_entities, interactions, and optional groups."
            ),
        })
        planning = json.loads(_clean_json(client.generate(messages)))

    # ---------- Diagram IR assembly ----------
    diagram = {
        "nodes": [],
        "edges": [],
        "groups": [],
        "notes": [],
    }

    node_ids: set[str] = set()
    capability_ids: set[str] = set()
    data_ids: set[str] = set()

    # ---- Actors ----
    for a in planning.get("actors", []):
        aid = _ref_id(a)
        if aid and aid not in node_ids:
            node_ids.add(aid)
            diagram["nodes"].append({
                "id": aid,
                "kind": "actor",
                "label": aid.replace("_", " ").title(),
            })

    # ---- Capabilities ----
    for c in planning.get("capabilities", []):
        cid = _ref_id(c)
        if cid and cid not in node_ids:
            capability_ids.add(cid)
            node_ids.add(cid)
            diagram["nodes"].append({
                "id": cid,
                "kind": "capability",
                "label": cid.replace("_", " ").title(),
            })

    # ---- Data entities ----
    for d in planning.get("data_entities", []):
        did = _ref_id(d)
        if did and did not in node_ids:
            data_ids.add(did)
            node_ids.add(did)
            diagram["nodes"].append({
                "id": did,
                "kind": "data",
                "label": did.replace("_", " ").title(),
            })

    # ---- SAFETY NET: capabilities ----
    if not capability_ids:
        if any("auth" in d or "login" in d for d in data_ids):
            diagram["nodes"].append({
                "id": "authenticate_user",
                "kind": "capability",
                "label": "Authenticate User",
            })

        if any("access" in d for d in data_ids):
            diagram["nodes"].append({
                "id": "process_access_request",
                "kind": "capability",
                "label": "Process Access Request",
            })

    # ---- Interactions ----
    for inter in planning.get("interactions", []):
        src = _ref_id(inter.get("source"))
        tgt = _ref_id(inter.get("target"))
        if src and tgt:
            diagram["edges"].append({
                "source": src,
                "target": tgt,
                "label": inter.get("semantics", "interacts"),
                "style": "dashed" if inter.get("trust_crossing") else "solid",
            })

    # ---- Notes ----
    diagram["notes"].extend(_normalize_notes(planning.get("assumptions", [])))
    diagram["notes"].extend(_normalize_notes(planning.get("constraints", [])))

    # ---- STEP 10/13: GROUPS ----
    planner_groups = planning.get("groups")

    if isinstance(planner_groups, list) and planner_groups:
        diagram["groups"] = _normalize_groups(planner_groups)
    else:
        diagram["groups"] = _infer_groups_fallback(diagram["nodes"])

    # ---------- FINAL VALIDATION ----------
    return DiagramIR.model_validate(diagram)
