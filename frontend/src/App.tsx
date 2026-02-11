import { useState, useEffect, useRef } from "react";
import mermaid from "mermaid";
import domtoimage from "dom-to-image";
import { generateDiagram, fetchPatternDetails, PatternSuggestion } from "./api";
import { DiagramDisplay } from "./components/DiagramDisplay";
import { PatternSelector } from "./components/PatternSelector";
import "./components/DiagramDisplay.css";
import "./components/PatternSelector.css";

let renderCount = 0;

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [mermaidDiagram, setMermaidDiagram] = useState("");
  const [d2Diagram, setD2Diagram] = useState("");
  const [loading, setLoading] = useState(false);
  const [detailLevel, setDetailLevel] = useState<"low" | "medium" | "high">(
    "high",
  );

  // Pattern state
  const [suggestedPatterns, setSuggestedPatterns] = useState<
    PatternSuggestion[]
  >([]);
  const [selectedPatterns, setSelectedPatterns] = useState<string[]>([]);
  const [appliedPatterns, setAppliedPatterns] = useState<string[]>([]);
  const [patternsLoading, setPatternsLoading] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "default",
    });
  }, []);

  useEffect(() => {
    if (!mermaidDiagram || !containerRef.current) return;

    (async () => {
      try {
        const id = `diagram-${Date.now()}-${renderCount++}`;
        const { svg } = await mermaid.render(id, mermaidDiagram);
        containerRef.current!.innerHTML = svg;
        postProcessSvg(containerRef.current!);
      } catch (err) {
        console.error(err);
        containerRef.current!.innerHTML =
          "<pre style='color:red'>Failed to render diagram</pre>";
      }
    })();
  }, [mermaidDiagram]);

  function postProcessSvg(container: HTMLDivElement) {
    const svg = container.querySelector("svg");
    if (!svg) return;
    svg.setAttribute("width", "100%");
    svg.querySelectorAll("text").forEach((t) => {
      t.setAttribute("font-size", "14");
    });
  }

  async function handleGenerate(withPatterns: boolean = false) {
    if (!prompt.trim()) return;

    setLoading(true);
    try {
      const patternsToApply = withPatterns ? selectedPatterns : [];
      const res = await generateDiagram(prompt, detailLevel, patternsToApply);

      setMermaidDiagram(res.mermaid);
      setD2Diagram(res.d2);
      setAppliedPatterns(res.applied_patterns || []);
      setValidationResult(res.validation || null);
      setFixResult(res.auto_fix || null);

      // Log for debugging
      console.log("=== GENERATION RESULT ===");
      console.log("Validation:", res.validation);
      console.log("Auto-fix:", res.auto_fix);

      // Fetch pattern details for suggestions (only on first generate)
      if (
        !withPatterns &&
        res.suggested_patterns &&
        res.suggested_patterns.length > 0
      ) {
        setPatternsLoading(true);
        const details = await fetchPatternDetails(res.suggested_patterns);
        setSuggestedPatterns(details);
        setPatternsLoading(false);
      }
    } catch (err) {
      console.error(err);
      alert("Diagram generation failed");
    } finally {
      setLoading(false);
    }
  }

  function handlePatternToggle(patternId: string) {
    setSelectedPatterns((prev) =>
      prev.includes(patternId)
        ? prev.filter((id) => id !== patternId)
        : [...prev, patternId],
    );
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
      style: { transform: `scale(${scale})`, transformOrigin: "top left" },
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "architecture-diagram.png";
    a.click();
    URL.revokeObjectURL(url);
  }

  const [validationResult, setValidationResult] = useState<any>(null);
  const [fixResult, setFixResult] = useState<any>(null);

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
        <button onClick={() => handleGenerate(false)} disabled={loading}>
          {loading ? "Generating..." : "Generate Diagram"}
        </button>

        {selectedPatterns.length > 0 && (
          <button
            onClick={() => handleGenerate(true)}
            disabled={loading}
            style={{
              marginLeft: 10,
              background: "#4caf50",
              color: "white",
              border: "none",
              padding: "8px 16px",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            {loading
              ? "Applying..."
              : `Apply ${selectedPatterns.length} Pattern(s)`}
          </button>
        )}

        <button
          onClick={downloadSVG}
          disabled={!mermaidDiagram}
          style={{ marginLeft: 10 }}
        >
          Export SVG
        </button>
        <button
          onClick={downloadPNG}
          disabled={!mermaidDiagram}
          style={{ marginLeft: 10 }}
        >
          Export PNG
        </button>
      </div>

      {/* Pattern Selector */}
      <PatternSelector
        suggestedPatterns={suggestedPatterns}
        selectedPatterns={selectedPatterns}
        onPatternToggle={handlePatternToggle}
        loading={patternsLoading}
      />

      {/* Applied Patterns Notice */}
      {appliedPatterns.length > 0 && (
        <div
          style={{
            marginTop: 12,
            padding: 12,
            background: "#e8f5e9",
            borderRadius: 6,
          }}
        >
          <strong>✅ Applied Patterns:</strong> {appliedPatterns.join(", ")}
        </div>
      )}

      {/* Validation & Fix Result Display */}
      {(validationResult || fixResult) && (
        <div
          style={{
            marginTop: 12,
            padding: 12,
            background: validationResult?.is_valid ? "#e8f5e9" : "#fff3e0",
            borderRadius: 6,
            fontSize: 13,
          }}
        >
          <strong>🔍 Diagram Validation:</strong>
          {validationResult && (
            <div>
              <span style={{ marginLeft: 8 }}>
                {validationResult.is_valid ? "✅ Valid" : "⚠️ Has Issues"}
              </span>
              <span style={{ marginLeft: 8 }}>
                Errors: {validationResult.error_count || 0}, Warnings:{" "}
                {validationResult.warning_count || 0}
              </span>
              {validationResult.issues &&
                validationResult.issues.length > 0 && (
                  <ul
                    style={{ margin: "4px 0", paddingLeft: 20, fontSize: 12 }}
                  >
                    {validationResult.issues
                      .slice(0, 5)
                      .map((issue: any, i: number) => (
                        <li
                          key={i}
                          style={{
                            color:
                              issue.severity === "error"
                                ? "#d32f2f"
                                : "#f57c00",
                          }}
                        >
                          [{issue.code}] {issue.message}
                        </li>
                      ))}
                    {validationResult.issues.length > 5 && (
                      <li>...and {validationResult.issues.length - 5} more</li>
                    )}
                  </ul>
                )}
            </div>
          )}
          {fixResult && fixResult.fix_type && fixResult.fix_type !== "none" && (
            <div
              style={{
                marginTop: 8,
                padding: 8,
                background: "#e3f2fd",
                borderRadius: 4,
              }}
            >
              <strong>🔧 Auto-Fix Applied:</strong>
              <span style={{ marginLeft: 8 }}>
                {fixResult.success ? "✅" : "⚠️"} {fixResult.fix_type} fix
              </span>
              <span style={{ marginLeft: 8 }}>
                ({fixResult.issues_fixed?.length || 0} fixed,{" "}
                {fixResult.issues_remaining?.length || 0} remaining)
              </span>
              {fixResult.llm_used && (
                <span style={{ marginLeft: 8, fontStyle: "italic" }}>
                  (LLM assisted)
                </span>
              )}
              {fixResult.changes_made && fixResult.changes_made.length > 0 && (
                <ul style={{ margin: "4px 0", paddingLeft: 20, fontSize: 12 }}>
                  {fixResult.changes_made.map((change: string, i: number) => (
                    <li key={i} style={{ color: "#1976d2" }}>
                      ✓ {change}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

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

      <div
        style={{
          marginTop: 24,
          border: "1px solid #ccc",
          padding: 16,
          minHeight: 300,
          background: "#fafafa",
        }}
      >
        <DiagramDisplay mermaidDiagram={mermaidDiagram} d2Diagram={d2Diagram} />
      </div>
    </div>
  );
}
