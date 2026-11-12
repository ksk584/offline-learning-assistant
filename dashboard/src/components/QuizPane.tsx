import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  answerQuiz,
  generateRemediation,
  getGaps,
  startQuiz,
  submitRemediation,
} from "../api";
import { messageOf } from "../format";
import type {
  AnswerSource,
  ChapterSummary,
  DemoLine,
  GapsResponse,
  MasteryRow,
  QuizAnswerResponse,
  QuizProgress,
  QuizQuestion,
  RemediationAnswerResult,
  RemediationPack,
} from "../types";
import { BookIcon, CheckIcon, PlayIcon, SparkIcon, WarningIcon } from "./icons";

interface QuizPaneProps {
  classLevel: number;
  subject: string;
  subjectLabel: string;
  courseLabel: string | null;
  chapters: ChapterSummary[];
  lines: DemoLine[];
  sourceHint: string;
  onSelectSubject?: (subject: string) => void;
}

const NCERT_MATH_CHAPTERS: ChapterSummary[] = [
  { number: 1, title: "Real Numbers" },
  { number: 2, title: "Polynomials" },
  { number: 3, title: "Pair of Linear Equations in Two Variables" },
  { number: 4, title: "Quadratic Equations" },
  { number: 5, title: "Arithmetic Progressions" },
  { number: 6, title: "Triangles" },
  { number: 7, title: "Coordinate Geometry" },
  { number: 8, title: "Introduction to Trigonometry" },
  { number: 9, title: "Some Applications of Trigonometry" },
  { number: 10, title: "Circles" },
  { number: 11, title: "Areas Related to Circles" },
  { number: 12, title: "Surface Areas and Volumes" },
  { number: 13, title: "Statistics" },
  { number: 14, title: "Probability" },
];

interface ActiveQuiz {
  id: string;
  question: QuizQuestion;
  progress: QuizProgress;
  targetDifficulty: number;
  mastery: MasteryRow[];
  total: number;
  source: AnswerSource;
  topics: string[];
  topic: string | null;
}

const STUDENT_KEY = "ila.studentId";
const LETTERS = ["A", "B", "C", "D", "E", "F"];
const DIFFICULTY_LABELS: Record<number, string> = {
  1: "Foundation",
  2: "Core",
  3: "Challenge",
};

function loadStudentId(): string {
  try {
    return window.localStorage.getItem(STUDENT_KEY) || "demo-student";
  } catch {
    return "demo-student";
  }
}

function mergeMastery(rows: MasteryRow[], row: MasteryRow): MasteryRow[] {
  const next = rows.some((item) => item.topic === row.topic)
    ? rows.map((item) => (item.topic === row.topic ? row : item))
    : [...rows, row];
  return next.sort((first, second) => first.mastery - second.mastery);
}

function masteryClass(score: number): string {
  if (score < 0.4) return "weak";
  if (score < 0.7) return "ok";
  return "strong";
}

export function QuizPane({
  classLevel,
  subject,
  subjectLabel,
  courseLabel,
  chapters,
  lines,
  sourceHint,
  onSelectSubject,
}: QuizPaneProps) {
  const [currentSubject, setCurrentSubject] = useState(subject);
  const [studentId, setStudentId] = useState(loadStudentId);
  const [length, setLength] = useState(5);
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [active, setActive] = useState<ActiveQuiz | null>(null);
  const [feedback, setFeedback] = useState<QuizAnswerResponse | null>(null);
  const [finished, setFinished] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [shortAnswer, setShortAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [answering, setAnswering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gaps, setGaps] = useState<GapsResponse | null>(null);
  const [questionStartedAt, setQuestionStartedAt] = useState(() => Date.now());

  useEffect(() => {
    setCurrentSubject(subject);
  }, [subject]);

  const handleSwitchSubject = (newSubject: string) => {
    setCurrentSubject(newSubject);
    setTopic("");
    setActive(null);
    setFeedback(null);
    setFinished(false);
    setSelected(null);
    setShortAnswer("");
    setError(null);
    onSelectSubject?.(newSubject);
  };

  // Auto-Remediation state
  const [remediationPack, setRemediationPack] = useState<RemediationPack | null>(null);
  const [remediationLoading, setRemediationLoading] = useState(false);
  const [remediationError, setRemediationError] = useState<string | null>(null);
  const [remediationIndex, setRemediationIndex] = useState(0);
  const [remediationAnswer, setRemediationAnswer] = useState("");
  const [remediationSelected, setRemediationSelected] = useState<number | null>(null);
  const [remediationResult, setRemediationResult] = useState<RemediationAnswerResult | null>(null);
  const [remediationSubmitting, setRemediationSubmitting] = useState(false);
  const [remediationStartedAt, setRemediationStartedAt] = useState(() => Date.now());
  const [remediationCompleted, setRemediationCompleted] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  // KaTeX auto-render hook for mathematical formulas ($b^2 - 4ac$, $p/q$, $\sqrt{2}$, etc.)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const timer = setTimeout(() => {
        const renderMathInElement = (window as any).renderMathInElement;
        if (renderMathInElement && containerRef.current) {
          try {
            renderMathInElement(containerRef.current, {
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
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [feedback, remediationResult, active, remediationIndex]);

  const trimmedStudent = studentId.trim();

  useEffect(() => {
    try {
      if (trimmedStudent) window.localStorage.setItem(STUDENT_KEY, trimmedStudent);
    } catch {
      // Private mode: keep the id in memory only.
    }
  }, [trimmedStudent]);

  useEffect(() => {
    setActive(null);
    setFeedback(null);
    setFinished(false);
    setSelected(null);
    setShortAnswer("");
    setError(null);
  }, [classLevel, currentSubject]);

  useEffect(() => {
    if (!trimmedStudent) {
      setGaps(null);
      return;
    }
    let mounted = true;
    const timer = window.setTimeout(() => {
      getGaps(trimmedStudent)
        .then((result) => {
          if (mounted) setGaps(result);
        })
        .catch(() => {
          // Gaps are supplementary; a failed lookup must not block the quiz.
        });
    }, 350);
    return () => {
      mounted = false;
      window.clearTimeout(timer);
    };
  }, [trimmedStudent]);

  const start = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      const session = await startQuiz({
        studentId: trimmedStudent || "demo-student",
        classLevel,
        subject: currentSubject,
        topic: topic || null,
        length,
        difficulty: difficulty ? Number(difficulty) : null,
        lines,
      });
      setActive({
        id: session.quiz_id,
        question: session.question,
        progress: session.progress,
        targetDifficulty: session.question.difficulty,
        mastery: session.mastery,
        total: session.total,
        source: session.source,
        topics: session.topics,
        topic: session.topic,
      });
      setFeedback(null);
      setFinished(false);
      setSelected(null);
      setShortAnswer("");
      setQuestionStartedAt(Date.now());
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      setLoading(false);
    }
  }, [classLevel, currentSubject, difficulty, length, lines, loading, topic, trimmedStudent]);

  const submit = useCallback(async () => {
    if (!active || feedback || answering) return;
    const question = active.question;
    if (question.kind === "mcq" && selected === null) return;
    if (question.kind === "short" && !shortAnswer.trim()) return;

    setAnswering(true);
    setError(null);
    try {
      const result = await answerQuiz({
        quizId: active.id,
        questionId: question.id,
        answer: question.kind === "short" ? shortAnswer.trim() : "",
        answerIndex: question.kind === "mcq" ? selected : null,
        responseMs: Math.max(0, Date.now() - questionStartedAt),
      });
      setFeedback(result);
      setGaps(result.gaps);
      setActive((current) =>
        current
          ? {
              ...current,
              progress: result.progress,
              targetDifficulty: result.target_difficulty,
              mastery: mergeMastery(current.mastery, result.mastery),
            }
          : current,
      );
      if (result.completed) setFinished(true);
    } catch (caught) {
      setError(messageOf(caught));
    } finally {
      setAnswering(false);
    }
  }, [active, answering, feedback, questionStartedAt, selected, shortAnswer]);

  const next = useCallback(() => {
    if (!active || !feedback) return;
    const upcoming = feedback.next_question;
    if (!upcoming) {
      setFinished(true);
      return;
    }
    setActive({ ...active, question: upcoming, progress: feedback.progress });
    setFeedback(null);
    setSelected(null);
    setShortAnswer("");
    setError(null);
    setQuestionStartedAt(Date.now());
  }, [active, feedback]);

  const endQuiz = useCallback(() => {
    setActive(null);
    setFeedback(null);
    setFinished(false);
    setSelected(null);
    setShortAnswer("");
    setError(null);
  }, []);

  const handleStartRemediation = useCallback(
    async (topicName?: string) => {
      setRemediationLoading(true);
      setRemediationError(null);
      setRemediationResult(null);
      setRemediationIndex(0);
      setRemediationCompleted(false);
      setRemediationAnswer("");
      setRemediationSelected(null);
      try {
        const pack = await generateRemediation({
          studentId: trimmedStudent || "demo-student",
          topic: topicName || null,
          classLevel,
          subject: currentSubject,
          count: 3,
          lines,
        });
        setRemediationPack(pack);
        setRemediationStartedAt(Date.now());
      } catch (err) {
        setRemediationError(messageOf(err));
      } finally {
        setRemediationLoading(false);
      }
    },
    [classLevel, currentSubject, lines, trimmedStudent],
  );

  const handleSubmitRemediation = useCallback(async () => {
    if (!remediationPack || remediationSubmitting) return;
    const currentItem = remediationPack.items[remediationIndex];
    if (!currentItem) return;
    setRemediationSubmitting(true);
    setRemediationError(null);
    try {
      const elapsed = Math.max(500, Date.now() - remediationStartedAt);
      const res = await submitRemediation({
        packId: remediationPack.pack_id,
        studentId: trimmedStudent || "demo-student",
        itemId: currentItem.id,
        answer: remediationAnswer,
        selectedIndex: remediationSelected,
        responseMs: elapsed,
      });
      setRemediationResult(res);
      // Refresh gaps and mastery in background
      if (trimmedStudent) {
        void getGaps(trimmedStudent).then((resGaps) => setGaps(resGaps)).catch(() => {});
      }
    } catch (err) {
      setRemediationError(messageOf(err));
    } finally {
      setRemediationSubmitting(false);
    }
  }, [
    remediationAnswer,
    remediationIndex,
    remediationPack,
    remediationSelected,
    remediationStartedAt,
    remediationSubmitting,
    trimmedStudent,
  ]);

  const handleNextRemediation = useCallback(() => {
    if (!remediationPack) return;
    if (remediationIndex + 1 < remediationPack.items.length) {
      setRemediationIndex((prev) => prev + 1);
      setRemediationAnswer("");
      setRemediationSelected(null);
      setRemediationResult(null);
      setRemediationStartedAt(Date.now());
    } else {
      setRemediationCompleted(true);
    }
  }, [remediationIndex, remediationPack]);

  const handleCloseRemediation = useCallback(() => {
    setRemediationPack(null);
    setRemediationResult(null);
    setRemediationCompleted(false);
    setRemediationError(null);
    if (trimmedStudent) {
      void getGaps(trimmedStudent).then((resGaps) => setGaps(resGaps)).catch(() => {});
    }
  }, [trimmedStudent]);

  const question = active?.question ?? null;
  const showResult = feedback !== null;
  const expectedOption = feedback?.expected ?? null;
  const isMath = currentSubject === "maths";
  const topicOptions = useMemo(() => {
    if (isMath && classLevel === 10) {
      return NCERT_MATH_CHAPTERS;
    }
    return [...chapters].sort((first, second) => first.number - second.number);
  }, [chapters, isMath, classLevel]);
  const mastery = active?.mastery ?? [];
  const weakest = gaps?.gaps ?? [];

  const progressPercent = active
    ? Math.round((active.progress.answered / Math.max(1, active.progress.total)) * 100)
    : 0;

  return (
    <section className="panel study-panel quiz-pane" ref={containerRef}>
      <header className="panel-header">
        <div>
          <p className="panel-kicker">Adaptive practice · mastery in SQLite</p>
          <h2>Practice quiz</h2>
        </div>
        <div className="panel-actions">
          <span className="chip chip-accent">
            <SparkIcon />
            {isMath
              ? "Class 10 Mathematics (14 Textbooks)"
              : (courseLabel ?? `Class ${classLevel} ${subjectLabel}`)}
          </span>
          {active ? (
            <button type="button" className="btn ghost compact" onClick={endQuiz}>
              End quiz
            </button>
          ) : null}
        </div>
      </header>

      <div className="study-body">
        {/* Subject Switcher Bar */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            marginBottom: "16px",
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
        {remediationError ? (
          <div className="inline-warning error flush" style={{ marginBottom: "16px" }}>
            <WarningIcon />
            <span>{remediationError}</span>
          </div>
        ) : null}

        {/* Auto-Remediation Modal / Drill View */}
        {remediationLoading ? (
          <div className="study-loading" style={{ margin: "20px 0", padding: "24px" }}>
            <span className="spinner" />
            <div>
              <strong>Generating Auto-Remediation Drill…</strong>
              <p>Analyzing knowledge gaps, extracting NCERT passages, and generating targeted primer &amp; questions with local Qwen 3.5 LLM.</p>
            </div>
          </div>
        ) : remediationPack ? (
          <div
            className="remediation-drill-container"
            style={{
              background: "rgba(11, 19, 43, 0.95)",
              border: "1px solid rgba(59, 130, 246, 0.4)",
              borderRadius: "12px",
              padding: "24px",
              marginBottom: "24px",
              boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: "16px",
                borderBottom: "1px solid rgba(59, 130, 246, 0.2)",
                paddingBottom: "12px",
              }}
            >
              <div>
                <span
                  className="chip"
                  style={{
                    background: "rgba(37, 99, 235, 0.25)",
                    color: "#93c5fd",
                    border: "1px solid #2563eb",
                    fontWeight: 700,
                    marginBottom: "6px",
                  }}
                >
                  🎯 Auto-Remediation Drill · Closing Knowledge Gaps
                </span>
                <h3 style={{ margin: "6px 0 2px 0", fontSize: "1.25rem", color: "#f8fafc" }}>
                  {remediationPack.topic}
                </h3>
                <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                  Powered by Local Qwen 3.5 LLM · Grounded on NCERT Textbooks · Student:{" "}
                  <strong>{remediationPack.student_id}</strong>
                </span>
              </div>
              <button
                type="button"
                className="btn ghost compact"
                onClick={handleCloseRemediation}
              >
                ✕ Close Drill
              </button>
            </div>

            {/* Conceptual Foundation Primer */}
            <div
              style={{
                background: "rgba(15, 23, 42, 0.8)",
                borderLeft: "4px solid #3b82f6",
                padding: "14px 18px",
                borderRadius: "4px 8px 8px 4px",
                marginBottom: "20px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  marginBottom: "6px",
                }}
              >
                <SparkIcon />
                <strong style={{ color: "#60a5fa", fontSize: "0.9rem" }}>
                  Core Concept Primer (NCERT Textbooks):
                </strong>
              </div>
              <p
                style={{
                  margin: 0,
                  fontSize: "0.88rem",
                  lineHeight: 1.6,
                  color: "#e2e8f0",
                }}
              >
                {remediationPack.primer}
              </p>
            </div>

            {remediationCompleted ? (
              <div style={{ textAlign: "center", padding: "24px 12px" }}>
                <div style={{ fontSize: "2.5rem", marginBottom: "8px" }}>🎉</div>
                <h3 style={{ color: "#34d399", margin: "0 0 8px 0" }}>
                  Remediation Complete!
                </h3>
                <p
                  style={{
                    color: "#94a3b8",
                    maxWidth: "500px",
                    margin: "0 auto 18px auto",
                    fontSize: "0.9rem",
                  }}
                >
                  Great work! You have completed all targeted remediation items for this topic.
                  Your updated mastery score has been recorded into SQLite storage.
                </p>
                <button
                  type="button"
                  className="btn primary"
                  onClick={handleCloseRemediation}
                >
                  Done · Return to Practice
                </button>
              </div>
            ) : (
              <div>
                {/* Practice Item Header */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "12px",
                  }}
                >
                  <span style={{ fontSize: "0.82rem", color: "#94a3b8", fontWeight: 600 }}>
                    Practice Item {remediationIndex + 1} of {remediationPack.items.length}
                  </span>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span
                      className="chip"
                      style={{ textTransform: "uppercase", fontSize: "0.72rem" }}
                    >
                      {remediationPack.items[remediationIndex]?.kind.replace("_", " ")}
                    </span>
                    <span
                      className="chip chip-accent"
                      style={{ fontSize: "0.72rem" }}
                    >
                      Difficulty {remediationPack.items[remediationIndex]?.difficulty}
                    </span>
                  </div>
                </div>

                {/* Prompt */}
                <p
                  style={{
                    fontSize: "1.05rem",
                    fontWeight: 600,
                    color: "#f8fafc",
                    margin: "0 0 16px 0",
                    lineHeight: 1.5,
                  }}
                >
                  {remediationPack.items[remediationIndex]?.prompt}
                </p>

                {/* Answer Options */}
                {remediationPack.items[remediationIndex]?.kind === "mcq" ? (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                      marginBottom: "18px",
                    }}
                  >
                    {remediationPack.items[remediationIndex]?.options.map((opt, idx) => (
                      <button
                        key={opt}
                        type="button"
                        disabled={remediationResult !== null || remediationSubmitting}
                        onClick={() => setRemediationSelected(idx)}
                        style={{
                          textAlign: "left",
                          padding: "10px 14px",
                          borderRadius: "8px",
                          border:
                            remediationSelected === idx
                              ? "1px solid #3b82f6"
                              : "1px solid rgba(255,255,255,0.1)",
                          background:
                            remediationSelected === idx
                              ? "rgba(37, 99, 235, 0.3)"
                              : "rgba(15, 23, 42, 0.6)",
                          color: "#f1f5f9",
                          cursor: remediationResult !== null ? "default" : "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                          fontSize: "0.9rem",
                        }}
                      >
                        <span
                          style={{
                            fontWeight: 700,
                            color: remediationSelected === idx ? "#60a5fa" : "#94a3b8",
                          }}
                        >
                          {LETTERS[idx] ?? idx + 1}.
                        </span>
                        <span>{opt}</span>
                      </button>
                    ))}
                  </div>
                ) : remediationPack.items[remediationIndex]?.kind === "true_false" ? (
                  <div style={{ display: "flex", gap: "12px", marginBottom: "18px" }}>
                    {["True", "False"].map((tf) => (
                      <button
                        key={tf}
                        type="button"
                        disabled={remediationResult !== null || remediationSubmitting}
                        onClick={() => setRemediationAnswer(tf)}
                        style={{
                          flex: 1,
                          padding: "12px",
                          borderRadius: "8px",
                          fontWeight: 700,
                          border:
                            remediationAnswer.toLowerCase() === tf.toLowerCase()
                              ? "1px solid #3b82f6"
                              : "1px solid rgba(255,255,255,0.1)",
                          background:
                            remediationAnswer.toLowerCase() === tf.toLowerCase()
                              ? "rgba(37, 99, 235, 0.3)"
                              : "rgba(15, 23, 42, 0.6)",
                          color: "#f1f5f9",
                          cursor: remediationResult !== null ? "default" : "pointer",
                        }}
                      >
                        {tf}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div style={{ marginBottom: "18px" }}>
                    <input
                      type="text"
                      className="text-input"
                      placeholder="Type your answer here…"
                      value={remediationAnswer}
                      onChange={(e) => setRemediationAnswer(e.target.value)}
                      disabled={remediationResult !== null || remediationSubmitting}
                      style={{ width: "100%", padding: "10px 14px", fontSize: "0.95rem" }}
                    />
                  </div>
                )}

                {/* Remediation Result Feedback Box */}
                {remediationResult ? (
                  <div className="nlm-feedback-container">
                    <div className="nlm-feedback-status-bar">
                      <div className="nlm-status-left">
                        <span
                          className={`nlm-status-badge ${remediationResult.correct ? "correct" : "wrong"}`}
                        >
                          {remediationResult.correct ? <CheckIcon /> : <WarningIcon />}
                          <span>{remediationResult.correct ? "Correct! Well Done" : "Review Needed"}</span>
                        </span>
                        <span className="nlm-chip">
                          Mastery: {Math.round(remediationResult.prev_mastery * 100)}% ➔{" "}
                          <strong>{Math.round(remediationResult.updated_mastery * 100)}%</strong>
                        </span>
                      </div>
                      {remediationResult.post_diagnosis && (
                        <span className="nlm-chip nlm-target-chip">
                          Tier: <strong>{remediationResult.post_diagnosis.tier_label}</strong> ({Math.round(remediationResult.post_diagnosis.gap_probability * 100)}%)
                        </span>
                      )}
                    </div>

                    {/* NotebookLM Answer Comparison Diff */}
                    {!remediationResult.correct && (
                      <div className="nlm-answer-diff-card">
                        {remediationResult.submitted && (
                          <div className="diff-row your-answer">
                            <span className="diff-label">Your answer:</span>
                            <span className="diff-val">{remediationResult.submitted}</span>
                          </div>
                        )}
                        <div className="diff-row expected-answer">
                          <span className="diff-label">Expected definition:</span>
                          <span className="diff-val">{remediationResult.expected}</span>
                        </div>
                      </div>
                    )}

                    {/* 💡 Built-in Concept Explanation Card */}
                    <div className="concept-explanation-card">
                      <div className="concept-explanation-header">
                        <div className="concept-header-left">
                          <span className="concept-bulb-icon">💡</span>
                          <span className="concept-card-title">Built-in Concept Explanation</span>
                        </div>
                        <span className="ncert-badge">📘 NCERT Syllabus Grounded</span>
                      </div>

                      {/* Meaning & Intent Analysis */}
                      {remediationResult.evaluation_reason && (
                        <div className="concept-intent-box">
                          <div className="intent-box-head">
                            <SparkIcon />
                            <span>
                              Meaning &amp; Intent Analysis{" "}
                              {remediationResult.evaluator === "llm"
                                ? "· Local Qwen 3.5 LLM"
                                : remediationResult.evaluator === "math_concept"
                                  ? "· Mathematical Equivalence"
                                  : remediationResult.evaluator
                                    ? `· ${remediationResult.evaluator}`
                                    : ""}
                            </span>
                          </div>
                          <p className="intent-box-text">{remediationResult.evaluation_reason}</p>
                        </div>
                      )}

                      {/* Grounded Concept Markdown Body */}
                      {remediationResult.explanation && (
                        <div className="concept-explanation-body">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {remediationResult.explanation}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  </div>
                ) : null}

                {/* Action Buttons */}
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                  {remediationResult ? (
                    <button
                      type="button"
                      className="btn primary"
                      onClick={handleNextRemediation}
                    >
                      {remediationIndex + 1 < remediationPack.items.length
                        ? "Next Item ➔"
                        : "Complete Drill 🎉"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn primary"
                      onClick={() => void handleSubmitRemediation()}
                      disabled={
                        remediationSubmitting ||
                        (remediationPack.items[remediationIndex]?.kind === "mcq"
                          ? remediationSelected === null
                          : remediationAnswer.trim().length === 0)
                      }
                    >
                      {remediationSubmitting ? "Checking…" : "Check Answer"}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : null}

        {!active ? (
          <div className="quiz-start">
            <div className="quiz-start-copy">
              <span className="empty-icon-wrap">
                <BookIcon />
              </span>
              <div>
                <h3>Questions built from this lecture</h3>
                <p>
                  Every question is generated from a definition or statement in the lecture
                  or notes — nothing is invented. Difficulty adapts after each answer.
                </p>
                <p className="empty-subtext">
                  Source:{" "}
                  <strong>
                    {lines.length
                      ? `${lines.length} captured utterances`
                      : isMath
                        ? "NCERT Class 10 Mathematics Textbook (All 14 Chapters)"
                        : `${sourceHint} (NCERT demo)`}
                  </strong>
                </p>
              </div>
            </div>

            <div className="quiz-setup-grid">
              <div className="field">
                <label htmlFor="quiz-student">Student</label>
                <input
                  id="quiz-student"
                  className="text-input"
                  value={studentId}
                  maxLength={120}
                  onChange={(event) => setStudentId(event.target.value)}
                  placeholder="demo-student"
                />
              </div>
              <div className="field">
                <label htmlFor="quiz-topic">Topic</label>
                <select
                  id="quiz-topic"
                  className="select"
                  value={topic}
                  onChange={(event) => setTopic(event.target.value)}
                >
                  <option value="">All available topics</option>
                  {topicOptions.map((chapter) => (
                    <option key={chapter.number} value={String(chapter.number)}>
                      {chapter.number}. {chapter.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="quiz-length">Questions</label>
                <select
                  id="quiz-length"
                  className="select"
                  value={length}
                  onChange={(event) => setLength(Number(event.target.value))}
                >
                  {[3, 5, 8, 10].map((count) => (
                    <option key={count} value={count}>
                      {count} questions
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="quiz-difficulty">Starting difficulty</label>
                <select
                  id="quiz-difficulty"
                  className="select"
                  value={difficulty}
                  onChange={(event) => setDifficulty(event.target.value)}
                >
                  <option value="">Adaptive from mastery</option>
                  <option value="1">1 · Foundation</option>
                  <option value="2">2 · Core</option>
                  <option value="3">3 · Challenge</option>
                </select>
              </div>
            </div>

            <div className="quiz-start-actions">
              <button
                type="button"
                className="btn primary"
                onClick={() => void start()}
                disabled={loading || !trimmedStudent}
              >
                {loading ? <span className="spinner small" /> : <PlayIcon />}
                {loading ? "Building questions…" : "Start quiz"}
              </button>
              <span className="quiz-start-note">
                Mastery is saved per student id.
              </span>
            </div>
          </div>
        ) : (
          <div className="quiz-layout">
            <div className="quiz-main">
              <div className="quiz-progress-row">
                <div className="quiz-progress-meta">
                  <span>
                    Question {Math.min(active.progress.answered + 1, active.progress.total)} of{" "}
                    {active.progress.total}
                  </span>
                  <span>
                    {active.progress.correct} correct ·{" "}
                    {Math.round(active.progress.score * 100)}%
                  </span>
                </div>
                <div className="quiz-progress-track">
                  <span style={{ width: `${progressPercent}%` }} />
                </div>
              </div>

              {question ? (
                <article className="quiz-question">
                  <div className="quiz-question-meta">
                    <span className={`chip ${question.kind === "mcq" ? "chip-accent" : ""}`}>
                      {question.kind === "mcq" ? "Multiple choice" : "Short answer"}
                    </span>
                    <span className="chip">{question.topic}</span>
                    <span className="chip">
                      Difficulty {question.difficulty} ·{" "}
                      {DIFFICULTY_LABELS[question.difficulty] ?? "Core"}
                    </span>
                    <span className="chip">
                      {question.chapter_number
                        ? `Chapter ${question.chapter_number}`
                        : question.source}
                    </span>
                  </div>

                  <h3 className="quiz-prompt">{question.prompt}</h3>

                  {question.kind === "mcq" ? (
                    <div className="quiz-options">
                      {question.options.map((option, index) => {
                        const isSelected = selected === index;
                        const isCorrect = showResult && expectedOption === option;
                        const isWrong = showResult && isSelected && !isCorrect;
                        return (
                          <button
                            key={`${question.id}-${index}`}
                            type="button"
                            className={`quiz-option ${isSelected ? "selected" : ""} ${
                              isCorrect ? "correct" : ""
                            } ${isWrong ? "wrong" : ""}`}
                            onClick={() => setSelected(index)}
                            disabled={showResult || answering}
                          >
                            <span className="option-letter">{LETTERS[index] ?? index + 1}</span>
                            <span>{option}</span>
                            {isCorrect ? <CheckIcon /> : null}
                            {isWrong ? <WarningIcon /> : null}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="quiz-short-answer">
                      <label htmlFor="quiz-answer">Your answer</label>
                      <textarea
                        id="quiz-answer"
                        className="quiz-textarea"
                        value={shortAnswer}
                        onChange={(event) => setShortAnswer(event.target.value)}
                        placeholder="Write the key idea or formula in one line."
                        rows={2}
                        disabled={showResult || answering}
                      />
                      {showResult ? (
                        <p className="quiz-expected">
                          Expected: <strong>{feedback?.expected}</strong>
                        </p>
                      ) : null}
                    </div>
                  )}

                  {showResult ? (
                    <div className="nlm-feedback-container">
                      <div className="nlm-feedback-status-bar">
                        <div className="nlm-status-left">
                          <span
                            className={`nlm-status-badge ${feedback?.correct ? "correct" : "wrong"}`}
                          >
                            {feedback?.correct ? <CheckIcon /> : <WarningIcon />}
                            <span>{feedback?.correct ? "Correct! Well Done" : "Review Needed"}</span>
                          </span>
                          <span className="nlm-chip">
                            Mastery: <strong>{Math.round((feedback?.mastery.mastery ?? 0) * 100)}%</strong>
                          </span>
                        </div>
                        <span className="nlm-chip nlm-target-chip">
                          Next target: <strong>{DIFFICULTY_LABELS[feedback?.target_difficulty ?? 2] ?? "Core"}</strong>
                        </span>
                      </div>

                      {/* NotebookLM Answer Comparison Diff */}
                      {!feedback?.correct && (
                        <div className="nlm-answer-diff-card">
                          {(feedback?.response || (selected !== null && question.options[selected])) && (
                            <div className="diff-row your-answer">
                              <span className="diff-label">Your selection:</span>
                              <span className="diff-val">
                                {feedback?.response || question.options[selected!]}
                              </span>
                            </div>
                          )}
                          <div className="diff-row expected-answer">
                            <span className="diff-label">
                              {question.kind === "mcq" ? "Correct syllabus option:" : "Expected standard definition:"}
                            </span>
                            <span className="diff-val">{feedback?.expected}</span>
                          </div>
                        </div>
                      )}

                      {/* 💡 Built-in Concept Explanation Card */}
                      <div className="concept-explanation-card">
                        <div className="concept-explanation-header">
                          <div className="concept-header-left">
                            <span className="concept-bulb-icon">💡</span>
                            <span className="concept-card-title">Built-in Concept Explanation</span>
                          </div>
                          <span className="ncert-badge">📘 NCERT Syllabus Grounded</span>
                        </div>

                        {/* Meaning & Intent Analysis */}
                        {feedback?.evaluation_reason && (
                          <div className="concept-intent-box">
                            <div className="intent-box-head">
                              <SparkIcon />
                              <span>
                                Meaning &amp; Intent Analysis{" "}
                                {feedback.evaluator === "llm"
                                  ? "· Local Qwen 3.5 LLM"
                                  : feedback.evaluator === "math_concept"
                                    ? "· Mathematical Equivalence"
                                    : feedback.evaluator
                                      ? `· ${feedback.evaluator}`
                                      : ""}
                              </span>
                            </div>
                            <p className="intent-box-text">{feedback.evaluation_reason}</p>
                          </div>
                        )}

                        {/* Grounded Concept Markdown Body */}
                        {feedback?.explanation && (
                          <div className="concept-explanation-body">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {feedback.explanation}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : null}

                  <div className="quiz-actions">
                    {showResult ? (
                      feedback?.completed ? (
                        <button type="button" className="btn primary" onClick={endQuiz}>
                          <SparkIcon />
                          New quiz
                        </button>
                      ) : (
                        <button type="button" className="btn primary" onClick={next}>
                          Next question
                        </button>
                      )
                    ) : (
                      <button
                        type="button"
                        className="btn primary"
                        onClick={() => void submit()}
                        disabled={
                          answering ||
                          (question.kind === "mcq"
                            ? selected === null
                            : shortAnswer.trim().length === 0)
                        }
                      >
                        {answering ? <span className="spinner small" /> : <CheckIcon />}
                        {answering ? "Checking…" : "Check answer"}
                      </button>
                    )}
                    <span className="quiz-source-note">
                      Grounded in {active.source.kind === "demo" ? "NCERT demo" : "lecture"} ·{" "}
                      {active.total} question{active.total === 1 ? "" : "s"} prepared
                    </span>
                  </div>
                </article>
              ) : null}

              {finished ? (
                <div className="quiz-summary">
                  <div className="quiz-summary-head">
                    <div>
                      <p className="panel-kicker">Session complete</p>
                      <h3>
                        {active.progress.correct}/{active.progress.total} correct ·{" "}
                        {Math.round(active.progress.score * 100)}%
                      </h3>
                    </div>
                    <span className="quiz-score-ring">
                      {Math.round(active.progress.score * 100)}%
                    </span>
                  </div>
                  <p className="quiz-summary-note">
                    Mastery moved on {mastery.length} topic
                    {mastery.length === 1 ? "" : "s"}. The next quiz starts at{" "}
                    {DIFFICULTY_LABELS[active.targetDifficulty] ?? "Core"} difficulty.
                  </p>
                  <div className="quiz-summary-actions">
                    <button type="button" className="btn primary" onClick={() => void start()}>
                      <PlayIcon />
                      Practise again
                    </button>
                    <button type="button" className="btn ghost" onClick={endQuiz}>
                      Change settings
                    </button>
                  </div>
                </div>
              ) : null}
            </div>

            <aside className="quiz-side">
              <div className="quiz-side-card">
                <div className="quiz-side-head">
                  <span>Mastery</span>
                  <span className="chip">{trimmedStudent}</span>
                </div>
                {mastery.length ? (
                  <div className="mastery-list">
                    {mastery.map((row) => (
                      <div key={row.topic} className="mastery-row">
                        <div className="mastery-row-top">
                          <span>{row.topic}</span>
                          <span>{Math.round(row.mastery * 100)}%</span>
                        </div>
                        <div className="mastery-track">
                          <span
                            className={masteryClass(row.mastery)}
                            style={{ width: `${Math.round(row.mastery * 100)}%` }}
                          />
                        </div>
                        <span className="mastery-meta">
                          {row.correct}/{row.attempts} correct
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="quiz-side-empty">Answer a question to build mastery.</p>
                )}
              </div>

              <div className="nlm-side-card">
                <div className="nlm-side-head">
                  <div className="nlm-head-title-wrap">
                    <span className="nlm-head-icon">📊</span>
                    <span className="nlm-head-title">Weakest Topics &amp; ML Gaps</span>
                  </div>
                  <span className="nlm-pill-badge">{gaps?.attempts ?? 0} attempts</span>
                </div>
                {weakest.length ? (
                  <div className="nlm-gap-list">
                    {weakest.map((gap) => {
                      const masteryPct = Math.round(gap.mastery * 100);
                      const isCritical = gap.tier === "critical_gap";
                      const isNeedsReview = gap.tier === "needs_review";
                      const tierColor = isCritical ? "#ef4444" : isNeedsReview ? "#f59e0b" : "#10b981";
                      const tierLabel = isCritical ? "Critical Gap" : isNeedsReview ? "Needs Review" : "Proficient";
                      const gapProb = Math.round((gap.gap_probability ?? 0.5) * 100);

                      return (
                        <div key={gap.topic} className="nlm-gap-card">
                          <div className="nlm-gap-top">
                            <div className="nlm-gap-title-group">
                              <span className="nlm-gap-dot" style={{ backgroundColor: tierColor }} />
                              <strong className="nlm-gap-topic-name" title={gap.topic}>
                                {gap.topic}
                              </strong>
                            </div>
                            <span className="nlm-gap-score" style={{ color: tierColor }}>
                              {masteryPct}%
                            </span>
                          </div>

                          <div className="nlm-gap-progress-track">
                            <div
                              className="nlm-gap-progress-fill"
                              style={{
                                width: `${Math.max(6, masteryPct)}%`,
                                backgroundColor: tierColor,
                              }}
                            />
                          </div>

                          <div className="nlm-gap-meta">
                            <span className={`nlm-tier-chip ${gap.tier}`}>
                              {tierLabel} ({gapProb}%)
                            </span>
                            <span className="nlm-rec-chip">
                              Rec: {DIFFICULTY_LABELS[gap.recommended_difficulty] ?? "Core"}
                            </span>
                          </div>

                          {gap.diagnostic_reasons && gap.diagnostic_reasons.length > 0 && (
                            <p className="nlm-gap-reason">{gap.diagnostic_reasons[0]}</p>
                          )}

                          <button
                            type="button"
                            className="nlm-remediate-btn"
                            onClick={() => void handleStartRemediation(gap.topic)}
                            disabled={remediationLoading}
                          >
                            <SparkIcon />
                            <span>Auto-Remediate Gap</span>
                          </button>
                        </div>
                      );
                    })}

                    <button
                      type="button"
                      className="nlm-start-drill-btn"
                      onClick={() => void handleStartRemediation()}
                      disabled={remediationLoading}
                    >
                      <SparkIcon />
                      <span>Start Auto-Remediation Drill</span>
                    </button>
                  </div>
                ) : (
                  <p className="nlm-side-empty">
                    Completed quizzes surface the three weakest topics analyzed by the
                    Decision Tree ML classifier.
                  </p>
                )}
              </div>

              {error ? (
                <div className="inline-warning error flush">
                  <WarningIcon />
                  <span>{error}</span>
                </div>
              ) : null}
            </aside>
          </div>
        )}

        {!active && error ? (
          <div className="inline-warning error flush">
            <WarningIcon />
            <span>{error}</span>
          </div>
        ) : null}
      </div>
    </section>
  );
}
