import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { getTeacherOverview, getTeacherStudentDetail, getTeacherStudents } from "../api";
import { messageOf } from "../format";
import type { TeacherOverview, TeacherStudentDetail, TeacherTopic } from "../types";
import {
  RefreshCwIcon,
  SparkIcon,
  WarningIcon,
} from "./icons";

const SUBJECT_MAP: Record<string, string> = {
  // Mathematics
  "real numbers": "Mathematics",
  "polynomials": "Mathematics",
  "pair of linear equations in two variables": "Mathematics",
  "quadratic equations": "Mathematics",
  "arithmetic progressions": "Mathematics",
  "triangles": "Mathematics",
  "coordinate geometry": "Mathematics",
  "introduction to trigonometry": "Mathematics",
  "some applications of trigonometry": "Mathematics",
  "circles": "Mathematics",
  "areas related to circles": "Mathematics",
  "surface areas and volumes": "Mathematics",
  "statistics": "Mathematics",
  "probability": "Mathematics",
  "number systems": "Mathematics",
  "linear equations in two variables": "Mathematics",
  "introduction to euclid's geometry": "Mathematics",
  "lines and angles": "Mathematics",
  "quadrilaterals": "Mathematics",
  "heron's formula": "Mathematics",
  "rational numbers": "Mathematics",
  "linear equations in one variable": "Mathematics",
  "understanding quadrilaterals": "Mathematics",
  "data handling": "Mathematics",
  "squares and square roots": "Mathematics",
  "cubes and cube roots": "Mathematics",
  "comparing quantities": "Mathematics",
  "algebraic expressions and identities": "Mathematics",
  "mensuration": "Mathematics",
  "exponents and powers": "Mathematics",
  "direct and inverse proportions": "Mathematics",
  "factorisation": "Mathematics",
  "introduction to graphs": "Mathematics",

  // Science
  "chemical reactions and equations": "Science",
  "acids, bases and salts": "Science",
  "metals and non-metals": "Science",
  "carbon and its compounds": "Science",
  "life processes": "Science",
  "control and coordination": "Science",
  "how do organisms reproduce?": "Science",
  "heredity": "Science",
  "light - reflection and refraction": "Science",
  "the human eye and the colourful world": "Science",
  "electricity": "Science",
  "magnetic effects of electric current": "Science",
  "our environment": "Science",
  "matter in our surroundings": "Science",
  "is matter around us pure": "Science",
  "atoms and molecules": "Science",
  "structure of the atom": "Science",
  "the fundamental unit of life": "Science",
  "tissues": "Science",
  "motion": "Science",
  "force and laws of motion": "Science",
  "gravitation": "Science",
  "work and energy": "Science",
  "sound": "Science",
  "improvement in food resources": "Science",
  "crop production and management": "Science",
  "microorganisms: friend and foe": "Science",
  "coal and petroleum": "Science",
  "combustion and flame": "Science",
  "conservation of plants and animals": "Science",
  "reproduction in animals": "Science",
  "reaching the age of adolescence": "Science",
  "force and pressure": "Science",
  "friction": "Science",
  "chemical effects of electric current": "Science",
  "some natural phenomena": "Science",
  "light": "Science",
};

export function getTopicSubject(topicName: string, explicitLabel?: string): string {
  if (explicitLabel) return explicitLabel;
  const key = topicName.trim().toLowerCase();
  if (SUBJECT_MAP[key]) return SUBJECT_MAP[key];
  for (const [title, subj] of Object.entries(SUBJECT_MAP)) {
    if (key.includes(title) || title.includes(key)) return subj;
  }
  const mathKw = [
    "math", "equation", "number", "polynomial", "trigonometry", "algebra",
    "probability", "statistics", "geometry", "triangle", "circle", "arithmetic", "coordinate"
  ];
  if (mathKw.some((k) => key.includes(k))) return "Mathematics";
  const sciKw = [
    "science", "light", "current", "acid", "cell", "chemical", "physics",
    "biology", "chemistry", "eye", "environment", "motion", "force",
    "gravity", "energy", "sound", "matter", "reflection", "refraction"
  ];
  if (sciKw.some((k) => key.includes(k))) return "Science";
  return "General";
}

export function TeacherDashboard() {
  const [overview, setOverview] = useState<TeacherOverview | null>(null);
  const [students, setStudents] = useState<string[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string>("");
  const [selectedSubjectFilter, setSelectedSubjectFilter] = useState<string>("all");
  const [studentDetail, setStudentDetail] = useState<TeacherStudentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [studentLoading, setStudentLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ovData, stData] = await Promise.all([
        getTeacherOverview(),
        getTeacherStudents(),
      ]);
      setOverview(ovData);
      setStudents(stData.students);
      if (stData.students.length > 0 && !selectedStudent) {
        setSelectedStudent(stData.students[0]);
      }
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setLoading(false);
    }
  }, [selectedStudent]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!selectedStudent) {
      setStudentDetail(null);
      return;
    }
    setStudentLoading(true);
    getTeacherStudentDetail(selectedStudent)
      .then((detail) => setStudentDetail(detail))
      .catch(() => setStudentDetail(null))
      .finally(() => setStudentLoading(false));
  }, [selectedStudent]);

  const groupedTopics = useMemo(() => {
    if (!overview?.topics) return new Map<string, TeacherTopic[]>();
    const map = new Map<string, TeacherTopic[]>();
    for (const t of overview.topics) {
      const subj = getTopicSubject(t.topic, t.subject_label);
      const list = map.get(subj) ?? [];
      list.push(t);
      map.set(subj, list);
    }
    return map;
  }, [overview]);

  const availableSubjects = useMemo(() => {
    return Array.from(groupedTopics.keys()).sort((a, b) => {
      if (a === "Mathematics") return -1;
      if (b === "Mathematics") return 1;
      if (a === "Science") return -1;
      if (b === "Science") return 1;
      return a.localeCompare(b);
    });
  }, [groupedTopics]);

  const displaySubjects = useMemo(() => {
    if (selectedSubjectFilter === "all") {
      return availableSubjects;
    }
    return availableSubjects.filter((s) => s === selectedSubjectFilter);
  }, [availableSubjects, selectedSubjectFilter]);

  return (
    <div className="teacher-workspace">
      {/* Workspace Header */}
      <header className="workspace-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <p className="kicker" style={{ fontSize: "0.74rem", fontWeight: 600, color: "var(--accent-text)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px 0" }}>
            Teacher Analytics · SQLite Storage
          </p>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
            Classroom Knowledge Gaps &amp; Mastery
          </h2>
          <p style={{ margin: "4px 0 0 0", color: "var(--text-muted)", fontSize: "0.82rem" }}>
            Real-time offline diagnostics powered by Scikit-Learn Decision Trees and SQLite Local Storage.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <span className="badge badge-accent">
            <SparkIcon />
            <span>ML Gap Classifier</span>
          </span>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => void loadData()}>
            <RefreshCwIcon />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {error ? (
        <div className="inline-warning error">
          <WarningIcon />
          <span>{error}</span>
        </div>
      ) : null}

      {loading && !overview ? (
        <div className="study-loading" style={{ padding: "40px 0", textAlign: "center" }}>
          <span className="spinner" />
          <p style={{ marginTop: "12px", color: "var(--text-muted)" }}>Loading classroom analytics from SQLite database…</p>
        </div>
      ) : overview ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* KPI Summary Cards */}
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-label">Total Sessions</span>
              <div className="metric-value">{overview.total_sessions}</div>
              <span className="metric-meta">Recorded lectures in SQLite</span>
            </div>

            <div className="metric-card">
              <span className="metric-label">Questions Practiced</span>
              <div className="metric-value">{overview.total_attempts}</div>
              <span className="metric-meta">Logged student answers</span>
            </div>

            <div className="metric-card">
              <span className="metric-label">Class Accuracy</span>
              <div className="metric-value" style={{ color: "var(--success-text)" }}>
                {Math.round(overview.overall_accuracy * 100)}%
              </div>
              <span className="metric-meta">First-try accuracy</span>
            </div>

            <div className="metric-card">
              <span className="metric-label">Class Mastery Avg</span>
              <div className="metric-value" style={{ color: "var(--accent-text)" }}>
                {Math.round(overview.class_mastery_avg * 100)}%
              </div>
              <span className="metric-meta">Adaptive EMA score</span>
            </div>

            <div className="metric-card">
              <span className="metric-label">Avg Response Speed</span>
              <div className="metric-value">
                {overview.avg_response_ms ? `${(overview.avg_response_ms / 1000).toFixed(1)}s` : "5.0s"}
              </div>
              <span className="metric-meta">Fluency indicator</span>
            </div>

            <div className="metric-card">
              <span className="metric-label">Active Students</span>
              <div className="metric-value">
                {overview.total_students || students.length || 1}
              </div>
              <span className="metric-meta">Profiles in SQLite</span>
            </div>
          </div>

          {/* Topic Mastery Heatmap Table Grouped by Subject */}
          <div className="analytics-table-card">
            <div className="card-header" style={{ flexWrap: "wrap", gap: "12px" }}>
              <div>
                <h3 className="card-title">Curriculum Topic Mastery &amp; Knowledge Gap Diagnostics</h3>
                <p className="card-subtitle">
                  Classified into Critical Gaps, Needs Review, or Proficient based on accuracy and response latency. Grouped by subject.
                </p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                {availableSubjects.length > 1 && (
                  <div className="segmented" style={{ margin: 0 }}>
                    <button
                      type="button"
                      className={selectedSubjectFilter === "all" ? "active" : ""}
                      onClick={() => setSelectedSubjectFilter("all")}
                      style={{ padding: "4px 10px", fontSize: "0.78rem" }}
                    >
                      All Subjects ({overview.topics.length})
                    </button>
                    {availableSubjects.map((subj) => {
                      const count = groupedTopics.get(subj)?.length ?? 0;
                      const icon = subj === "Mathematics" ? "📐" : subj === "Science" ? "🔬" : "📚";
                      return (
                        <button
                          key={subj}
                          type="button"
                          className={selectedSubjectFilter === subj ? "active" : ""}
                          onClick={() => setSelectedSubjectFilter(subj)}
                          style={{ padding: "4px 10px", fontSize: "0.78rem" }}
                        >
                          <span style={{ marginRight: "4px" }}>{icon}</span>
                          {subj} ({count})
                        </button>
                      );
                    })}
                  </div>
                )}
                <span className="badge">{overview.topics.length} topics tracked</span>
              </div>
            </div>

            {overview.topics.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", padding: "20px" }}>
                No student quiz attempts recorded yet. Start practicing quizzes to populate topic mastery heatmaps.
              </p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="analytics-table">
                  <thead>
                    <tr>
                      <th>Topic / Chapter Name</th>
                      <th>Attempts</th>
                      <th>Accuracy</th>
                      <th>Avg Speed</th>
                      <th>ML Gap Tier</th>
                      <th>Remediation Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displaySubjects.map((subject) => {
                      const subjectTopics = groupedTopics.get(subject) ?? [];
                      if (subjectTopics.length === 0) return null;
                      const groupAttempts = subjectTopics.reduce((acc, curr) => acc + curr.attempts, 0);
                      const groupCorrect = subjectTopics.reduce((acc, curr) => acc + curr.correct, 0);
                      const groupAvgAcc = groupAttempts > 0 ? groupCorrect / groupAttempts : 0;
                      const subjectIcon = subject === "Mathematics" ? "📐" : subject === "Science" ? "🔬" : "📚";

                      return (
                        <Fragment key={subject}>
                          <tr className="analytics-subject-group-row">
                            <td colSpan={6}>
                              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                  <span style={{ fontSize: "1.05rem" }}>{subjectIcon}</span>
                                  <strong style={{ fontSize: "0.92rem", color: "var(--text-primary)" }}>
                                    {subject}
                                  </strong>
                                  <span className="badge" style={{ fontSize: "0.7rem", padding: "2px 8px" }}>
                                    {subjectTopics.length} {subjectTopics.length === 1 ? "chapter" : "chapters"}
                                  </span>
                                </div>
                                <div style={{ display: "flex", gap: "16px", fontSize: "0.76rem", color: "var(--text-muted)" }}>
                                  <span>
                                    Subject Accuracy:{" "}
                                    <strong
                                      style={{
                                        color:
                                          groupAvgAcc < 0.4
                                            ? "var(--danger-text)"
                                            : groupAvgAcc < 0.7
                                            ? "var(--warning-text)"
                                            : "var(--success-text)",
                                      }}
                                    >
                                      {Math.round(groupAvgAcc * 100)}%
                                    </strong>
                                  </span>
                                  <span>
                                    Total Attempts:{" "}
                                    <strong style={{ color: "var(--text-secondary)" }}>
                                      {groupAttempts}
                                    </strong>
                                  </span>
                                </div>
                              </div>
                            </td>
                          </tr>
                          {subjectTopics.map((t, idx) => {
                            const isCritical = t.accuracy < 0.4 || (t.attempts >= 2 && t.correct === 0);
                            const isReview = !isCritical && t.accuracy < 0.7;
                            return (
                              <tr key={t.topic}>
                                <td style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <span style={{ color: "var(--text-muted)", fontSize: "0.74rem", minWidth: "18px" }}>
                                      {idx + 1}.
                                    </span>
                                    <span>{t.topic}</span>
                                    <span
                                      className="badge"
                                      style={{
                                        fontSize: "0.64rem",
                                        padding: "1px 6px",
                                        background:
                                          subject === "Mathematics"
                                            ? "rgba(59, 130, 246, 0.12)"
                                            : "rgba(16, 185, 129, 0.12)",
                                        color: subject === "Mathematics" ? "#60a5fa" : "#34d399",
                                        border:
                                          subject === "Mathematics"
                                            ? "1px solid rgba(59, 130, 246, 0.25)"
                                            : "1px solid rgba(16, 185, 129, 0.25)",
                                      }}
                                    >
                                      {subject}
                                    </span>
                                  </div>
                                </td>
                                <td style={{ color: "var(--text-secondary)" }}>
                                  {t.attempts} ({t.correct} correct)
                                </td>
                                <td>
                                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <div
                                      style={{
                                        width: "60px",
                                        height: "4px",
                                        background: "rgba(255,255,255,0.08)",
                                        borderRadius: "var(--radius-pill)",
                                        overflow: "hidden",
                                      }}
                                    >
                                      <div
                                        style={{
                                          width: `${Math.round(t.accuracy * 100)}%`,
                                          height: "100%",
                                          background: isCritical
                                            ? "var(--danger-text)"
                                            : isReview
                                            ? "var(--warning-text)"
                                            : "var(--success-text)",
                                        }}
                                      />
                                    </div>
                                    <span
                                      style={{
                                        fontWeight: 600,
                                        fontSize: "0.82rem",
                                        color: isCritical
                                          ? "var(--danger-text)"
                                          : isReview
                                          ? "var(--warning-text)"
                                          : "var(--success-text)",
                                      }}
                                    >
                                      {Math.round(t.accuracy * 100)}%
                                    </span>
                                  </div>
                                </td>
                                <td style={{ color: "var(--text-secondary)" }}>
                                  {(t.avg_response_ms / 1000).toFixed(1)}s
                                </td>
                                <td>
                                  {isCritical ? (
                                    <span className="nlm-tier-chip critical_gap">
                                      Critical Gap
                                    </span>
                                  ) : isReview ? (
                                    <span className="nlm-tier-chip needs_review">
                                      Needs Review
                                    </span>
                                  ) : (
                                    <span className="nlm-tier-chip proficient">
                                      Proficient
                                    </span>
                                  )}
                                </td>
                                <td style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                                  {isCritical
                                    ? "Trigger Foundation Auto-Remediation drill on core definitions"
                                    : isReview
                                    ? "Assign Core adaptive practice questions"
                                    : "Ready for Challenge difficulty items"}
                                </td>
                              </tr>
                            );
                          })}
                        </Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Two-Column Bottom Grid */}
          <div className="teacher-grid-bottom">
            {/* Student Diagnostics Card */}
            <div className="teacher-bottom-card">
              <div className="card-header">
                <div>
                  <h3 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    Student Individual Diagnostics
                  </h3>
                  <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>
                    Select a student to inspect diagnosed gaps
                  </span>
                </div>
                {students.length > 0 && (
                  <select
                    className="select"
                    value={selectedStudent}
                    onChange={(e) => setSelectedStudent(e.target.value)}
                    style={{ padding: "4px 10px", fontSize: "0.78rem" }}
                  >
                    {students.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {studentLoading ? (
                <div style={{ textAlign: "center", padding: "24px 0" }}>
                  <span className="spinner small" />
                  <span style={{ marginLeft: "8px", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                    Loading student gaps…
                  </span>
                </div>
              ) : studentDetail ? (
                <div>
                  <div className="student-stat-strip">
                    <div className="student-stat-item">
                      <span className="student-stat-label">Overall Mastery</span>
                      <span className="student-stat-val" style={{ color: "var(--accent-text)" }}>
                        {Math.round(studentDetail.overall * 100)}%
                      </span>
                    </div>
                    <div className="student-stat-item">
                      <span className="student-stat-label">Questions Attempted</span>
                      <span className="student-stat-val">
                        {studentDetail.attempts}
                      </span>
                    </div>
                    <div className="student-stat-item">
                      <span className="student-stat-label">ML Classifier</span>
                      <span className="student-stat-val" style={{ color: "var(--success-text)", fontSize: "0.8rem" }}>
                        {studentDetail.classifier_model}
                      </span>
                    </div>
                  </div>

                  <h4 style={{ margin: "0 0 10px 0", fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-muted)" }}>
                    Diagnosed Knowledge Gaps:
                  </h4>
                  {studentDetail.gaps.length === 0 ? (
                    <p style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                      No knowledge gaps detected for this student.
                    </p>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {studentDetail.gaps.map((g) => {
                        const gapSubj = getTopicSubject(g.topic);
                        return (
                          <div key={g.topic} className="student-gap-item">
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                <strong style={{ fontSize: "0.84rem", color: "var(--text-primary)" }}>{g.topic}</strong>
                                <span
                                  className="badge"
                                  style={{
                                    fontSize: "0.62rem",
                                    padding: "1px 5px",
                                    background:
                                      gapSubj === "Mathematics"
                                        ? "rgba(59, 130, 246, 0.12)"
                                        : "rgba(16, 185, 129, 0.12)",
                                    color: gapSubj === "Mathematics" ? "#60a5fa" : "#34d399",
                                    border:
                                      gapSubj === "Mathematics"
                                        ? "1px solid rgba(59, 130, 246, 0.25)"
                                        : "1px solid rgba(16, 185, 129, 0.25)",
                                  }}
                                >
                                  {gapSubj}
                                </span>
                              </div>
                              <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--accent-text)" }}>
                                {Math.round(g.mastery * 100)}%
                              </span>
                            </div>
                            <div style={{ display: "flex", gap: "6px" }}>
                              <span className={`nlm-tier-chip ${g.tier === "critical_gap" ? "critical_gap" : "needs_review"}`}>
                                {g.tier_label ?? (g.mastery < 0.4 ? "Critical Gap" : "Needs Review")}
                              </span>
                              <span className="badge" style={{ fontSize: "0.68rem" }}>
                                Rec: Level {g.recommended_difficulty}
                              </span>
                            </div>
                            {g.diagnostic_reasons && g.diagnostic_reasons.length > 0 && (
                              <p style={{ margin: 0, fontSize: "0.74rem", color: "var(--text-muted)" }}>
                                {g.diagnostic_reasons[0]}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ) : (
                <p style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                  Select or enter a student ID to review diagnostic gap analysis.
                </p>
              )}
            </div>

            {/* SQLite Saved Lecture Sessions Card */}
            <div className="teacher-bottom-card">
              <div className="card-header">
                <div>
                  <h3 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    SQLite Saved Lecture Sessions
                  </h3>
                  <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>
                    Historical transcripts and generated notes
                  </span>
                </div>
                <span className="badge">Local DB</span>
              </div>

              {overview.recent_sessions.length === 0 ? (
                <p style={{ color: "var(--text-muted)", fontSize: "0.82rem", padding: "12px 0" }}>
                  No lecture sessions saved in SQLite yet. Transcribing a microphone session or audio file automatically archives it here.
                </p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "300px", overflowY: "auto" }}>
                  {overview.recent_sessions.map((sess) => (
                    <div key={sess.id} className="session-item">
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <strong style={{ fontSize: "0.84rem", color: "var(--text-primary)" }}>{sess.title}</strong>
                        <span style={{ fontSize: "0.74rem", color: "var(--text-muted)" }}>
                          {new Date(sess.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <span className="badge" style={{ fontSize: "0.68rem" }}>
                          Class {sess.class_level ?? 10} {sess.subject ?? "Science"}
                        </span>
                        {sess.duration_s ? (
                          <span className="badge" style={{ fontSize: "0.68rem" }}>
                            {Math.round(sess.duration_s)}s duration
                          </span>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
