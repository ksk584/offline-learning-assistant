import { useCallback, useEffect, useMemo, useState } from "react";
import { askQuestion } from "../api";
import { formatTime, messageOf } from "../format";
import type { AskResponse, DemoLine } from "../types";
import { BookIcon, SearchIcon, SparkIcon, WarningIcon } from "./icons";

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
  { num: 1, title: "Real Numbers", file: "jemh101.pdf" },
  { num: 2, title: "Polynomials", file: "jemh102.pdf" },
  { num: 3, title: "Pair of Linear Equations in Two Variables", file: "jemh103.pdf" },
  { num: 4, title: "Quadratic Equations", file: "jemh104.pdf" },
  { num: 5, title: "Arithmetic Progressions", file: "jemh105.pdf" },
  { num: 6, title: "Triangles", file: "jemh106.pdf" },
  { num: 7, title: "Coordinate Geometry", file: "jemh107.pdf" },
  { num: 8, title: "Introduction to Trigonometry", file: "jemh108.pdf" },
  { num: 9, title: "Some Applications of Trigonometry", file: "jemh109.pdf" },
  { num: 10, title: "Circles", file: "jemh110.pdf" },
  { num: 11, title: "Areas Related to Circles", file: "jemh111.pdf" },
  { num: 12, title: "Surface Areas and Volumes", file: "jemh112.pdf" },
  { num: 13, title: "Statistics", file: "jemh113.pdf" },
  { num: 14, title: "Probability", file: "jemh114.pdf" },
];

const MATH_CHAPTER_SUGGESTIONS: Record<number, string[]> = {
  1: [
    "State the Fundamental Theorem of Arithmetic.",
    "Prove that √2 is an irrational number.",
    "What is the relationship between HCF and LCM of two numbers?",
  ],
  2: [
    "What is the relationship between zeroes and coefficients of a quadratic polynomial?",
    "What is the geometrical meaning of the zeroes of a polynomial?",
  ],
  3: [
    "What are the consistency conditions for a pair of linear equations?",
    "What is the substitution method for solving linear equations?",
  ],
  4: [
    "What is the discriminant of a quadratic equation?",
    "State the quadratic formula for ax² + bx + c = 0.",
    "What are the conditions for real and equal roots?",
  ],
  5: [
    "What is the formula for the nth term of an Arithmetic Progression?",
    "What is the sum of the first n terms of an AP?",
  ],
  6: [
    "State the Basic Proportionality Theorem (Thales Theorem).",
    "What are the criteria for similarity of triangles?",
  ],
  7: [
    "What is the distance formula in coordinate geometry?",
    "State the section formula for internal division.",
  ],
  8: [
    "Define the trigonometric ratios sine, cosine, and tangent.",
    "What are the trigonometric ratios of complementary angles?",
  ],
  9: [
    "What is the angle of elevation and angle of depression in trigonometry?",
  ],
  10: [
    "How many tangents can be drawn to a circle from an external point?",
    "Prove that lengths of tangents drawn from an external point to a circle are equal.",
  ],
  11: [
    "What is the formula for the area of a sector of a circle?",
  ],
  12: [
    "What is the formula for the volume and surface area of a cylinder?",
    "What is the volume of a sphere and hemisphere?",
  ],
  13: [
    "How is the mode of grouped data calculated in statistics?",
    "State the empirical relationship between mean, median, and mode.",
  ],
  14: [
    "Define theoretical probability of an event.",
    "What is an impossible event and sure event in probability?",
  ],
};

const SUGGESTIONS: Record<string, string[]> = {
  "8-science": [
    "What are kharif crops?",
    "What is manure?",
    "What is ploughing?",
  ],
  "9-science": [
    "What is displacement?",
    "What is acceleration?",
    "What does the slope of a velocity-time graph give?",
  ],
  "10-science": [
    "What is reflection?",
    "What is the law of reflection?",
    "What is a concave mirror?",
    "What is the refractive index?",
  ],
  "8-maths": [
    "What is a perfect square?",
    "What is the square root?",
    "What is the radical sign?",
  ],
  "9-maths": [
    "What are rational numbers?",
    "What are irrational numbers?",
    "What is rationalisation?",
  ],
  "10-maths": [
    "State the Fundamental Theorem of Arithmetic.",
    "What is the discriminant of a quadratic equation?",
    "What is the condition for a pair of linear equations to be consistent?",
    "What is an Arithmetic Progression and common difference?",
    "State the Basic Proportionality Theorem (Thales Theorem).",
    "Define trigonometric ratios: sine, cosine and tangent.",
    "How many tangents can be drawn to a circle from an external point?",
    "What is the formula for the distance between two points in coordinate geometry?",
  ],
};

const KIND_LABELS: Record<string, string> = {
  demo: "NCERT demo",
  transcript: "Current transcript",
  session: "Saved session",
  textbook: "NCERT Textbook PDF",
};

export function AskPane({
  classLevel,
  subject,
  subjectLabel,
  lines,
  sourceHint,
  courseLabel,
  onSelectSubject,
}: AskPaneProps) {
  const [currentSubject, setCurrentSubject] = useState(subject);
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCurrentSubject(subject);
  }, [subject]);

  const handleSwitchSubject = (newSubject: string) => {
    setCurrentSubject(newSubject);
    setSelectedChapter(null);
    setResponse(null);
    setError(null);
    setQuestion("");
    onSelectSubject?.(newSubject);
  };

  const suggestions = useMemo(() => {
    if (currentSubject === "maths" && classLevel === 10) {
      if (selectedChapter && MATH_CHAPTER_SUGGESTIONS[selectedChapter]) {
        return MATH_CHAPTER_SUGGESTIONS[selectedChapter];
      }
      return SUGGESTIONS["10-maths"];
    }
    return SUGGESTIONS[`${classLevel}-${currentSubject}`] ?? [];
  }, [classLevel, currentSubject, selectedChapter]);

  useEffect(() => {
    setResponse(null);
    setError(null);
    setQuestion("");
  }, [classLevel, currentSubject]);

  const runAsk = useCallback(
    async (raw: string) => {
      const trimmed = raw.trim();
      if (!trimmed || loading) return;
      setQuestion(trimmed);
      setLoading(true);
      setError(null);
      try {
        const result = await askQuestion({
          question: trimmed,
          lines,
          classLevel,
          subject: currentSubject,
        });
        setResponse(result);
      } catch (caught) {
        setError(messageOf(caught));
        setResponse(null);
      } finally {
        setLoading(false);
      }
    },
    [classLevel, currentSubject, lines, loading],
  );

  const usingTranscript = lines.length > 0;
  const isMath = currentSubject === "maths";
  const sourceTitle = response?.source.title ?? (isMath ? "NCERT Class 10 Mathematics Textbook (All 14 Chapters)" : sourceHint);
  const sourceKind = response
    ? (KIND_LABELS[response.source.kind] ?? response.source.kind)
    : usingTranscript
      ? "Current transcript"
      : isMath
        ? "NCERT Textbook PDF"
        : "NCERT demo";

  const topics = useMemo(() => response?.topics.slice(0, 3) ?? [], [response]);

  return (
    <section className="panel study-panel ask-pane">
      <header className="panel-header">
        <div>
          <p className="panel-kicker">Grounded Q&amp;A · cite or refuse</p>
          <h2>Ask the lecture &amp; NCERT Textbook</h2>
        </div>
        <div className="panel-actions">
          <span className="chip chip-accent">
            <SparkIcon />
            {isMath ? "Class 10 Mathematics (14 Textbooks)" : (courseLabel ?? `Class ${classLevel} ${subjectLabel}`)}
          </span>
        </div>
      </header>

      <div className="study-body">
        {/* Subject Switcher Bar */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            marginBottom: "14px",
            background: "rgba(5, 8, 17, 0.9)",
            padding: "6px",
            borderRadius: "12px",
            border: "1px solid rgba(37, 99, 235, 0.25)",
          }}
        >
          <button
            type="button"
            className={`btn ${isMath ? "primary" : "ghost"}`}
            style={{ flex: 1, padding: "8px 14px", fontSize: "0.85rem", fontWeight: 700 }}
            onClick={() => handleSwitchSubject("maths")}
          >
            📘 Class 10 Mathematics (NCERT Textbooks)
          </button>
          <button
            type="button"
            className={`btn ${!isMath ? "primary" : "ghost"}`}
            style={{ flex: 1, padding: "8px 14px", fontSize: "0.85rem", fontWeight: 700 }}
            onClick={() => handleSwitchSubject("science")}
          >
            🔬 Class 10 Science (Demo Lecture)
          </button>
        </div>

        {/* Math Chapter Selector Chips */}
        {isMath && (
          <div
            style={{
              marginBottom: "14px",
              padding: "10px 12px",
              background: "rgba(7, 11, 20, 0.75)",
              borderRadius: "12px",
              border: "1px solid rgba(37, 99, 235, 0.18)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "0.78rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "#60a5fa" }}>
                Filter by Chapter (14 NCERT Units Available):
              </span>
              {selectedChapter !== null && (
                <button
                  type="button"
                  style={{
                    background: "none",
                    border: "none",
                    color: "#93c5fd",
                    cursor: "pointer",
                    fontSize: "0.75rem",
                    textDecoration: "underline",
                  }}
                  onClick={() => setSelectedChapter(null)}
                >
                  Show All Chapters
                </button>
              )}
            </div>
            <div
              style={{
                display: "flex",
                gap: "6px",
                overflowX: "auto",
                paddingBottom: "4px",
              }}
            >
              <button
                type="button"
                className={`suggestion-chip ${selectedChapter === null ? "active" : ""}`}
                style={{
                  background: selectedChapter === null ? "#2563eb" : "rgba(37, 99, 235, 0.12)",
                  color: selectedChapter === null ? "#ffffff" : "#bfdbfe",
                  border: selectedChapter === null ? "1px solid #60a5fa" : "1px solid rgba(37, 99, 235, 0.3)",
                  whiteSpace: "nowrap",
                  padding: "4px 10px",
                  fontSize: "0.78rem",
                  fontWeight: 600,
                  borderRadius: "8px",
                  cursor: "pointer",
                }}
                onClick={() => setSelectedChapter(null)}
              >
                All Chapters
              </button>
              {NCERT_MATH_CHAPTERS.map((ch) => {
                const isActive = selectedChapter === ch.num;
                return (
                  <button
                    key={ch.num}
                    type="button"
                    className={`suggestion-chip ${isActive ? "active" : ""}`}
                    style={{
                      background: isActive ? "#2563eb" : "rgba(37, 99, 235, 0.12)",
                      color: isActive ? "#ffffff" : "#bfdbfe",
                      border: isActive ? "1px solid #60a5fa" : "1px solid rgba(37, 99, 235, 0.3)",
                      whiteSpace: "nowrap",
                      padding: "4px 10px",
                      fontSize: "0.78rem",
                      fontWeight: 600,
                      borderRadius: "8px",
                      cursor: "pointer",
                    }}
                    onClick={() => setSelectedChapter(ch.num)}
                    title={ch.title}
                  >
                    Ch {ch.num}: {ch.title}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="source-banner">
          <span className={`source-dot ${usingTranscript ? "live" : ""}`} />
          <div>
            <strong>{sourceTitle}</strong>
            <span>
              {sourceKind} ·{" "}
              {usingTranscript
                ? `${lines.length} captured utterance${lines.length === 1 ? "" : "s"}`
                : isMath
                  ? "offline doubts Q&A across all 14 chapters (jemh101.pdf - jemh114.pdf)"
                  : "answers fall back to the selected NCERT demo"}
            </span>
          </div>
          <span className="chip">{response ? "retrieved" : "ready"}</span>
        </div>

        <form
          className="ask-form"
          onSubmit={(event) => {
            event.preventDefault();
            void runAsk(question);
          }}
        >
          <div className="ask-input-row">
            <span className="ask-input-icon">
              <SearchIcon />
            </span>
            <input
              id="ask-question"
              className="text-input ask-input"
              type="text"
              value={question}
              maxLength={500}
              placeholder="Ask a syllabus question, e.g. what is the discriminant?"
              onChange={(event) => setQuestion(event.target.value)}
              disabled={loading}
              autoComplete="off"
            />
            <button
              type="submit"
              className="btn primary"
              disabled={loading || question.trim().length < 2}
            >
              {loading ? <span className="spinner small" /> : <SearchIcon />}
              {loading ? "Retrieving…" : "Ask"}
            </button>
          </div>
        </form>

        {suggestions.length > 0 ? (
          <div className="suggestion-row">
            <span className="suggestion-label">Try</span>
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="suggestion-chip"
                onClick={() => void runAsk(suggestion)}
                disabled={loading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        ) : null}

        {error ? (
          <div className="inline-warning error flush">
            <WarningIcon />
            <span>{error}</span>
          </div>
        ) : null}

        {loading ? (
          <div className="study-loading">
            <span className="spinner" />
            <div>
              <strong>Searching the lecture and syllabus…</strong>
              <p>BM25 and on-device embeddings rank passages; the answer quotes a source.</p>
            </div>
          </div>
        ) : response ? (
          <article className={`answer-card ${response.answerable ? "" : "refused"}`}>
            <div className="answer-meta">
              <span className={`chip ${response.answerable ? "chip-accent" : "chip-warn"}`}>
                {response.answerable ? <SparkIcon /> : <WarningIcon />}
                {response.answerable ? "Grounded answer" : "No source above threshold"}
              </span>
              {response.answerable ? (
                <>
                  <span
                    className="chip"
                    style={{
                      background: "rgba(37, 99, 235, 0.25)",
                      border: "1px solid #2563eb",
                      color: "#93c5fd",
                      fontWeight: 600,
                    }}
                  >
                    ⚡ Qwen 3.5 Local LLM Grounded (Offline)
                  </span>
                  <span
                    className="chip"
                    style={{
                      background: "rgba(16, 185, 129, 0.2)",
                      color: "#6ee7b7",
                      border: "1px solid rgba(16, 185, 129, 0.4)",
                      fontWeight: 600,
                    }}
                  >
                    Confidence: {Math.round(response.confidence * 100)}%
                  </span>
                  <span className="chip">{response.engine}</span>
                  <span className="chip">{response.latency_s.toFixed(2)} s latency</span>
                </>
              ) : null}
            </div>

            <p className="answer-question">{response.question}</p>
            <p className="answer-text">{response.answer}</p>

            {response.answerable && topics.length > 0 ? (
              <div className="answer-topics">
                {topics.map((topic) => (
                  <span key={`${topic.chapter_number}-${topic.chapter_title}`} className="topic-pill">
                    <BookIcon />
                    {topic.chapter_number}. {topic.chapter_title ?? "NCERT chapter"}
                  </span>
                ))}
              </div>
            ) : null}

            {response.citations.length > 0 ? (
              <div className="citation-list">
                <p className="citation-heading">
                  Citations · {response.citations.length} retrieved passage
                  {response.citations.length === 1 ? "" : "s"}
                </p>
                {response.citations.map((citation) => (
                  <div key={citation.id} className="citation-card">
                    <div className="citation-top">
                      <span className="citation-source">
                        {citation.source === "syllabus" ? "Syllabus" : "Lecture"}
                      </span>
                      <span className="citation-title">
                        {citation.chapter_number ? `${citation.chapter_number}. ` : ""}
                        {citation.chapter_title ?? citation.title}
                      </span>
                      <span className="citation-score">
                        {Math.round(citation.score * 100)}%
                      </span>
                    </div>
                    <p className="citation-snippet">{citation.snippet}</p>
                    <div className="citation-foot">
                      {citation.start !== null ? (
                        <span>at {formatTime(citation.start)}</span>
                      ) : (
                        <span>{citation.title}</span>
                      )}
                      <span>{citation.source}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="answer-note">
                Nothing in the selected lecture or syllabus crossed the grounding threshold,
                so the assistant refused rather than invent an answer.
              </p>
            )}
          </article>
        ) : (
          <div className="study-empty">
            <span className="empty-icon-wrap">
              <BookIcon />
            </span>
            <h3>Answers you can trace</h3>
            <p>
              Ask about the current lecture. Every answer names the NCERT chapter it came
              from, and questions outside the syllabus are refused instead of guessed.
            </p>
            <p className="empty-subtext">
              {usingTranscript
                ? "The live transcript is the source of truth for this session."
                : "No transcript yet — questions use the selected NCERT demo lecture."}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
