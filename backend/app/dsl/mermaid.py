import re

MERMAID_DIRECTIVE_RE = re.compile(r"^flowchart\s+(TD|LR|TB|RL)$", re.IGNORECASE)


def _pre_split_keywords(code: str) -> str:
    """
    Insert safe newlines when important keywords are glued to other tokens.
    Examples we handle:
      - "endClient" -> "end\nClient"
      - "endsubgraph" -> "end\nsubgraph"
      - "subgraphFrontend" -> "\nsubgraph Frontend" (we ensure the keyword is on its own line)
    This prevents the parser from seeing joined tokens like 'endClient' or 'endsubgraph'.
    """

    # If 'end' is immediately followed by an alnum or '[' (e.g. 'endClient' or 'end['),
    # put a newline after 'end'
    code = re.sub(r'(?i)\bend(?=[A-Za-z0-9_\[])', 'end\n', code)

    # If 'subgraph' is glued to a previous token (e.g. 'endsubgraph' or 'foo subgraph' without newline),
    # ensure there is a newline before 'subgraph'
    # This will convert '...endsubgraph' -> '...end\nsubgraph' or 'XYZsubgraph' -> 'XYZ\nsubgraph'
    code = re.sub(r'(?i)(?<!\n)(subgraph)', r'\n\1', code)

    # Also ensure a newline after 'subgraph' if it has been followed immediately by an identifier
    # (e.g. 'subgraphFrontend' -> 'subgraph Frontend')
    code = re.sub(r'(?i)subgraph(?=[A-Za-z0-9_])', 'subgraph ', code)

    return code


def sanitize_line(line: str) -> list[str]:
    """
    Grammar-safe Mermaid sanitizer.
    Returns zero or more valid Mermaid lines.
    """
    line = line.strip()
    if not line:
        return []

    # If the line is exactly 'end', keep it as the keyword
    if line == "end":
        return ["end"]

    # If 'end' appears glued to something else, split and sanitize each piece
    if "end" in line and not line == "end":
        # break glued 'end' occurrences into their own line
        parts = re.sub(r'(?i)end', '\nend\n', line).splitlines()
        out = []
        for p in parts:
            out.extend(sanitize_line(p))
        return out

    # If 'subgraph' appears glued to something else, split similarly
    if "subgraph" in line and not line.startswith("subgraph"):
        parts = line.replace("subgraph", "\nsubgraph").splitlines()
        out = []
        for p in parts:
            out.extend(sanitize_line(p))
        return out

    # DO NOT alter edge lines (they can contain labels and arrows)
    if "-->" in line or "---" in line:
        # Trim repeated whitespace but keep structure exactly
        return [re.sub(r'\s+', ' ', line)]

    # SUBGRAPH (safe transform)
    if line.startswith("subgraph"):
        title = line[len("subgraph"):].strip()
        # Title may already be like "Frontend" or "Frontend[Frontend]" — normalize to ID + [Label]
        safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", title)
        # keep original title as label (trim double quotes etc.)
        return [f"subgraph {safe_id}[{title}]"]

    # NODE (bare labels)
    if re.match(r"^[A-Za-z][A-Za-z0-9 _/\-()]+$", line):
        label = line
        safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", label)
        return [f"{safe_id}[{label}]"]

    # If nothing matched, return the line unchanged (best effort)
    return [line]


def normalize_mermaid(code: str) -> str:
    if not code:
        return ""

    # Remove markdown fences
    code = re.sub(r"```mermaid|```", "", code, flags=re.IGNORECASE).strip()

    # Pre-split glued keywords to avoid 'endClient' or 'endsubgraph' problems
    code = _pre_split_keywords(code)

    # Break into non-empty lines
    lines = [l for l in code.splitlines() if l.strip()]
    if not lines:
        return ""

    # Protect and normalize the first line (directive)
    first = lines[0].strip()
    if first.lower().startswith("graph"):
        first = first.replace("graph", "flowchart", 1)

    if not MERMAID_DIRECTIVE_RE.match(first):
        first = "flowchart TD"

    sanitized = [first]

    # Sanitize remaining lines. sanitize_line returns list[str] so we extend.
    for line in lines[1:]:
        sanitized.extend(sanitize_line(line))

    # Ensure there is exactly one blank line between directive and first content (optional)
    return "\n".join(sanitized)


def validate_mermaid(code: str) -> bool:
    if not code:
        return False

    lines = [l for l in code.splitlines() if l.strip()]
    if not lines:
        return False

    # First line must be a valid directive like "flowchart TD"
    if not MERMAID_DIRECTIVE_RE.match(lines[0]):
        return False

    # Basic safety: no script tags or markdown fences
    forbidden = re.search(r"<script|</|```", code, re.IGNORECASE)
    return forbidden is None