import { useMemo, useState } from "react";
import type { AppConfig, DemoLecture, SyllabusContext } from "../types";
import { PlayIcon, SearchIcon, StopIcon } from "./icons";

interface CurriculumPanelProps {
  config: AppConfig | null;
  classLevel: number;
  subject: string;
  onSelect: (level: number, subject: string) => void;
  syllabus: SyllabusContext | null;
  demo: DemoLecture | null;
  demoPlaying: boolean;
  demoLoading: boolean;
  onPlayDemo: () => void;
  onStopDemo: () => void;
  onSelectNcertUnit?: (unit: number) => void;
  activeNcertUnit?: number | null;
}

export function CurriculumPanel({
  config,
  classLevel,
  subject,
  onSelect,
  syllabus,
  demo,
  demoPlaying,
  demoLoading,
  onPlayDemo,
  onStopDemo,
  onSelectNcertUnit,
  activeNcertUnit,
}: CurriculumPanelProps) {
  const [query, setQuery] = useState("");

  const course = useMemo(
    () =>
      config?.curriculum.courses.find(
        (item) => item.class_level === classLevel && item.subject === subject,
      ) ?? null,
    [config, classLevel, subject],
  );

  const matches = useMemo(
    () => new Map((syllabus?.matches ?? []).map((match) => [match.number, match])),
    [syllabus],
  );

  const chapters = useMemo(() => {
    if (!course) return [];
    const needle = query.trim().toLowerCase();
    if (!needle) return course.chapters;
    return course.chapters.filter(
      (chapter) =>
        chapter.title.toLowerCase().includes(needle) ||
        String(chapter.number) === needle,
    );
  }, [course, query]);

  const subjectLabels = config?.curriculum.subject_labels ?? {
    science: "Science",
    maths: "Mathematics",
  };

  return (
    <section className="panel curriculum-panel" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <header className="panel-header">
        <div className="panel-title-group">
          <span className="panel-kicker">Curriculum Alignment</span>
          <h2>NCERT Syllabus</h2>
        </div>
        <div className="panel-actions">
          <span className="badge">Class {classLevel}</span>
        </div>
      </header>

      <div className="curriculum-body">
        {/* Class Level Selector */}
        <div>
          <span className="field-label">Grade / Class</span>
          <div className="segmented" style={{ width: "100%", display: "flex" }}>
            {(config?.curriculum.class_levels ?? [8, 9, 10]).map((level) => (
              <button
                key={level}
                type="button"
                className={level === classLevel ? "active" : ""}
                onClick={() => onSelect(level, subject)}
                style={{ flex: 1 }}
              >
                Class {level}
              </button>
            ))}
          </div>
        </div>

        {/* Subject Selector */}
        <div>
          <span className="field-label">Subject</span>
          <div className="segmented" style={{ width: "100%", display: "flex" }}>
            {(config?.curriculum.subjects ?? ["science", "maths"]).map((name) => (
              <button
                key={name}
                type="button"
                className={name === subject ? "active" : ""}
                onClick={() => onSelect(classLevel, name)}
                style={{ flex: 1 }}
              >
                {subjectLabels[name] ?? name}
              </button>
            ))}
          </div>
        </div>

        {/* Built-in Demo Lecture Action */}
        <div
          style={{
            padding: "10px 12px",
            background: "var(--bg-surface-subtle)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 10,
          }}
        >
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {demo ? demo.title : `NCERT Class ${classLevel} Demo`}
            </div>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
              {course ? `${course.chapters.length} chapters loaded` : "Local curriculum"}
            </span>
          </div>

          <button
            type="button"
            className={`btn btn-sm ${demoPlaying ? "btn-danger" : "btn-secondary"}`}
            onClick={demoPlaying ? onStopDemo : onPlayDemo}
            disabled={demoLoading}
            title="Replay an official NCERT demo lecture"
          >
            {demoLoading ? (
              <span className="spinner small" />
            ) : demoPlaying ? (
              <StopIcon />
            ) : (
              <PlayIcon />
            )}
            <span>{demoLoading ? "Loading…" : demoPlaying ? "Stop" : "Play Demo"}</span>
          </button>
        </div>

        {/* Syllabus Correlation Matches (if available) */}
        {syllabus && syllabus.matches.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span className="field-label">Syllabus Match</span>
            {syllabus.matches.slice(0, 2).map((match) => (
              <div
                key={match.number}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "6px 10px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--accent-subtle)",
                  border: "1px solid var(--accent-border)",
                  fontSize: "0.76rem",
                }}
              >
                <span style={{ fontWeight: 600, color: "var(--accent-text)" }}>
                  Ch {match.number}: {match.title}
                </span>
                <span className="badge badge-accent" style={{ height: 18, fontSize: "0.68rem" }}>
                  {match.score.toFixed(1)} match
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Chapter Search Bar */}
        <div>
          <span className="field-label">Browse Syllabus Chapters</span>
          <div className="chapter-search-box">
            <SearchIcon />
            <input
              type="search"
              placeholder="Filter chapters by title or #…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Filter chapters"
            />
          </div>
        </div>

        {/* Scrollable Chapter List */}
        <div className="chapter-list-scroll">
          {chapters.map((ch) => {
            const hasMatch = matches.has(ch.number);
            const isNcertActive = activeNcertUnit === ch.number;
            return (
              <button
                key={ch.number}
                type="button"
                className={`chapter-item-btn ${isNcertActive ? "selected" : ""}`}
                onClick={() => onSelectNcertUnit?.(ch.number)}
                title={`NCERT Unit ${ch.number}: ${ch.title}`}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-muted)" }}>
                    {String(ch.number).padStart(2, "0")}
                  </span>
                  <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {ch.title}
                  </span>
                </div>
                {hasMatch && (
                  <span className="badge badge-accent" style={{ height: 16, fontSize: "0.65rem", padding: "0 4px" }}>
                    Matched
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
