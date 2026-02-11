import React from "react";

export interface PatternSuggestion {
  id: string;
  name: string;
  description: string;
  category: string;
}

interface PatternSelectorProps {
  suggestedPatterns: PatternSuggestion[];
  selectedPatterns: string[];
  onPatternToggle: (patternId: string) => void;
  loading?: boolean;
}

export const PatternSelector: React.FC<PatternSelectorProps> = ({
  suggestedPatterns,
  selectedPatterns,
  onPatternToggle,
  loading,
}) => {
  if (loading) {
    return (
      <div className="pattern-selector">
        <h4>🔍 Finding applicable patterns...</h4>
      </div>
    );
  }

  if (suggestedPatterns.length === 0) {
    return null;
  }

  return (
    <div className="pattern-selector">
      <h4>📐 Suggested Architecture Patterns</h4>
      <p className="pattern-hint">
        Select patterns to inject into your diagram:
      </p>
      <div className="pattern-list">
        {suggestedPatterns.map((pattern) => (
          <label key={pattern.id} className="pattern-item">
            <input
              type="checkbox"
              checked={selectedPatterns.includes(pattern.id)}
              onChange={() => onPatternToggle(pattern.id)}
            />
            <div className="pattern-info">
              <span className="pattern-name">{pattern.name}</span>
              <span className="pattern-category">{pattern.category}</span>
              <span className="pattern-description">{pattern.description}</span>
            </div>
          </label>
        ))}
      </div>
      {selectedPatterns.length > 0 && (
        <p className="pattern-selected-count">
          ✅ {selectedPatterns.length} pattern(s) will be injected
        </p>
      )}
    </div>
  );
};
