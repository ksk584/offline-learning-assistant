import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getNcertUnitNote, getStoredLectureNotes } from "../api";
import type { NcertNoteDetail, NcertPage, NotesResult, StoredLectureNotesResponse } from "../types";
import {
  BookIcon,
  CheckIcon,
  CopyIcon,
  DownloadIcon,
  FileTextIcon,
  MaximizeIcon,
  MicIcon,
  MinimizeIcon,
  PlayIcon,
  SparkIcon,
  WarningIcon,
} from "./icons";

interface NotesPaneProps {
  notes: NotesResult | null;
  markdown: string;
  loading: boolean;
  error: string | null;
  hasLines: boolean;
  finalsCount?: number;
  onGenerate: () => void;
  onSelectNcertUnit?: (unit: number) => void;
  activeNcertUnit?: number | null;
  onStartMic?: () => void;
  onPlayDemo?: () => void;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  mappedTopic?: string | null;
  chapterNumber?: number | null;
  classLevel?: number;
  subject?: string;
}

const UNITS = [
  {
    id: 1,
    title: "Unit 1: Real Numbers",
    sub: "NCERT Class 10 · Chapter 1 · jemh101.pdf · 10 Pages",
    topics: "Fundamental Theorem of Arithmetic, HCF & LCM, Proofs of Irrationality",
  },
  {
    id: 2,
    title: "Unit 2: Polynomials",
    sub: "NCERT Class 10 · Chapter 2 · jemh102.pdf · 10 Pages",
    topics: "Geometrical Zeroes, Parabola Properties, Quadratic & Cubic Relationships",
  },
  {
    id: 3,
    title: "Unit 3: Pair of Linear Equations",
    sub: "NCERT Class 10 · Chapter 3 · jemh103.pdf · 10 Pages",
    topics: "Consistency Ratios (a1/a2 ≠ b1/b2), Elimination, Substitution",
  },
];

async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    document.body.removeChild(area);
  }
}

export function NotesPane({
  notes,
  markdown,
  loading: transcriptLoading,
  error: transcriptError,
  hasLines,
  finalsCount = 0,
  onGenerate,
  onSelectNcertUnit,
  activeNcertUnit = 1,
  onStartMic,
  onPlayDemo,
  isExpanded = false,
  onToggleExpand,
  mappedTopic = null,
  chapterNumber = null,
  classLevel = 10,
  subject = "maths",
}: NotesPaneProps) {
  const [selectedUnit, setSelectedUnit] = useState<number>(activeNcertUnit || 1);
  const [activeTab, setActiveTab] = useState<"textbook" | "transcript" | "both">("textbook");
  const [textbookData, setTextbookData] = useState<NcertNoteDetail | null>(null);
  const [textbookLoading, setTextbookLoading] = useState<boolean>(true);
  const [textbookError, setTextbookError] = useState<string | null>(null);
  const [storedLectureNote, setStoredLectureNote] = useState<StoredLectureNotesResponse | null>(null);
  const [selectedPage, setSelectedPage] = useState<"all" | number>("all");
  const [copied, setCopied] = useState<boolean>(false);

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeNcertUnit && activeNcertUnit !== selectedUnit) {
      setSelectedUnit(activeNcertUnit);
    }
  }, [activeNcertUnit]);

  // Load Textbook Notes for selected unit
  useEffect(() => {
    let active = true;
    setTextbookLoading(true);
    setTextbookError(null);
    setSelectedPage("all");

    getNcertUnitNote(selectedUnit)
      .then((data) => {
        if (active) {
          setTextbookData(data);
          setTextbookLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setTextbookError(err.message || "Failed to load NCERT textbook notes");
          setTextbookLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedUnit]);

  // Load Stored Lecture Notes from SQLite for selected unit
  useEffect(() => {
    let active = true;
    getStoredLectureNotes(selectedUnit, classLevel, subject)
      .then((res) => {
        if (active && res.found) {
          setStoredLectureNote(res);
        } else if (active) {
          setStoredLectureNote(null);
        }
      })
      .catch(() => {
        if (active) setStoredLectureNote(null);
      });

    return () => {
      active = false;
    };
  }, [selectedUnit, classLevel, subject, notes]);

  // KaTeX rendering hook
  useEffect(() => {
    if (!textbookLoading && typeof window !== "undefined") {
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
      }, 120);
      return () => clearTimeout(timer);
    }
  }, [textbookLoading, textbookData, selectedPage, activeTab, markdown, storedLectureNote]);

  const handleUnitClick = (unitId: number) => {
    setSelectedUnit(unitId);
  };

  const currentMarkdown =
    markdown ||
    (storedLectureNote?.found && storedLectureNote.markdown ? storedLectureNote.markdown : "");

  const handleCopyCurrent = async () => {
    const textToCopy =
      activeTab === "transcript"
        ? currentMarkdown
        : activeTab === "textbook"
          ? textbookData?.markdown || ""
          : `--- LECTURE TRANSCRIPT NOTES ---\n\n${currentMarkdown}\n\n--- TEXTBOOK MASTER NOTES ---\n\n${textbookData?.markdown || ""}`;
    if (!textToCopy) return;
    await copyText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  const handleDownloadCurrent = () => {
    const isTranscript = activeTab === "transcript";
    const textToDownload = isTranscript
      ? currentMarkdown
      : activeTab === "textbook"
        ? textbookData?.markdown || ""
        : `# Unit ${selectedUnit} Combined Notes\n\n## Lecture Transcript Notes\n\n${currentMarkdown}\n\n## NCERT 10-Page Master Guide\n\n${textbookData?.markdown || ""}`;
    if (!textToDownload) return;
    const blob = new Blob([textToDownload], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = isTranscript
      ? `Lecture_Session_Notes.md`
      : `NCERT_Class10_Unit_${selectedUnit}_Master_Notes.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const pages = textbookData?.pages || [];

  return (
    <section className="panel notes-panel" ref={containerRef}>
      {/* Panel Top Header */}
      <header className="panel-header">
        <div className="panel-title-group">
          <span className="panel-kicker">Grounded NCERT Curriculum</span>
          <h2>Study Notes &amp; Guides</h2>
        </div>

        <div className="panel-actions">
          {onToggleExpand && (
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              onClick={onToggleExpand}
              title={isExpanded ? "Restore default 3-column view" : "Expand notes view to full width"}
            >
              {isExpanded ? <MinimizeIcon /> : <MaximizeIcon />}
              <span>{isExpanded ? "Collapse" : "Expand"}</span>
            </button>
          )}

          <button
            type="button"
            className="btn-icon"
            onClick={handleCopyCurrent}
            title="Copy Markdown to Clipboard"
            aria-label="Copy Markdown"
          >
            {copied ? <CheckIcon /> : <CopyIcon />}
          </button>

          <button
            type="button"
            className="btn-icon"
            onClick={handleDownloadCurrent}
            title="Download Notes Markdown"
            aria-label="Download Markdown"
          >
            <DownloadIcon />
          </button>

          <button
            type="button"
            className="btn-icon"
            onClick={() => window.print()}
            title="Print or Export to PDF"
            aria-label="Print"
          >
            🖨️
          </button>

          {hasLines && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={onGenerate}
              disabled={transcriptLoading}
              title="Convert live transcript into syllabus-grounded notes"
            >
              <SparkIcon />
              <span>{transcriptLoading ? "Writing…" : notes ? "Regenerate" : "Generate Notes"}</span>
            </button>
          )}
        </div>
      </header>

      {/* Sleek Compact Unit Selector */}
      <div className="notes-sub-header">
        <div className="unit-selector-chips">
          {UNITS.map((u) => (
            <button
              key={u.id}
              type="button"
              className={`unit-chip ${selectedUnit === u.id ? "active" : ""}`}
              onClick={() => handleUnitClick(u.id)}
              title={u.topics}
            >
              Unit {u.id}: {u.title.replace(/^Unit \d+:\s*/, "")}
            </button>
          ))}
        </div>

        {onSelectNcertUnit && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => onSelectNcertUnit(selectedUnit)}
            title="Open Dedicated Fullscreen 10-Page Reader View"
            style={{ fontSize: "0.74rem" }}
          >
            <FileTextIcon />
            <span>Full Reader View →</span>
          </button>
        )}
      </div>

      {/* Notes View Switcher (Textbook vs Transcript vs Both) */}
      <div className="notes-nav-tabs">
        <button
          type="button"
          className={`notes-tab-btn ${activeTab === "textbook" ? "active" : ""}`}
          onClick={() => setActiveTab("textbook")}
        >
          <BookIcon />
          <span>NCERT Master Guide (10 Pages)</span>
        </button>

        <button
          type="button"
          className={`notes-tab-btn ${activeTab === "transcript" ? "active" : ""}`}
          onClick={() => setActiveTab("transcript")}
        >
          <MicIcon />
          <span>Lecture Transcript Notes</span>
          {(notes || storedLectureNote?.found) && (
            <span className="badge badge-success" style={{ height: 18, fontSize: "0.68rem" }}>Saved</span>
          )}
        </button>

        <button
          type="button"
          className={`notes-tab-btn ${activeTab === "both" ? "active" : ""}`}
          onClick={() => setActiveTab("both")}
        >
          <span>Combined Notes</span>
        </button>
      </div>

      {/* Page Filter Bar (When Textbook Notes active) */}
      {(activeTab === "textbook" || activeTab === "both") && (
        <div className="page-filter-bar">
          <div className="page-chip-list">
            <span style={{ color: "var(--text-muted)", marginRight: 6 }}>Section Pages:</span>
            <button
              type="button"
              className={`page-chip-btn ${selectedPage === "all" ? "active" : ""}`}
              onClick={() => setSelectedPage("all")}
            >
              All 10 Pages
            </button>
            {pages.map((p) => (
              <button
                key={p.page_number}
                type="button"
                className={`page-chip-btn ${selectedPage === p.page_number ? "active" : ""}`}
                onClick={() => setSelectedPage(p.page_number)}
                title={`Section ${p.section_id}: ${p.title}`}
              >
                P{p.page_number}
              </button>
            ))}
          </div>

          <span style={{ color: "var(--text-muted)", fontSize: "0.72rem" }}>
            10-Page Local LLM Grounded NCERT Guide
          </span>
        </div>
      )}

      {/* Main Content Reading Viewport */}
      <div className="notes-content-viewport">
        {/* TAB 1: TEXTBOOK MASTER NOTES */}
        {(activeTab === "textbook" || activeTab === "both") && (
          <div>
            {textbookLoading ? (
              <div
                style={{
                  padding: 40,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 14,
                  color: "var(--text-secondary)",
                }}
              >
                <span className="spinner" />
                <span>Loading Unit {selectedUnit} Master Notes from local storage…</span>
              </div>
            ) : textbookError ? (
              <div className="inline-warning error">
                <WarningIcon />
                <span>{textbookError}</span>
              </div>
            ) : textbookData ? (
              <div>
                {(selectedPage === "all"
                  ? pages
                  : pages.filter((p) => p.page_number === selectedPage)
                ).map((page: NcertPage) => (
                  <article key={page.page_number} className="study-document-sheet">
                    <div className="sheet-header-meta">
                      <span>NCERT Class 10 Mathematics · Unit {selectedUnit}</span>
                      <span>Page {page.page_number} of {pages.length || 10}</span>
                    </div>

                    <div style={{ marginBottom: 16 }}>
                      <span className="badge badge-accent" style={{ marginBottom: 6 }}>
                        Section {page.section_id}
                      </span>
                      <h3 className="sheet-section-title">{page.title}</h3>
                    </div>

                    <div className="markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {page.content}
                      </ReactMarkdown>
                    </div>

                    <div
                      style={{
                        marginTop: 24,
                        paddingTop: 12,
                        borderTop: "1px solid var(--border-subtle)",
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: "0.72rem",
                        color: "var(--text-muted)",
                      }}
                    >
                      <span>Offline Intelligent Learning Assistant (ILA)</span>
                      <span>CBSE / NCERT Syllabus Grounded</span>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p style={{ textAlign: "center", color: "var(--text-muted)", padding: 40 }}>
                No textbook notes available for Unit {selectedUnit}.
              </p>
            )}
          </div>
        )}

        {/* TAB 2: LECTURE TRANSCRIPT NOTES */}
        {(activeTab === "transcript" || activeTab === "both") && (
          <div style={{ marginTop: activeTab === "both" ? 30 : 0 }}>
            {transcriptLoading ? (
              <div
                style={{
                  padding: 40,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 14,
                  color: "var(--text-secondary)",
                }}
              >
                <span className="spinner" />
                <span>Synthesizing notes and mapping to NCERT syllabus with local LLM…</span>
              </div>
            ) : transcriptError ? (
              <div className="inline-warning error" style={{ margin: "16px 0" }}>
                <WarningIcon />
                <div>
                  <strong style={{ display: "block", marginBottom: 4 }}>
                    Syllabus Correlation Error · Notes Dropped
                  </strong>
                  <p style={{ margin: 0, fontSize: "0.82rem", color: "#fecaca" }}>{transcriptError}</p>
                </div>
              </div>
            ) : notes && markdown ? (
              <article className="study-document-sheet">
                {mappedTopic && (
                  <div className="mapped-correlation-banner">
                    <div>
                      <span>Mapped NCERT Unit: </span>
                      <strong>Unit {chapterNumber ?? selectedUnit}: {mappedTopic}</strong>
                    </div>
                    <span className="badge badge-success">✓ Stored in SQLite</span>
                  </div>
                )}

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 16,
                    flexWrap: "wrap",
                  }}
                >
                  <span className={`badge ${notes.used_llm ? "badge-accent" : ""}`}>
                    {notes.used_llm ? `${notes.model ?? "local model"} · ${notes.profile}` : "Extractive TextRank"}
                  </span>
                  <span className="badge">{notes.latency_s.toFixed(1)}s</span>
                  <span className="badge">{notes.points.length} key points</span>
                  <span className="badge">{notes.sentences} sentences</span>
                </div>

                <div className="markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
                </div>
              </article>
            ) : storedLectureNote?.found && storedLectureNote.markdown ? (
              <article className="study-document-sheet">
                <div className="mapped-correlation-banner">
                  <div>
                    <span>Previous Session: </span>
                    <strong>Unit {storedLectureNote.chapter_number ?? selectedUnit}: {storedLectureNote.topic ?? storedLectureNote.title}</strong>
                  </div>
                  <span className="badge badge-success">Stored in SQLite</span>
                </div>

                <div className="markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{storedLectureNote.markdown}</ReactMarkdown>
                </div>
              </article>
            ) : hasLines ? (
              <div
                style={{
                  padding: "36px 24px",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-lg)",
                  textAlign: "center",
                  maxWidth: 500,
                  margin: "20px auto",
                }}
              >
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: "var(--radius-md)",
                    background: "var(--accent-subtle)",
                    color: "var(--accent-text)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 14px",
                  }}
                >
                  <SparkIcon />
                </div>
                <h3 style={{ fontSize: "1.05rem", marginBottom: 6, color: "var(--text-primary)" }}>
                  Transcript Ready for Synthesis
                </h3>
                <p style={{ fontSize: "0.84rem", color: "var(--text-secondary)", marginBottom: 18 }}>
                  {finalsCount > 0 ? `${finalsCount} speech utterances captured` : "Spoken lecture audio captured"}.
                  Synthesize into structured NCERT notes mapped to your syllabus.
                </p>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={onGenerate}
                  disabled={transcriptLoading}
                >
                  <SparkIcon />
                  <span>Synthesize Notes Now</span>
                </button>
              </div>
            ) : (
              <div
                style={{
                  padding: "40px 20px",
                  textAlign: "center",
                  color: "var(--text-muted)",
                }}
              >
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: "var(--radius-md)",
                    background: "var(--bg-surface-subtle)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 12px",
                    color: "var(--text-secondary)",
                  }}
                >
                  <MicIcon />
                </div>
                <h4 style={{ fontSize: "0.95rem", color: "var(--text-primary)", marginBottom: 4 }}>
                  No Spoken Lecture Recorded Yet
                </h4>
                <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", maxWidth: 360, margin: "0 auto 16px" }}>
                  Start your microphone or replay an official NCERT demo lecture to synthesize lecture notes.
                </p>
                <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={onStartMic}>
                    <MicIcon />
                    <span>Start Microphone</span>
                  </button>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={onPlayDemo}>
                    <PlayIcon />
                    <span>Play Demo</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
