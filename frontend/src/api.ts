export async function generateDiagram(
  prompt: string,
  detailLevel: string,
): Promise<{ mermaid: string }> {
  const res = await fetch("http://localhost:8000/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      requirements: prompt, // ✅ FIX HERE
      detail_level: detailLevel,
    }),
  });

  const data = await res.json();

  if (!res.ok || data.status === "error") {
    throw new Error(data.message || "Backend error");
  }

  return data;
}
