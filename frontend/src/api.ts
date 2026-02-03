export async function generateDiagram(
  prompt: string,
  detailLevel: string,
): Promise<{ mermaid: string }> {
  const res = await fetch("http://localhost:8000/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      detail_level: detailLevel,
    }),
  });

  if (!res.ok) {
    throw new Error("Backend error");
  }

  return res.json();
}
