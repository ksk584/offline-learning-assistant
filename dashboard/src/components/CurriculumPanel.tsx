import { useMemo, useState } from "react";
import type { AppConfig, DemoLecture, SyllabusContext } from "../types";
import { BookIcon, PlayIcon, SearchIcon, StopIcon } from "./icons";

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

  const demoChapter = useMemo(() => {
    const hit = demo?.chapter.match(/chapter\s+(\d{1,2})/i);
    return hit ? Number(hit[1]) : null;
  }, [demo]);

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
    <section className="panel curriculum-panel">
      <header className="panel-header">
        <div>
          <p className="panel-kicker">NCERT · India</p>
          <h2>Syllabus map</h2>
        </div>
        <div className="panel-actions">
          <span className="chip">
            <BookIcon />
            Class&nbsp;{classLevel}
          </span>
        </div>
      </header>

      <div className="curriculum-body">
        <div className="control-group">
          <span className="field-label">Class</span>
          <div className="segmented" role="group" aria-label="Class level">
            {(config?.curriculum.class_levels ?? [8, 9, 10]).map((level) => (
              <button
                key={level}
                type="button"
                className={level === classLevel ? "active" : ""}
                onClick={() => onSelect(level, subject)}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <span className="field-label">Subject</span>
          <div className="segmented" role="group" aria-label="Subject">
            {(config?.curriculum.subjects ?? ["science", "maths"]).map((name) => (
              <button
                key={name}
                type="button"
                className={name === subject ? "active" : ""}
                onClick={() => onSelect(classLevel, name)}
              >
                {subjectLabels[name] ?? name}
              </button>
            ))}
          </div>
        </div>

        <div className="course-summary">
          <div>
            <strong>{course?.label ?? "Loading course…"}</strong>
            <span>
              {course ? `${course.chapters.length} chapters` : "from /api/config"}
            </span>
          </div>
          <button
            type="button"
            className="btn ghost compact"
            onClick={demoPlaying ? onStopDemo : onPlayDemo}
            disabled={demoLoading}
            title="Replay a built-in NCERT lecture without a microphone"
          >
            {demoLoading ? (
              <span className="spinner small" />
            ) : demoPlaying ? (
              <StopIcon />
            ) : (
              <PlayIcon />
            )}
            {demoLoading ? "Loading" : demoPlaying ? "Stop demo" : "Play demo"}
          </button>
        </div>

        {syllabus && syllabus.matches.length > 0 ? (
          <div className="match-list">
            {syllabus.matches.map((match) => (
              <div className="match-card" key={match.number}>
                <span className="match-score">{match.score.toFixed(1)}</span>
                <div>
                  <strong>
                    Ch {match.number} · {match.title}
                  </strong>
                  {match.matched_terms.length ? (
                    <p className="match-terms">
                      {match.matched_terms.slice(0, 5).join(" · ")}
                    </p>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="hint">
            {syllabus
              ? "No confident chapter match yet. Generate notes from the transcript to align it."
              : "Generate notes to align this lecture to a chapter. Matching needs at least two supporting terms."}
          </p>
        )}

        <div className="chapter-search">
          <SearchIcon />
          <input
            type="search"
            placeholder="Find a chapter or number…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Search chapters"
          />
        </div>

        <ul className="chapter-list">
          {chapters.map((chapter) => {
            const match = matches.get(chapter.number);
            const isDemo = demoChapter === chapter.number;
            const hasNcertNotes =
              classLevel === 10 &&
              (subject === "maths" || subject === "mathematics") &&
              [1, 2, 3].includes(chapter.number);
            return (
              <li
                key={chapter.number}
                className={`chapter-item ${match ? "matched" : ""} ${
                  isDemo ? "current" : ""
                }`}
                title={chapter.title}
                style={{ display: "flex", alignItems: "center", gap: "6px" }}
              >
                <span className="chapter-number">{chapter.number}</span>
                <span className="chapter-title" style={{ flex: 1 }}>{chapter.title}</span>
                {isDemo && !match ? <span className="demo-badge">demo</span> : null}
                {match ? <span className="score-badge">{match.score.toFixed(1)}</span> : null}
                {hasNcertNotes ? (
                  <button
                    type="button"
                    className={`btn compact ${activeNcertUnit === chapter.number ? "primary" : "ghost"}`}
                    style={{
                      fontSize: "0.72rem",
                      padding: "2px 7px",
                      marginLeft: "auto",
                      whiteSpace: "nowrap",
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectNcertUnit?.(chapter.number);
                    }}
                    title={`View generated 10-page notes for Unit ${chapter.number}`}
                  >
                    📖 10-Pg Notes
                  </button>
                ) : null}
              </li>
            );
          })}
          {!chapters.length ? (
            <li className="chapter-item">
              <span className="chapter-title">No chapter matches that search.</span>
            </li>
          ) : null}
        </ul>

        <p className="panel-footnote">
          Chapter hints steer terminology only. The grounding verifier still checks every
          generated line against the transcript.
        </p>
      </div>
    </section>
  );
}
