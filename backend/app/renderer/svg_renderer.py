def render_svg(spec: dict) -> str:
    w = spec["canvas"]["width"]
    h = spec["canvas"]["height"]

    svg = [
        f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">'
    ]

    # Draw edges first
    node_map = {n["id"]: n for n in spec["nodes"]}

    for e in spec.get("edges", []):
        src = node_map[e["from"]]
        dst = node_map[e["to"]]

        x1 = src["x"] + src["width"] / 2
        y1 = src["y"] + src["height"] / 2
        x2 = dst["x"] + dst["width"] / 2
        y2 = dst["y"] + dst["height"] / 2

        svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="#555" stroke-width="2"/>'
        )

    # Draw nodes
    for n in spec["nodes"]:
        svg.append(
            f'<rect x="{n["x"]}" y="{n["y"]}" '
            f'width="{n["width"]}" height="{n["height"]}" '
            f'rx="8" ry="8" fill="#E3F2FD" stroke="#1E88E5"/>'
        )

        svg.append(
            f'<text x="{n["x"] + n["width"]/2}" '
            f'y="{n["y"] + n["height"]/2}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-family="Arial" font-size="14">'
            f'{n["label"]}</text>'
        )

    svg.append("</svg>")
    return "\n".join(svg)
