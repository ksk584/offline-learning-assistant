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
import {
  ArrowRightIcon,
  AwardIcon,
  BarChartIcon,
  BookIcon,
  CheckCircleIcon,
  CheckIcon,
  PlayIcon,
  SparkIcon,
  WarningIcon,
  XIcon,
} from "./icons";

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
          <p className="panel-kicker">Adaptive Practice · SQLite Storage</p>
          <h2>Adaptive Quizzes &amp; Auto-Remediation</h2>
        </div>
        <div className="panel-actions">
          <span className="badge badge-accent">
            <SparkIcon />
            {isMath
              ? "Class 10 Mathematics (14 Textbooks)"
              : (courseLabel ?? `Class ${classLevel} ${subjectLabel}`)}
          </span>
          {active ? (
            <button type="button" className="btn btn-ghost btn-sm" onClick={endQuiz}>
              End Quiz
            </button>
          ) : null}
        </div>
      </header>

      <div className="study-body">
        {/* Subject Switcher Bar */}
        <div className="segmented" style={{ marginBottom: "16px" }}>
          <button
            type="button"
            className={`segmented-btn ${isMath ? "active" : ""}`}
            onClick={() => handleSwitchSubject("maths")}
          >
            <BookIcon />
            <span>Class 10 Mathematics (NCERT)</span>
          </button>
          <button
            type="button"
            className={`segmented-btn ${!isMath ? "active" : ""}`}
            onClick={() => handleSwitchSubject("science")}
          >
            <SparkIcon />
            <span>Class 10 Science (Demo Lecture)</span>
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
          <div className="remediation-drill-card">
            <div className="remediation-header">
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span className="badge badge-accent">
                    <SparkIcon />
                    <span>Auto-Remediation Drill</span>
                  </span>
                  <span className="badge">Student: {remediationPack.student_id}</span>
                </div>
                <h3 style={{ margin: "4px 0", fontSize: "1.15rem", color: "var(--text-primary)" }}>
                  {remediationPack.topic}
                </h3>
                <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                  Powered by Local Qwen 3.5 LLM · Grounded on NCERT Textbooks
                </span>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={handleCloseRemediation}
              >
                <XIcon />
                <span>Close Drill</span>
              </button>
            </div>

            {/* Conceptual Foundation Primer */}
            <div className="remediation-primer-box">
              <strong>
                <SparkIcon />
                <span>Core Concept Primer (NCERT Textbooks):</span>
              </strong>
              <p>{remediationPack.primer}</p>
            </div>

            {remediationCompleted ? (
              <div className="remediation-complete-box">
                <AwardIcon style={{ width: 40, height: 40, color: "var(--success-text)" }} />
                <h3>Remediation Completed</h3>
                <p>
                  Great work! You have completed all targeted remediation items for this topic.
                  Your updated mastery score has been recorded into SQLite storage.
                </p>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleCloseRemediation}
                >
                  Return to Practice
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
                  <span style={{ fontSize: "0.82rem", color: "var(--text-muted)", fontWeight: 600 }}>
                    Practice Item {remediationIndex + 1} of {remediationPack.items.length}
                  </span>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span className="badge" style={{ textTransform: "uppercase" }}>
                      {remediationPack.items[remediationIndex]?.kind.replace("_", " ")}
                    </span>
                    <span className="badge badge-accent">
                      Difficulty {remediationPack.items[remediationIndex]?.difficulty}
                    </span>
                  </div>
                </div>

                {/* Prompt */}
                <h4
                  style={{
                    fontSize: "1.05rem",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                    margin: "0 0 16px 0",
                    lineHeight: 1.5,
                  }}
                >
                  {remediationPack.items[remediationIndex]?.prompt}
                </h4>

                {/* Answer Options */}
                {remediationPack.items[remediationIndex]?.kind === "mcq" ? (
                  <div className="quiz-options-list">
                    {remediationPack.items[remediationIndex]?.options.map((opt, idx) => (
                      <button
                        key={opt}
                        type="button"
                        className={`quiz-option-btn ${remediationSelected === idx ? "selected" : ""}`}
                        disabled={remediationResult !== null || remediationSubmitting}
                        onClick={() => setRemediationSelected(idx)}
                      >
                        <span className="quiz-option-letter">
                          {LETTERS[idx] ?? idx + 1}
                        </span>
                        <span style={{ flex: 1 }}>{opt}</span>
                      </button>
                    ))}
                  </div>
                ) : remediationPack.items[remediationIndex]?.kind === "true_false" ? (
                  <div className="segmented" style={{ marginBottom: "18px" }}>
                    {["True", "False"].map((tf) => (
                      <button
                        key={tf}
                        type="button"
                        disabled={remediationResult !== null || remediationSubmitting}
                        onClick={() => setRemediationAnswer(tf)}
                        className={`segmented-btn ${remediationAnswer.toLowerCase() === tf.toLowerCase() ? "active" : ""}`}
                        style={{ padding: "10px 16px" }}
                      >
                        {tf}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div style={{ marginBottom: "18px" }}>
                    <input
                      type="text"
                      className="input"
                      placeholder="Type your answer here…"
                      value={remediationAnswer}
                      onChange={(e) => setRemediationAnswer(e.target.value)}
                      disabled={remediationResult !== null || remediationSubmitting}
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

                    {/* Built-in Concept Explanation Card */}
                    <div className="concept-explanation-card">
                      <div className="concept-explanation-header">
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <BookIcon />
                          <span className="concept-card-title">Concept Explanation</span>
                        </div>
                        <span className="badge">NCERT Grounded</span>
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
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "16px" }}>
                  {remediationResult ? (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={handleNextRemediation}
                    >
                      {remediationIndex + 1 < remediationPack.items.length ? (
                        <>
                          <span>Next Item</span>
                          <ArrowRightIcon />
                        </>
                      ) : (
                        <>
                          <CheckCircleIcon />
                          <span>Complete Drill</span>
                        </>
                      )}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => void handleSubmitRemediation()}
                      disabled={
                        remediationSubmitting ||
                        (remediationPack.items[remediationIndex]?.kind === "mcq"
                          ? remediationSelected === null
                          : remediationAnswer.trim().length === 0)
                      }
                    >
                      {remediationSubmitting ? <span className="spinner small" /> : <CheckIcon />}
                      <span>{remediationSubmitting ? "Checking…" : "Check Answer"}</span>
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
                    <div className="quiz-options-list">
                      {question.options.map((option, index) => {
                        const isSelected = selected === index;
                        const isCorrect = showResult && expectedOption === option;
                        const isWrong = showResult && isSelected && !isCorrect;
                        return (
                          <button
                            key={`${question.id}-${index}`}
                            type="button"
                            className={`quiz-option-btn ${isSelected ? "selected" : ""} ${
                              isCorrect ? "correct" : ""
                            } ${isWrong ? "wrong" : ""}`}
                            onClick={() => setSelected(index)}
                            disabled={showResult || answering}
                          >
                            <span className="quiz-option-letter">{LETTERS[index] ?? index + 1}</span>
                            <span style={{ flex: 1 }}>{option}</span>
                            {isCorrect ? <CheckIcon style={{ color: "var(--success-text)" }} /> : null}
                            {isWrong ? <WarningIcon style={{ color: "var(--danger-text)" }} /> : null}
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

                      {/* Built-in Concept Explanation Card */}
                      <div className="concept-explanation-card">
                        <div className="concept-explanation-header">
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <BookIcon />
                            <span className="concept-card-title">Concept Explanation</span>
                          </div>
                          <span className="badge">NCERT Grounded</span>
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

                  <div className="quiz-actions" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 20 }}>
                    {showResult ? (
                      feedback?.completed ? (
                        <button type="button" className="btn btn-primary" onClick={endQuiz}>
                          <CheckCircleIcon />
                          <span>New Quiz</span>
                        </button>
                      ) : (
                        <button type="button" className="btn btn-primary" onClick={next}>
                          <span>Next Question</span>
                          <ArrowRightIcon />
                        </button>
                      )
                    ) : (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => void submit()}
                        disabled={
                          answering ||
                          (question.kind === "mcq"
                            ? selected === null
                            : shortAnswer.trim().length === 0)
                        }
                      >
                        {answering ? <span className="spinner small" /> : <CheckIcon />}
                        <span>{answering ? "Checking…" : "Check Answer"}</span>
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
                      <p className="panel-kicker">Session Complete</p>
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
                  <div className="quiz-summary-actions" style={{ display: "flex", gap: 10, marginTop: 16 }}>
                    <button type="button" className="btn btn-primary" onClick={() => void start()}>
                      <PlayIcon />
                      <span>Practise Again</span>
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={endQuiz}>
                      Change Settings
                    </button>
                  </div>
                </div>
              ) : null}
            </div>

            <aside className="quiz-side">
              <div className="quiz-side-card">
                <div className="quiz-side-head">
                  <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Mastery by Topic</span>
                  <span className="badge">{trimmedStudent}</span>
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
                  <div className="nlm-head-title-wrap" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <BarChartIcon />
                    <span className="nlm-head-title" style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                      Weakest Topics &amp; ML Gaps
                    </span>
                  </div>
                  <span className="badge">{gaps?.attempts ?? 0} attempts</span>
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
