#backend\app\dsl\compiler.py

def expand_nodes(nodes, detail_level):
    if detail_level != "high":
        return nodes

    out = []
    for n in nodes:
        if "API" in n["label"]:
            base = n["id"]
            out.extend([
                {"id": f"{base}_gw", "label": "API Gateway", "type": "gateway"},
                {"id": f"{base}_ctrl", "label": "Controller", "type": "service"},
                {"id": f"{base}_svc", "label": "Business Service", "type": "service"},
                {"id": f"{base}_repo", "label": "Repository", "type": "service"},
            ])
        else:
            out.append(n)
    return out


def compile_mermaid(spec):
    lines = [f"flowchart {spec.get('orientation','TD')}"]

    for layer in spec["layers"]:
        lines.append(f"subgraph {layer['name']}")

        nodes = expand_nodes(layer["nodes"], spec.get("detail_level"))
        for n in nodes:
            lines.append(f'{n["id"]}[{n["label"]}]')

        for c in layer.get("connections", []):
            if c["label"] == "request":
                lines.append(f'{c["from"]} -->|request| {c["to"]}')
                lines.append(f'{c["to"]} -->|response| {c["from"]}')
            elif c["label"] == "data":
                lines.append(f'{c["from"]} -->|query| {c["to"]}')
                lines.append(f'{c["to"]} -->|result| {c["from"]}')

        lines.append("end")

    return "\n".join(lines)
