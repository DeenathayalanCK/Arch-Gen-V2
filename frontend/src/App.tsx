import { useState, useEffect, useRef } from "react";
import mermaid from "mermaid";
import domtoimage from "dom-to-image";
import { generateDiagram } from "./api";

let renderCount = 0;

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [diagram, setDiagram] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailLevel, setDetailLevel] = useState<"low" | "medium" | "high">(
    "high",
  );

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "default",
    });
  }, []);

  useEffect(() => {
    if (!diagram || !containerRef.current) return;

    (async () => {
      try {
        const id = `diagram-${Date.now()}-${renderCount++}`;
        const { svg } = await mermaid.render(id, diagram);
        containerRef.current!.innerHTML = svg;
        postProcessSvg(containerRef.current!);
      } catch (err) {
        console.error(err);
        containerRef.current!.innerHTML =
          "<pre style='color:red'>Failed to render diagram</pre>";
      }
    })();
  }, [diagram]);

  function postProcessSvg(container: HTMLDivElement) {
    const svg = container.querySelector("svg");
    if (!svg) return;

    svg.setAttribute("width", "100%");
    svg.querySelectorAll("text").forEach((t) => {
      t.setAttribute("font-size", "14");
    });
  }

  async function handleGenerate() {
    if (!prompt.trim()) return;

    setLoading(true);
    try {
      const res = await generateDiagram(prompt, detailLevel);
      setDiagram(res.mermaid);
    } catch (err) {
      console.error(err);
      alert("Diagram generation failed");
    } finally {
      setLoading(false);
    }
  }

  function downloadSVG() {
    const svg = containerRef.current?.querySelector("svg");
    if (!svg) return;

    const blob = new Blob([svg.outerHTML], {
      type: "image/svg+xml;charset=utf-8",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "architecture-diagram.svg";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function downloadPNG() {
    if (!containerRef.current) return;

    const scale = 2;
    const node = containerRef.current;

    const blob = await domtoimage.toBlob(node, {
      width: node.scrollWidth * scale,
      height: node.scrollHeight * scale,
      style: {
        transform: `scale(${scale})`,
        transformOrigin: "top left",
      },
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "architecture-diagram.png";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <h2>Architecture Diagram Generator</h2>

      <textarea
        rows={10}
        style={{ width: "100%", fontFamily: "monospace", padding: 12 }}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe your system architecture..."
      />

      <div style={{ marginTop: 10 }}>
        Detail level:&nbsp;
        <select
          value={detailLevel}
          onChange={(e) => setDetailLevel(e.target.value as any)}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>

      <div style={{ marginTop: 12 }}>
        <button onClick={handleGenerate} disabled={loading}>
          {loading ? "Generating..." : "Generate Diagram"}
        </button>
        <button
          onClick={downloadSVG}
          disabled={!diagram}
          style={{ marginLeft: 10 }}
        >
          Export SVG
        </button>
        <button
          onClick={downloadPNG}
          disabled={!diagram}
          style={{ marginLeft: 10 }}
        >
          Export PNG
        </button>
      </div>

      <div
        ref={containerRef}
        style={{
          marginTop: 24,
          border: "1px solid #ccc",
          padding: 16,
          minHeight: 300,
          background: "#fafafa",
        }}
      />
    </div>
  );
}
