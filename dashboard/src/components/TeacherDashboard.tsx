import { useCallback, useEffect, useState } from "react";
import { getTeacherOverview, getTeacherStudentDetail, getTeacherStudents } from "../api";
import { messageOf } from "../format";
import type { TeacherOverview, TeacherStudentDetail } from "../types";
import { WarningIcon } from "./icons";

export function TeacherDashboard() {
  const [overview, setOverview] = useState<TeacherOverview | null>(null);
  const [students, setStudents] = useState<string[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<string>("");
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

  return (
    <section className="panel teacher-panel" style={{ flex: 1, padding: "20px 28px", overflowY: "auto" }}>
      <header
        className="panel-header"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "24px",
          borderBottom: "1px solid rgba(37, 99, 235, 0.25)",
          paddingBottom: "16px",
        }}
      >
        <div>
          <p className="panel-kicker" style={{ color: "#3b82f6", fontWeight: 700, letterSpacing: "0.08em" }}>
            Teacher Analytics &amp; Adaptive Learning Dashboard
          </p>
          <h2 style={{ fontSize: "1.75rem", margin: "4px 0", color: "#f8fafc" }}>
            Classroom Knowledge Gap &amp; Mastery Overview
          </h2>
          <p style={{ margin: "4px 0 0 0", color: "#94a3b8", fontSize: "0.88rem" }}>
            Real-time offline diagnostics powered by Scikit-Learn Decision Trees and SQLite Local Storage.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <span
            className="chip"
            style={{
              background: "rgba(37, 99, 235, 0.2)",
              border: "1px solid #2563eb",
              color: "#93c5fd",
              fontWeight: 600,
            }}
          >
            ⚡ ML Knowledge Gap Engine
          </span>
          <button type="button" className="btn ghost compact" onClick={() => void loadData()}>
            ↻ Refresh
          </button>
        </div>
      </header>

      {error ? (
        <div className="inline-warning error flush" style={{ marginBottom: "20px" }}>
          <WarningIcon />
          <span>{error}</span>
        </div>
      ) : null}

      {loading && !overview ? (
        <div className="study-loading" style={{ padding: "40px 0", textAlign: "center" }}>
          <span className="spinner" />
          <p style={{ marginTop: "12px", color: "#94a3b8" }}>Loading classroom analytics from SQLite database…</p>
        </div>
      ) : overview ? (
        <div>
          {/* KPI Summary Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "16px",
              marginBottom: "28px",
            }}
          >
            <div
              style={{
                background: "rgba(11, 19, 43, 0.8)",
                border: "1px solid rgba(37, 99, 235, 0.3)",
                borderRadius: "10px",
                padding: "16px 20px",
              }}
            >
              <span style={{ fontSize: "0.78rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 700 }}>
                Total Sessions
              </span>
              <h3 style={{ fontSize: "1.8rem", margin: "8px 0 4px 0", color: "#f8fafc" }}>
                {overview.total_sessions}
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#60a5fa" }}>Recorded lectures in SQLite</span>
            </div>

            <div
              style={{
                background: "rgba(11, 19, 43, 0.8)",
                border: "1px solid rgba(37, 99, 235, 0.3)",
                borderRadius: "10px",
                padding: "16px 20px",
              }}
            >
              <span style={{ fontSize: "0.78rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 700 }}>
                Questions Practiced
              </span>
              <h3 style={{ fontSize: "1.8rem", margin: "8px 0 4px 0", color: "#f8fafc" }}>
                {overview.total_attempts}
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#60a5fa" }}>Total student answers logged</span>
            </div>

            <div
              style={{
                background: "rgba(11, 19, 43, 0.8)",
                border: "1px solid rgba(37, 99, 235, 0.3)",
                borderRadius: "10px",
                padding: "16px 20px",
              }}
            >
              <span style={{ fontSize: "0.78rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 700 }}>
                Class Accuracy
              </span>
              <h3 style={{ fontSize: "1.8rem", margin: "8px 0 4px 0", color: "#34d399" }}>
                {Math.round(overview.overall_accuracy * 100)}%
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#6ee7b7" }}>First-try response accuracy</span>
            </div>

            <div
              style={{
                background: "rgba(11, 19, 43, 0.8)",
                border: "1px solid rgba(37, 99, 235, 0.3)",
                borderRadius: "10px",
                padding: "16px 20px",
              }}
            >
              <span style={{ fontSize: "0.78rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 700 }}>
                Class Mastery Avg
              </span>
              <h3 style={{ fontSize: "1.8rem", margin: "8px 0 4px 0", color: "#60a5fa" }}>
                {Math.round(overview.class_mastery_avg * 100)}%
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#93c5fd" }}>Adaptive EMA score</span>
            </div>

            <div
              style={{
                background: "rgba(11, 19, 43, 0.8)",
                border: "1px solid rgba(37, 99, 235, 0.3)",
                borderRadius: "10px",
                padding: "16px 20px",
              }}
            >
              <span style={{ fontSize: "0.78rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 700 }}>
                Avg Response Latency
              </span>
              <h3 style={{ fontSize: "1.8rem", margin: "8px 0 4px 0", color: "#f8fafc" }}>
                {overview.avg_response_ms ? `${(overview.avg_response_ms / 1000).toFixed(1)}s` : "5.0s"}
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Fluency indicator</span>
            </div>

            <div
              style={{
                background: "rgba(11, 19, 43, 0.8)",
                border: "1px solid rgba(37, 99, 235, 0.3)",
                borderRadius: "10px",
                padding: "16px 20px",
              }}
            >
              <span style={{ fontSize: "0.78rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: 700 }}>
                Active Students
              </span>
              <h3 style={{ fontSize: "1.8rem", margin: "8px 0 4px 0", color: "#f8fafc" }}>
                {overview.total_students || students.length || 1}
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#60a5fa" }}>Distinct student profiles</span>
            </div>
          </div>

          {/* Topic Mastery Heatmap Table */}
          <div
            style={{
              background: "rgba(11, 19, 43, 0.6)",
              border: "1px solid rgba(37, 99, 235, 0.25)",
              borderRadius: "12px",
              padding: "20px 24px",
              marginBottom: "28px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "1.15rem", color: "#f8fafc" }}>
                  Curriculum Topic Mastery &amp; Knowledge Gap Diagnostics
                </h3>
                <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                  Classified into Critical Gaps, Needs Review, or Proficient based on accuracy and response latency.
                </span>
              </div>
              <span className="chip" style={{ background: "rgba(37, 99, 235, 0.2)", color: "#93c5fd" }}>
                {overview.topics.length} topics tracked
              </span>
            </div>

            {overview.topics.length === 0 ? (
              <p style={{ color: "#94a3b8", fontSize: "0.88rem", padding: "12px 0" }}>
                No student quiz attempts recorded yet. Start practicing quizzes to populate topic mastery heatmaps.
              </p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", textAlign: "left" }}>
                      <th style={{ padding: "10px 14px", color: "#94a3b8", fontWeight: 600 }}>Topic Name</th>
                      <th style={{ padding: "10px 14px", color: "#94a3b8", fontWeight: 600 }}>Attempts</th>
                      <th style={{ padding: "10px 14px", color: "#94a3b8", fontWeight: 600 }}>Accuracy</th>
                      <th style={{ padding: "10px 14px", color: "#94a3b8", fontWeight: 600 }}>Avg Speed</th>
                      <th style={{ padding: "10px 14px", color: "#94a3b8", fontWeight: 600 }}>ML Gap Tier</th>
                      <th style={{ padding: "10px 14px", color: "#94a3b8", fontWeight: 600 }}>Remediation Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.topics.map((t) => {
                      const isCritical = t.accuracy < 0.4 || (t.attempts >= 2 && t.correct === 0);
                      const isReview = !isCritical && t.accuracy < 0.7;
                      return (
                        <tr
                          key={t.topic}
                          style={{
                            borderBottom: "1px solid rgba(255,255,255,0.06)",
                            background: isCritical
                              ? "rgba(239, 68, 68, 0.05)"
                              : isReview
                              ? "rgba(245, 158, 11, 0.05)"
                              : "transparent",
                          }}
                        >
                          <td style={{ padding: "12px 14px", fontWeight: 600, color: "#f1f5f9" }}>
                            {t.topic}
                          </td>
                          <td style={{ padding: "12px 14px", color: "#cbd5e1" }}>
                            {t.attempts} ({t.correct} correct)
                          </td>
                          <td style={{ padding: "12px 14px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <div
                                style={{
                                  width: "60px",
                                  height: "6px",
                                  background: "rgba(255,255,255,0.1)",
                                  borderRadius: "3px",
                                  overflow: "hidden",
                                }}
                              >
                                <div
                                  style={{
                                    width: `${Math.round(t.accuracy * 100)}%`,
                                    height: "100%",
                                    background: isCritical ? "#ef4444" : isReview ? "#f59e0b" : "#10b981",
                                  }}
                                />
                              </div>
                              <span style={{ fontWeight: 600, color: isCritical ? "#fca5a5" : isReview ? "#fcd34d" : "#6ee7b7" }}>
                                {Math.round(t.accuracy * 100)}%
                              </span>
                            </div>
                          </td>
                          <td style={{ padding: "12px 14px", color: "#cbd5e1" }}>
                            {(t.avg_response_ms / 1000).toFixed(1)}s
                          </td>
                          <td style={{ padding: "12px 14px" }}>
                            {isCritical ? (
                              <span
                                className="chip"
                                style={{
                                  background: "rgba(239, 68, 68, 0.2)",
                                  color: "#fca5a5",
                                  border: "1px solid #ef4444",
                                  fontSize: "0.72rem",
                                }}
                              >
                                Critical Gap
                              </span>
                            ) : isReview ? (
                              <span
                                className="chip"
                                style={{
                                  background: "rgba(245, 158, 11, 0.2)",
                                  color: "#fcd34d",
                                  border: "1px solid #f59e0b",
                                  fontSize: "0.72rem",
                                }}
                              >
                                Needs Review
                              </span>
                            ) : (
                              <span
                                className="chip"
                                style={{
                                  background: "rgba(16, 185, 129, 0.2)",
                                  color: "#6ee7b7",
                                  border: "1px solid rgba(16, 185, 129, 0.4)",
                                  fontSize: "0.72rem",
                                }}
                              >
                                Proficient
                              </span>
                            )}
                          </td>
                          <td style={{ padding: "12px 14px", color: "#94a3b8", fontSize: "0.82rem" }}>
                            {isCritical
                              ? "Trigger Foundation Auto-Remediation drill on core definitions"
                              : isReview
                              ? "Assign Core adaptive practice questions"
                              : "Ready for Challenge difficulty items"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Two-Column Section: Student Diagnostics & SQLite Saved Sessions */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
            {/* Student Diagnostics Card */}
            <div
              style={{
                background: "rgba(11, 19, 43, 0.6)",
                border: "1px solid rgba(37, 99, 235, 0.25)",
                borderRadius: "12px",
                padding: "20px 24px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#f8fafc" }}>
                    Student Individual Diagnostics
                  </h3>
                  <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    Select a student to inspect diagnosed gaps
                  </span>
                </div>
                {students.length > 0 && (
                  <select
                    className="select"
                    value={selectedStudent}
                    onChange={(e) => setSelectedStudent(e.target.value)}
                    style={{ padding: "6px 12px", fontSize: "0.82rem" }}
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
                <div style={{ textAlign: "center", padding: "20px 0" }}>
                  <span className="spinner small" />
                  <span style={{ marginLeft: "8px", color: "#94a3b8", fontSize: "0.82rem" }}>
                    Loading student gaps…
                  </span>
                </div>
              ) : studentDetail ? (
                <div>
                  <div
                    style={{
                      display: "flex",
                      gap: "12px",
                      marginBottom: "14px",
                      background: "rgba(15, 23, 42, 0.5)",
                      padding: "10px 14px",
                      borderRadius: "8px",
                    }}
                  >
                    <div>
                      <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>Overall Mastery</span>
                      <p style={{ margin: 0, fontWeight: 700, color: "#60a5fa" }}>
                        {Math.round(studentDetail.overall * 100)}%
                      </p>
                    </div>
                    <div style={{ borderLeft: "1px solid rgba(255,255,255,0.1)", paddingLeft: "12px" }}>
                      <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>Questions Attempted</span>
                      <p style={{ margin: 0, fontWeight: 700, color: "#f8fafc" }}>
                        {studentDetail.attempts}
                      </p>
                    </div>
                    <div style={{ borderLeft: "1px solid rgba(255,255,255,0.1)", paddingLeft: "12px" }}>
                      <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>ML Model</span>
                      <p style={{ margin: 0, fontWeight: 600, color: "#34d399", fontSize: "0.85rem" }}>
                        {studentDetail.classifier_model}
                      </p>
                    </div>
                  </div>

                  <h4 style={{ margin: "0 0 8px 0", fontSize: "0.9rem", color: "#cbd5e1" }}>
                    Diagnosed Knowledge Gaps:
                  </h4>
                  {studentDetail.gaps.length === 0 ? (
                    <p style={{ fontSize: "0.82rem", color: "#94a3b8" }}>
                      No knowledge gaps detected for this student.
                    </p>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {studentDetail.gaps.map((g) => (
                        <div
                          key={g.topic}
                          style={{
                            background: "rgba(15, 23, 42, 0.7)",
                            padding: "10px 12px",
                            borderRadius: "6px",
                            border: "1px solid rgba(255,255,255,0.06)",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <strong style={{ fontSize: "0.88rem", color: "#f1f5f9" }}>{g.topic}</strong>
                            <span style={{ fontSize: "0.82rem", color: "#60a5fa" }}>
                              {Math.round(g.mastery * 100)}% mastery
                            </span>
                          </div>
                          <div style={{ display: "flex", gap: "6px", marginTop: "4px" }}>
                            <span
                              className="chip"
                              style={{
                                fontSize: "0.7rem",
                                background: g.tier === "critical_gap" ? "rgba(239, 68, 68, 0.2)" : "rgba(245, 158, 11, 0.2)",
                                color: g.tier === "critical_gap" ? "#fca5a5" : "#fcd34d",
                              }}
                            >
                              {g.tier_label ?? (g.mastery < 0.4 ? "Critical Gap" : "Needs Review")}
                            </span>
                            <span className="chip" style={{ fontSize: "0.7rem" }}>
                              Rec: Level {g.recommended_difficulty}
                            </span>
                          </div>
                          {g.diagnostic_reasons && g.diagnostic_reasons.length > 0 && (
                            <p style={{ margin: "4px 0 0 0", fontSize: "0.74rem", color: "#94a3b8" }}>
                              {g.diagnostic_reasons[0]}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
                  Select or enter a student ID to review diagnostic gap analysis.
                </p>
              )}
            </div>

            {/* SQLite Saved Lecture Sessions */}
            <div
              style={{
                background: "rgba(11, 19, 43, 0.6)",
                border: "1px solid rgba(37, 99, 235, 0.25)",
                borderRadius: "12px",
                padding: "20px 24px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#f8fafc" }}>
                    SQLite Saved Lecture Sessions
                  </h3>
                  <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    Historical transcripts and generated notes
                  </span>
                </div>
                <span className="chip" style={{ fontSize: "0.72rem" }}>
                  Local DB
                </span>
              </div>

              {overview.recent_sessions.length === 0 ? (
                <p style={{ color: "#94a3b8", fontSize: "0.85rem", padding: "12px 0" }}>
                  No lecture sessions saved in SQLite yet. Transcribing a microphone session or audio file automatically archives it here.
                </p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "320px", overflowY: "auto" }}>
                  {overview.recent_sessions.map((sess) => (
                    <div
                      key={sess.id}
                      style={{
                        background: "rgba(15, 23, 42, 0.7)",
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "1px solid rgba(255,255,255,0.06)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <strong style={{ fontSize: "0.88rem", color: "#f1f5f9" }}>{sess.title}</strong>
                        <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                          {new Date(sess.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                        <span className="chip" style={{ fontSize: "0.7rem" }}>
                          Class {sess.class_level ?? 10} {sess.subject ?? "Science"}
                        </span>
                        {sess.duration_s ? (
                          <span className="chip" style={{ fontSize: "0.7rem" }}>
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
    </section>
  );
}
