import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { askQuestion } from "../api";
import { messageOf } from "../format";
import type { AskResponse, DemoLine } from "../types";
import { CheckCircleIcon, SearchIcon, WarningIcon } from "./icons";

interface AskPaneProps {
  classLevel: number;
  subject: string;
  subjectLabel: string;
  lines: DemoLine[];
  sourceHint: string;
  courseLabel: string | null;
  onSelectSubject?: (subject: string) => void;
}

const NCERT_MATH_CHAPTERS = [
  { num: 1, title: "Real Numbers" },
  { num: 2, title: "Polynomials" },
  { num: 3, title: "Pair of Linear Equations" },
  { num: 4, title: "Quadratic Equations" },
  { num: 5, title: "Arithmetic Progressions" },
  { num: 6, title: "Triangles" },
  { num: 7, title: "Coordinate Geometry" },
  { num: 8, title: "Introduction to Trigonometry" },
  { num: 9, title: "Applications of Trigonometry" },
  { num: 10, title: "Circles" },
  { num: 11, title: "Areas Related to Circles" },
  { num: 12, title: "Surface Areas and Volumes" },
  { num: 13, title: "Statistics" },
  { num: 14, title: "Probability" },
];

const MATH_SUGGESTIONS: Record<number, string[]> = {
  1: ["State the Fundamental Theorem of Arithmetic.", "Find HCF and LCM of 12 and 18 using prime factorisation."],
  2: ["What is the relationship between zeroes and coefficients of a quadratic polynomial?", "Find zeroes of x² + 7x + 10."],
  3: ["What are the consistency conditions for a pair of linear equations?", "Solve x + y = 14 and x - y = 4 by substitution."],
  4: ["State the quadratic formula and explain the discriminant b² - 4ac.", "Solve 2x² - 7x + 3 = 0 using the quadratic formula."],
  5: ["What is the formula for the nth term and sum of an Arithmetic Progression?", "Find the 20th term of the AP 2, 7, 12, ..."],
  6: ["State and explain the Basic Proportionality Theorem (Thales Theorem)."],
  7: ["State the distance formula and section formula in Coordinate Geometry."],
  8: ["Define the basic trigonometric ratios sine, cosine, and tangent."],
  9: ["If an observer is 30 m from a tower and angle of elevation is 45°, find tower height."],
  10: ["State and prove that tangents drawn from an external point to a circle are equal."],
  11: ["What is the formula for the area of a sector of angle θ of a circle?"],
  12: ["State the formulas for surface area and volume of a cylinder, cone, and sphere."],
  13: ["State the relationship between mean, median, and mode (empirical relationship)."],
  14: ["A die is thrown once. Find the probability of getting a prime number."],
};

export function AskPane({
  classLevel,
  subject,
  subjectLabel,
  lines,
}: AskPaneProps) {
  const [question, setQuestion] = useState("");
  const [selectedChapter, setSelectedChapter] = useState<number>(1);
  const [speedMode, setSpeedMode] = useState<"fast" | "balanced">("fast");
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isMath = subject === "maths" || subject === "mathematics";

  const suggestions = useMemo(() => {
    if (isMath) {
      return MATH_SUGGESTIONS[selectedChapter] ?? [
        "Explain the core theorem of this chapter.",
        "What are the standard CBSE examination formulas for this unit?",
      ];
    }
    return [
      "What is the difference between a concave and convex mirror?",
      "An object is placed at 2F of a convex lens. Explain where the image is formed.",
      "State Ohm's Law and calculate the resistance if V = 12V and I = 2A.",
      "Explain the mirror formula and magnification with sign conventions.",
    ];
  }, [isMath, selectedChapter]);

  // KaTeX rendering hook
  useEffect(() => {
    if (response && typeof window !== "undefined") {
      const timer = setTimeout(() => {
        const renderMathInElement = (window as any).renderMathInElement;
        const answerElem = document.getElementById("qa-answer-container");
        if (renderMathInElement && answerElem) {
          try {
            renderMathInElement(answerElem, {
              delimiters: [
                { left: "$$", right: "$$", display: true },
                { left: "$", right: "$", display: false },
                { left: "\\[", right: "\\]", display: true },
                { left: "\\(", right: "\\)", display: false },
              ],
              throwOnError: false,
            });
          } catch {
            // ignore
          }
        }
      }, 80);
      return () => clearTimeout(timer);
    }
  }, [response]);

  const handleAsk = useCallback(
    async (qText?: string) => {
      const query = (qText ?? question).trim();
      if (!query || query.length < 3) return;

      setLoading(true);
      setError(null);
      try {
        const result = await askQuestion({
          question: query,
          classLevel,
          subject,
          chapter: isMath ? selectedChapter : null,
          lines,
          useLlm: true,
          profile: speedMode === "fast" ? "potato" : "balanced",
        });
        setResponse(result);
      } catch (err) {
        setError(messageOf(err));
      } finally {
        setLoading(false);
      }
    },
    [classLevel, isMath, lines, question, selectedChapter, speedMode, subject],
  );

  return (
    <div className="ask-workspace">
      {/* Search & Query Input Card */}
      <section className="ask-input-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <div>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--text-primary)" }}>
              Syllabus Q&amp;A with Citations
            </h2>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 2 }}>
              Ask questions grounded directly in official NCERT textbooks with zero hallucinations.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* Speed Engine Segmented Control */}
            <div style={{ display: "inline-flex", background: "var(--surface-sunken)", padding: "2px", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
              <button
                type="button"
                onClick={() => setSpeedMode("fast")}
                style={{
                  padding: "3px 8px",
                  fontSize: "0.72rem",
                  fontWeight: 500,
                  borderRadius: "4px",
                  background: speedMode === "fast" ? "var(--surface-elevated)" : "transparent",
                  color: speedMode === "fast" ? "var(--text-primary)" : "var(--text-muted)",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                ⚡ Fast (~1.2s)
              </button>
              <button
                type="button"
                onClick={() => setSpeedMode("balanced")}
                style={{
                  padding: "3px 8px",
                  fontSize: "0.72rem",
                  fontWeight: 500,
                  borderRadius: "4px",
                  background: speedMode === "balanced" ? "var(--surface-elevated)" : "transparent",
                  color: speedMode === "balanced" ? "var(--text-primary)" : "var(--text-muted)",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Balanced (~2.8s)
              </button>
            </div>

            <span className="badge">Class {classLevel}</span>
            <span className="badge badge-accent">{subjectLabel}</span>
          </div>
        </div>

        {/* Chapter Context Filter */}
        {isMath && (
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>Target NCERT Unit:</span>
            <select
              className="select"
              value={selectedChapter}
              onChange={(e) => setSelectedChapter(Number(e.target.value))}
              style={{ fontSize: "0.78rem" }}
            >
              {NCERT_MATH_CHAPTERS.map((ch) => (
                <option key={ch.num} value={ch.num}>
                  Unit {ch.num}: {ch.title}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Question Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleAsk();
          }}
          className="ask-input-row"
        >
          <input
            type="text"
            placeholder="Ask syllabus concepts, formulas, or new numerical problems to solve…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !question.trim()}>
            {loading ? <span className="spinner small" /> : <SearchIcon />}
            <span>{loading ? "Searching…" : "Ask Question"}</span>
          </button>
        </form>

        {/* Suggested Queries */}
        <div className="suggestions-wrap">
          <span style={{ fontSize: "0.74rem", color: "var(--text-muted)", alignSelf: "center", marginRight: 4 }}>
            Suggested:
          </span>
          {suggestions.map((sug) => (
            <button
              key={sug}
              type="button"
              className="suggestion-pill"
              onClick={() => {
                setQuestion(sug);
                void handleAsk(sug);
              }}
              disabled={loading}
            >
              {sug}
            </button>
          ))}
        </div>
      </section>

      {/* Error Banner */}
      {error && (
        <div className="inline-warning error">
          <WarningIcon />
          <span>{error}</span>
        </div>
      )}

      {/* Grounded Answer Card */}
      {response && (
        <article className="answer-card" id="qa-answer-container">
          <header className="answer-header">
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="badge badge-success">
                <CheckCircleIcon />
                <span>Grounded Answer</span>
              </span>
              <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>
                Retrieved in {response.latency_s.toFixed(2)}s via {response.engine ?? "BM25 + Local LLM"} ({speedMode === "fast" ? "Fast 0.8B" : "Balanced 2B"})
              </span>
            </div>

            <span className="badge">
              Source: {response.source?.kind ?? "NCERT Textbook"}
            </span>
          </header>

          {/* Formatted Answer Body */}
          <div
            id="qa-answer-container"
            className="markdown"
            style={{ fontSize: "0.96rem", lineHeight: 1.7 }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {response.answer}
            </ReactMarkdown>
          </div>

          {/* Verified Citations & Text Excerpts */}
          {response.citations && response.citations.length > 0 && (
            <div className="citations-container">
              <h4 style={{ fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", marginBottom: 10 }}>
                Verified Textbook Citations ({response.citations.length})
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {response.citations.map((cite, idx) => (
                  <div key={idx} className="citation-chip">
                    <div className="citation-chip-header">
                      <span>{cite.title || cite.chapter_title || `Chapter ${cite.chapter_number || selectedChapter}`}</span>
                      {cite.score !== undefined && (
                        <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                          Relevance {(cite.score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    {cite.snippet && <p className="citation-snippet">"{cite.snippet}"</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </article>
      )}
    </div>
  );
}
