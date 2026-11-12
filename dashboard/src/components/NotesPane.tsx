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
  MicIcon,
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
    topics: "Fundamental Theorem of Arithmetic, HCF & LCM, Proofs of Irrationality (√2, √3, √5)",
    wordCount: "3,720 words",
  },
  {
    id: 2,
    title: "Unit 2: Polynomials",
    sub: "NCERT Class 10 · Chapter 2 · jemh102.pdf · 10 Pages",
    topics: "Geometrical Zeroes, Parabola Properties, Quadratic & Cubic Zero-Coefficient Relationships",
    wordCount: "3,507 words",
  },
  {
    id: 3,
    title: "Unit 3: Pair of Linear Equations",
    sub: "NCERT Class 10 · Chapter 3 · jemh103.pdf · 10 Pages",
    topics: "Consistency Ratios (a1/a2 ≠ b1/b2), Elimination, Substitution, HOTS Word Problems",
    wordCount: "3,888 words",
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

  // Sync with prop when parent changes active unit
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
    onSelectNcertUnit?.(unitId);
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
  const currentUnitInfo = UNITS.find((u) => u.id === selectedUnit) || UNITS[0];

  return (
    <section className="panel notes-panel" ref={containerRef}>
      {/* Top Header */}
      <header className="panel-header">
        <div>
          <p className="panel-kicker">Grounded study material · NCERT Class 10</p>
          <h2>Study Notes &amp; Textbook Guides</h2>
        </div>
        <div className="panel-actions">
          {onToggleExpand && (
            <button
              type="button"
              className={`icon-btn expand-notes-btn ${isExpanded ? "active" : ""}`}
              onClick={onToggleExpand}
              title={isExpanded ? "Collapse notes panel (3-column view)" : "Expand notes panel (Full width study mode)"}
              aria-label={isExpanded ? "Collapse notes" : "Expand notes"}
            >
              <span className="expand-icon">{isExpanded ? "⤓" : "⛶"}</span>
              <span className="expand-text">{isExpanded ? "Collapse" : "Expand"}</span>
            </button>
          )}
          <button
            type="button"
            className="icon-btn"
            onClick={handleCopyCurrent}
            title="Copy Markdown"
            aria-label="Copy Markdown"
          >
            {copied ? <CheckIcon /> : <CopyIcon />}
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={handleDownloadCurrent}
            title="Download Markdown"
            aria-label="Download Markdown"
          >
            <DownloadIcon />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={() => window.print()}
            title="Print / Save PDF"
            aria-label="Print / Save PDF"
          >
            🖨️
          </button>
          {hasLines && (
            <button
              type="button"
              className="btn primary compact generate-notes-btn"
              onClick={onGenerate}
              disabled={transcriptLoading}
              title="Convert live transcript to grounded NCERT notes"
            >
              <SparkIcon />
              <span>{transcriptLoading ? "Writing…" : notes ? "Regenerate" : "Convert transcript"}</span>
            </button>
          )}
        </div>
      </header>

      {/* Clean Organized Unit List */}
      <div className="unit-list-container">
        <div className="unit-list-header">
          <span className="unit-list-title">NCERT Class 10 Units</span>
          <span className="unit-list-meta">10 Pages / Unit · Local LLM Grounded</span>
        </div>
        <div className="unit-clean-cards">
          {UNITS.map((u) => {
            const isSelected = selectedUnit === u.id;
            return (
              <button
                key={u.id}
                type="button"
                className={`unit-clean-card ${isSelected ? "selected" : ""}`}
                onClick={() => handleUnitClick(u.id)}
              >
                <div className="unit-clean-card-left">
                  <span className="unit-pill">Unit {u.id}</span>
                  <div className="unit-meta-texts">
                    <strong className="unit-card-heading">{u.title}</strong>
                    <span className="unit-card-sub">{u.topics}</span>
                  </div>
                </div>
                <div className="unit-clean-card-right">
                  <span className="unit-page-tag">10 Pages</span>
                  {isSelected && <span className="unit-active-glow" />}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Dual Tabs for Selected Unit: Textbook vs Transcript vs Both */}
      <div className="notes-dual-tabs">
        <button
          type="button"
          className={`dual-tab-pill ${activeTab === "textbook" ? "active" : ""}`}
          onClick={() => setActiveTab("textbook")}
        >
          <BookIcon />
          <span>📘 Textbook Master Notes (10 Pages)</span>
          <span className="tab-pill-badge ready">Ready</span>
        </button>
        <button
          type="button"
          className={`dual-tab-pill ${activeTab === "transcript" ? "active" : ""}`}
          onClick={() => setActiveTab("transcript")}
        >
          <MicIcon />
          <span>🎙️ Lecture Transcript Notes</span>
          {notes || storedLectureNote?.found ? (
            <span className="tab-pill-badge ready">Captured</span>
          ) : hasLines ? (
            <span className="tab-pill-badge ready">Ready</span>
          ) : (
            <span className="tab-pill-badge idle">Session</span>
          )}
        </button>
        <button
          type="button"
          className={`dual-tab-pill ${activeTab === "both" ? "active" : ""}`}
          onClick={() => setActiveTab("both")}
        >
          <span>📑 Both Notes</span>
        </button>
      </div>

      {/* Main Content Viewport */}
      <div className="notes-body-viewport">
        {/* ============================================================== */}
        {/* TAB 1: TEXTBOOK MASTER NOTES (10-Page Comprehensive Guide)      */}
        {/* ============================================================== */}
        {(activeTab === "textbook" || activeTab === "both") && (
          <div className="textbook-view-container">
            {activeTab === "both" && (
              <div className="both-section-divider">
                <BookIcon />
                <span>📘 NCERT 10-Page Textbook Master Notes — {currentUnitInfo.title}</span>
              </div>
            )}

            {/* Textbook Page Navigation Filter */}
            <div className="textbook-page-bar">
              <span className="page-bar-label">Page Filter:</span>
              <button
                type="button"
                className={`page-chip ${selectedPage === "all" ? "active" : ""}`}
                onClick={() => setSelectedPage("all")}
              >
                All 10 Pages
              </button>
              {pages.map((p) => (
                <button
                  key={p.page_number}
                  type="button"
                  className={`page-chip ${selectedPage === p.page_number ? "active" : ""}`}
                  onClick={() => setSelectedPage(p.page_number)}
                  title={`Section ${p.section_id}: ${p.title}`}
                >
                  Pg {p.page_number}
                </button>
              ))}
            </div>

            {textbookLoading ? (
              <div className="notes-loading-card">
                <span className="spinner" />
                <div>
                  <strong>Loading Unit {selectedUnit} Master Notes…</strong>
                  <p>Fetching on-device 10-page NCERT content generated with local LLM.</p>
                </div>
              </div>
            ) : textbookError ? (
              <div className="inline-warning error">
                <WarningIcon />
                <span>{textbookError}</span>
              </div>
            ) : textbookData ? (
              <div className="textbook-pages-display">
                {(selectedPage === "all"
                  ? pages
                  : pages.filter((p) => p.page_number === selectedPage)
                ).map((page: NcertPage) => (
                  <article key={page.page_number} className="textbook-doc-sheet">
                    <div className="sheet-running-header">
                      <span className="sheet-h-subject">NCERT Class 10 Mathematics</span>
                      <span className="sheet-h-title">
                        Unit {selectedUnit}: {currentUnitInfo.title}
                      </span>
                      <span className="sheet-h-page">
                        Page {page.page_number} of {pages.length || 10}
                      </span>
                    </div>

                    <div className="sheet-sec-badge">
                      <span className="sec-tag">Section {page.section_id}</span>
                      <h3 className="sec-title">{page.title}</h3>
                    </div>

                    <div className="sheet-markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {page.content}
                      </ReactMarkdown>
                    </div>

                    <div className="sheet-running-footer">
                      <span>Offline Intelligent Learning Assistant (ILA) · SDG 4</span>
                      <span className="sheet-page-indicator">
                        — Page {page.page_number} of {pages.length || 10} —
                      </span>
                      <span>CBSE / NCERT Standard</span>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <p>No textbook notes found for Unit {selectedUnit}.</p>
              </div>
            )}
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 2: LECTURE TRANSCRIPT NOTES                                */}
        {/* ============================================================== */}
        {(activeTab === "transcript" || activeTab === "both") && (
          <div className="transcript-view-container">
            {activeTab === "both" && (
              <div className="both-section-divider">
                <MicIcon />
                <span>🎙️ Lecture Transcript Grounded Notes (Current Session)</span>
              </div>
            )}

            {transcriptLoading ? (
              <div className="notes-loading-card">
                <span className="spinner" />
                <div>
                  <strong>Synthesizing lecture notes…</strong>
                  <p>
                    TextRank extracts core utterances, local LLM rewrites them, and the
                    syllabus correlation verifier grounds notes to NCERT topics.
                  </p>
                </div>
              </div>
            ) : transcriptError ? (
              <div className="transcript-correlation-error-card">
                <div className="error-card-header">
                  <WarningIcon />
                  <strong>Syllabus Correlation Error · Notes Dropped</strong>
                </div>
                <p className="error-card-message">{transcriptError}</p>
                <div className="error-card-help">
                  <span>💡 The lecture transcript was evaluated against NCERT syllabus topics. Off-topic talk or transcripts with insufficient correlation are rejected to protect grounded learning materials.</span>
                </div>
              </div>
            ) : notes && markdown ? (
              <div className="transcript-notes-content">
                {mappedTopic && (
                  <div className="mapped-topic-banner">
                    <div className="mapped-topic-info">
                      <span className="mapped-topic-pill">Unit {chapterNumber ?? selectedUnit}</span>
                      <div>
                        <strong>Mapped Syllabus Chapter: {mappedTopic}</strong>
                        <p>Verified against NCERT syllabus · Stored in SQLite database</p>
                      </div>
                    </div>
                    <span className="mapped-topic-badge">✓ Stored in SQLite</span>
                  </div>
                )}

                <div className="notes-meta">
                  <span className={`chip ${notes.used_llm ? "chip-accent" : "chip-muted"}`}>
                    {notes.used_llm ? <SparkIcon /> : null}
                    {notes.used_llm
                      ? `${notes.model ?? "local model"} · ${notes.profile}`
                      : "Extractive · TextRank"}
                  </span>
                  <span className="chip">{notes.latency_s.toFixed(1)} s</span>
                  <span className="chip">{notes.points.length} points</span>
                  <span className="chip">{notes.sentences} sentences</span>
                  {notes.dropped > 0 && (
                    <span className="chip chip-warn">
                      {notes.dropped} unsupported line{notes.dropped === 1 ? "" : "s"} dropped
                    </span>
                  )}
                </div>

                {!notes.used_llm && notes.fallback_reason && (
                  <div className="inline-warning">
                    <WarningIcon />
                    <span>
                      <strong>Extractive fallback.</strong> {notes.fallback_reason}
                    </span>
                  </div>
                )}

                <div className="markdown transcript-markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
                </div>
              </div>
            ) : storedLectureNote?.found && storedLectureNote.markdown ? (
              <div className="transcript-notes-content">
                <div className="mapped-topic-banner stored-history">
                  <div className="mapped-topic-info">
                    <span className="mapped-topic-pill">Unit {storedLectureNote.chapter_number ?? selectedUnit}</span>
                    <div>
                      <strong>Stored Lecture Notes: {storedLectureNote.topic ?? storedLectureNote.title}</strong>
                      <p>Retrieved from SQLite database ({storedLectureNote.created_at ? new Date(storedLectureNote.created_at).toLocaleDateString() : "Saved Lecture"})</p>
                    </div>
                  </div>
                  <span className="mapped-topic-badge stored">💾 Stored in SQLite</span>
                </div>

                <div className="markdown transcript-markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{storedLectureNote.markdown}</ReactMarkdown>
                </div>
              </div>
            ) : hasLines ? (
              <div className="transcript-convert-prompt-card">
                <div className="prompt-card-icon">
                  <SparkIcon />
                </div>
                <div className="prompt-card-body">
                  <h3>Live Lecture Transcript Ready for Conversion</h3>
                  <p>
                    {finalsCount > 0 ? `${finalsCount} speech utterances` : "Captured lecture utterances"} ready to synthesize into structured, syllabus-grounded notes mapped to NCERT units.
                  </p>
                  <button
                    type="button"
                    className="btn primary"
                    onClick={onGenerate}
                    disabled={transcriptLoading}
                  >
                    <SparkIcon />
                    {transcriptLoading ? "Writing Notes with Local LLM…" : "Convert Transcript to Notes"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="transcript-empty-card">
                <div className="empty-icon-wrap">
                  <MicIcon />
                </div>
                <h3>Live Lecture Notes for {currentUnitInfo.title}</h3>
                <p>
                  No spoken audio recorded yet for this session. The complete, rigorous
                  10-page NCERT Study Guide is available right now in the{" "}
                  <strong>Textbook Master Notes</strong> tab!
                </p>
                <p className="empty-subtext">
                  To capture and ground live lecture audio, start your microphone or replay
                  an official NCERT demo lecture.
                </p>
                <div className="empty-action-buttons">
                  <button
                    type="button"
                    className="btn primary"
                    onClick={onStartMic}
                    title="Start capturing microphone audio"
                  >
                    <MicIcon />
                    Start microphone
                  </button>
                  <button
                    type="button"
                    className="btn"
                    onClick={onPlayDemo}
                    title="Replay a built-in Class 10 NCERT lecture"
                  >
                    <PlayIcon />
                    Play Class 10 Demo
                  </button>
                  <button
                    type="button"
                    className="btn ghost"
                    onClick={() => setActiveTab("textbook")}
                    title="Read pre-generated 10-page textbook study guide"
                  >
                    <BookIcon />
                    View Unit {selectedUnit} Textbook Notes
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
