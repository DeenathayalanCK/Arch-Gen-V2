export interface PatternSuggestion {
  id: string;
  name: string;
  description: string;
  category: string;
}

export interface DiagramResponse {
  mermaid: string;
  d2: string;
  suggested_patterns?: string[];
  applied_patterns?: string[];
}

export async function generateDiagram(
  prompt: string,
  detailLevel: string,
  patterns: string[] = [],
): Promise<DiagramResponse> {
  const res = await fetch("http://localhost:8000/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      requirements: prompt,
      detail_level: detailLevel,
      patterns: patterns,
    }),
  });

  const data = await res.json();

  if (!res.ok || data.status === "error") {
    throw new Error(data.message || "Backend error");
  }

  return {
    mermaid: data.mermaid || "",
    d2: data.d2 || "",
    suggested_patterns: data.suggested_patterns || [],
    applied_patterns: data.applied_patterns || [],
  };
}

export async function fetchPatternDetails(
  patternIds: string[],
): Promise<PatternSuggestion[]> {
  const patterns: PatternSuggestion[] = [];

  for (const id of patternIds) {
    try {
      const res = await fetch(`http://localhost:8000/patterns/${id}`);
      if (res.ok) {
        const data = await res.json();
        if (!data.error) {
          patterns.push({
            id: data.id,
            name: data.name,
            description: data.description,
            category: data.category,
          });
        }
      }
    } catch (e) {
      console.warn(`Failed to fetch pattern ${id}`, e);
    }
  }

  return patterns;
}
