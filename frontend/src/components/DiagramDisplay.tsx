import React, { useState } from "react";

interface DiagramDisplayProps {
  mermaidDiagram?: string;
  d2Diagram?: string;
}

type TabType = "mermaid" | "d2";

export const DiagramDisplay: React.FC<DiagramDisplayProps> = ({
  mermaidDiagram,
  d2Diagram,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>("mermaid");

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  return (
    <div className="diagram-display">
      {/* Tab buttons */}
      <div className="diagram-tabs">
        <button
          className={`tab-button ${activeTab === "mermaid" ? "active" : ""}`}
          onClick={() => setActiveTab("mermaid")}
          disabled={!mermaidDiagram}
        >
          Mermaid Code
        </button>
        <button
          className={`tab-button ${activeTab === "d2" ? "active" : ""}`}
          onClick={() => setActiveTab("d2")}
          disabled={!d2Diagram}
        >
          D2 Code
        </button>
      </div>

      {/* Diagram content */}
      <div className="diagram-content">
        {activeTab === "mermaid" && mermaidDiagram && (
          <div className="diagram-panel">
            <div className="diagram-header">
              <h3>Mermaid Diagram Code</h3>
              <button
                className="copy-button"
                onClick={() => copyToClipboard(mermaidDiagram)}
              >
                Copy
              </button>
            </div>
            <pre className="diagram-code">{mermaidDiagram}</pre>
          </div>
        )}

        {activeTab === "d2" && d2Diagram && (
          <div className="diagram-panel">
            <div className="diagram-header">
              <h3>D2 Diagram Code</h3>
              <button
                className="copy-button"
                onClick={() => copyToClipboard(d2Diagram)}
              >
                Copy
              </button>
            </div>
            <pre className="diagram-code">{d2Diagram}</pre>
            <p className="diagram-hint">
              📎 Copy and paste to{" "}
              <a
                href="https://play.d2lang.com"
                target="_blank"
                rel="noopener noreferrer"
              >
                D2 Playground
              </a>{" "}
              to render
            </p>
          </div>
        )}

        {!mermaidDiagram && !d2Diagram && (
          <div className="diagram-empty">
            <p>No diagram generated yet</p>
          </div>
        )}
      </div>
    </div>
  );
};
