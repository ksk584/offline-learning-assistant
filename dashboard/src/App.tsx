import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createNotes, getConfig, getDemo, transcribeFile } from "./api";
import { AskPane } from "./components/AskPane";
import { CaptionPane } from "./components/CaptionPane";
import { CurriculumPanel } from "./components/CurriculumPanel";
import { NotesPane } from "./components/NotesPane";
import { PdfNotesViewer } from "./components/PdfNotesViewer";
import { QuizPane } from "./components/QuizPane";
import { TeacherDashboard } from "./components/TeacherDashboard";
import {
  BarChartIcon,
  BookIcon,
  CheckCircleIcon,
  FileTextIcon,
  MessageSquareIcon,
  MicIcon,
  SettingsIcon,
  StopIcon,
  UploadIcon,
  WarningIcon,
  XIcon,
} from "./components/icons";
import { formatDuration, messageOf } from "./format";
import type { AppConfig, DemoLecture, DemoLine, NotesResult } from "./types";
import { useCaptions } from "./useCaptions";

const PROFILE_LABELS: Record<string, string> = {
  extractive: "Extractive TextRank (No LLM)",
  auto: "Auto · Hardware Detected",
  potato: "Potato · Qwen 0.8B Q4",
  balanced: "Balanced · Qwen 2B Q4",
  full: "Full · Qwen 4B Q4",
};

const DEMO_SPEED = 9;

export function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [classLevel, setClassLevel] = useState(10);
  const [subject, setSubject] = useState("science");
  const [profile, setProfile] = useState("auto");
  const [demo, setDemo] = useState<DemoLecture | null>(null);
  const [demoPlaying, setDemoPlaying] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [notes, setNotes] = useState<NotesResult | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [notesExpanded, setNotesExpanded] = useState<boolean>(false);
  const [mappedTopic, setMappedTopic] = useState<string | null>(null);
  const [chapterNumber, setChapterNumber] = useState<number | null>(null);
  const [mainView, setMainView] = useState<"capture" | "ask" | "quiz" | "teacher" | "pdf">("capture");
  const [activeNcertUnit, setActiveNcertUnit] = useState<number>(1);
  const [uploading, setUploading] = useState(false);
  const [uploadInfo, setUploadInfo] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const timers = useRef<number[]>([]);

  const loadNcertUnit = useCallback((unitNum: number) => {
    setActiveNcertUnit(unitNum);
    setMainView("pdf");
  }, []);

  const {
    phase,
    asr,
    finals,
    partial,
    error: captionError,
    start,
    stop,
    disconnect,
    reset,
    loadTranscript,
    appendFinal,
    setPartial,
    setPhase,
  } = useCaptions();

  const loadConfig = useCallback(async () => {
    setConfigError(null);
    try {
      const loaded = await getConfig();
      setConfig(loaded);
      setClassLevel(loaded.curriculum.default_class_level);
      setSubject(loaded.curriculum.default_subject);
    } catch (error) {
      setConfigError(messageOf(error));
    }
  }, []);

  useEffect(() => {
    void loadConfig();
  }, [loadConfig]);

  const clearTimers = useCallback(() => {
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
  }, []);

  useEffect(() => () => clearTimers(), [clearTimers]);

  const clearDerived = useCallback(() => {
    setNotes(null);
    setMarkdown("");
    setMappedTopic(null);
    setChapterNumber(null);
    setNotesError(null);
    setUploadInfo(null);
    setUploadError(null);
    setDemoError(null);
  }, []);

  const stopDemo = useCallback(() => {
    clearTimers();
    setDemoPlaying(false);
    setPhase("done");
  }, [clearTimers, setPhase]);

  const playDemo = useCallback(async () => {
    clearTimers();
    disconnect();
    reset();
    clearDerived();
    setDemo(null);
    setDemoLoading(true);
    setDemoPlaying(false);

    let lecture: DemoLecture;
    try {
      lecture = await getDemo(classLevel, subject);
    } catch (error) {
      setDemoLoading(false);
      setDemoError(messageOf(error));
      return;
    }

    setDemo(lecture);
    setDemoLoading(false);
    setDemoPlaying(true);
    setPhase("live");

    const baseline = lecture.lines[0]?.start ?? 0;
    lecture.lines.forEach((line, index) => {
      const id = index + 1;
      const finalAt = Math.max(260, ((line.end - baseline) / DEMO_SPEED) * 1000);
      const previewAt = Math.max(160, finalAt - 300);
      const words = line.text.split(/\s+/);
      const preview = words
        .slice(0, Math.max(2, Math.ceil(words.length * 0.55)))
        .join(" ");

      timers.current.push(
        window.setTimeout(() => {
          setPartial({
            id,
            text: preview,
            start: line.start,
            end: line.end,
          });
        }, previewAt),
      );

      timers.current.push(
        window.setTimeout(() => {
          appendFinal({
            id,
            text: line.text,
            start: line.start,
            end: line.end,
            latencyMs: null,
          });
          setPartial(null);
        }, finalAt),
      );
    });

    const finishAt =
      lecture.lines.length > 0
        ? ((lecture.lines[lecture.lines.length - 1].end - baseline) / DEMO_SPEED) *
            1000 +
          400
        : 1000;
    timers.current.push(
      window.setTimeout(() => {
        setDemoPlaying(false);
        setPhase("done");
      }, finishAt),
    );
  }, [
    appendFinal,
    classLevel,
    clearDerived,
    clearTimers,
    disconnect,
    reset,
    setPartial,
    setPhase,
    subject,
  ]);

  const handleSelect = useCallback(
    (nextLevel: number, nextSubject: string) => {
      clearTimers();
      disconnect();
      reset();
      clearDerived();
      setClassLevel(nextLevel);
      setSubject(nextSubject);
      setDemo(null);
      setDemoPlaying(false);
      setDemoLoading(false);
    },
    [clearDerived, clearTimers, disconnect, reset],
  );

  const handleClear = useCallback(() => {
    clearTimers();
    disconnect();
    reset();
    clearDerived();
    setDemo(null);
    setDemoPlaying(false);
    setDemoLoading(false);
  }, [clearDerived, clearTimers, disconnect, reset]);

  const startMic = useCallback(() => {
    clearTimers();
    setDemo(null);
    setDemoPlaying(false);
    setDemoLoading(false);
    clearDerived();
    start();
  }, [clearDerived, clearTimers, start]);

  const handleUpload = useCallback(
    async (file: File) => {
      clearTimers();
      disconnect();
      reset();
      clearDerived();
      setDemo(null);
      setDemoPlaying(false);
      setDemoLoading(false);
      setUploading(true);
      setUploadError(null);
      setUploadInfo(null);
      try {
        const response = await transcribeFile(file, {
          classLevel,
          subject,
          profile,
          useLlm: true,
        });
        loadTranscript(
          response.lines.map((line, index) => ({
            id: index + 1,
            text: line.text,
            start: line.start,
            end: line.end,
            latencyMs: null,
          })),
        );
        if (response.notes && response.markdown) {
          setNotes(response.notes);
          setMarkdown(response.markdown);
        }
        setNotesError(response.notes_error);
        setUploadInfo(
          `${file.name} · ${formatDuration(response.duration_s)} · ` +
            `${response.lines.length} utterances · ${response.asr.model} on ` +
            `${response.asr.device}/${response.asr.compute_type}`,
        );
      } catch (error) {
        setUploadError(messageOf(error));
      } finally {
        setUploading(false);
      }
    },
    [classLevel, clearDerived, clearTimers, disconnect, loadTranscript, profile, reset, subject],
  );

  const generate = useCallback(async () => {
    if (!finals.length) return;
    setNotesLoading(true);
    setNotesError(null);

    const subjectLabel = config?.curriculum.subject_labels[subject] ?? subject;
    const title = demo?.title ?? `Class ${classLevel} ${subjectLabel} lecture`;
    try {
      const response = await createNotes({
        lines: finals.map((line) => ({
          text: line.text,
          start: line.start,
          end: line.end,
        })),
        title,
        class_level: classLevel,
        subject,
        profile,
        use_llm: profile !== "extractive",
        use_syllabus: true,
      });
      setNotes(response.notes);
      setMarkdown(response.markdown);
      setMappedTopic(response.mapped_topic || null);
      setChapterNumber(response.chapter_number || null);
    } catch (error) {
      setNotesError(messageOf(error));
    } finally {
      setNotesLoading(false);
    }
  }, [classLevel, config, demo, finals, profile, subject]);

  const busy = phase === "connecting" || phase === "loading" || phase === "live";

  const lectureLines = useMemo<DemoLine[]>(
    () =>
      finals.map((line) => ({
        text: line.text,
        start: line.start,
        end: line.end,
      })),
    [finals],
  );

  const subjectLabel = config?.curriculum.subject_labels[subject] ?? subject;
  const course = useMemo(
    () =>
      config?.curriculum.courses.find(
        (item) => item.class_level === classLevel && item.subject === subject,
      ) ?? null,
    [classLevel, config, subject],
  );
  const courseChapters = course?.chapters ?? [];
  const demoHint = useMemo(() => {
    if (demo) return demo.title;
    return (
      config?.curriculum.demos.find(
        (item) => item.class_level === classLevel && item.subject === subject,
      )?.title ?? `Class ${classLevel} ${subjectLabel} NCERT demo`
    );
  }, [classLevel, config, demo, subject, subjectLabel]);

  const sessionLabel = useMemo(() => {
    if (demoPlaying) return "Playing NCERT demo lecture";
    if (uploading) return "Transcribing uploaded media file";
    switch (phase) {
      case "connecting":
        return "Connecting to speech stream…";
      case "loading":
        return "Loading Whisper model…";
      case "live":
        return "Listening · Speech captured";
      case "error":
        return "Audio stream error";
      case "done":
        return finals.length ? "Transcript ready for review" : "Capture completed";
      default:
        return "Session idle";
    }
  }, [demoPlaying, finals.length, phase, uploading]);

  return (
    <div className="app-shell">
      {/* ------------------------------------------------------------------ Top Header */}
      <header className="app-header">
        <div className="app-brand">
          <div className="brand-mark">
            <BookIcon />
          </div>
          <div className="brand-info">
            <span className="brand-name">Offline Lecture Assistant</span>
            <span className="brand-curriculum">
              Class {classLevel} · {subjectLabel}
            </span>
          </div>
        </div>

        {/* Global Navigation Tabs (Linear style) */}
        <nav className="app-nav" aria-label="Main Navigation">
          <button
            type="button"
            className={`nav-tab-btn ${mainView === "capture" ? "active" : ""}`}
            onClick={() => setMainView("capture")}
          >
            <MicIcon />
            <span>Capture &amp; Notes</span>
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${mainView === "ask" ? "active" : ""}`}
            onClick={() => setMainView("ask")}
          >
            <MessageSquareIcon />
            <span>Syllabus Q&amp;A</span>
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${mainView === "quiz" ? "active" : ""}`}
            onClick={() => setMainView("quiz")}
          >
            <CheckCircleIcon />
            <span>Adaptive Quizzes</span>
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${mainView === "teacher" ? "active" : ""}`}
            onClick={() => setMainView("teacher")}
          >
            <BarChartIcon />
            <span>Teacher Analytics</span>
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${mainView === "pdf" ? "active" : ""}`}
            onClick={() => setMainView("pdf")}
          >
            <FileTextIcon />
            <span>NCERT Master Notes</span>
          </button>
        </nav>

        {/* Right Utilities & Settings */}
        <div className="app-utilities">
          <span className="offline-pill" title="Fully on-device inference. Zero external API calls.">
            <span className="offline-dot" />
            <span>Local &amp; Offline</span>
          </span>
          <button
            type="button"
            className="btn-icon"
            onClick={() => setShowSettings(true)}
            title="System &amp; Model Settings"
            aria-label="Settings"
          >
            <SettingsIcon />
          </button>
        </div>
      </header>

      {/* Backend Unreachable Alert Banner */}
      {configError && (
        <div className="inline-warning error" style={{ margin: "10px 20px 0" }}>
          <WarningIcon />
          <span>
            <strong>Local backend unreachable.</strong> {configError} Start server via{" "}
            <code>ila serve</code>, then{" "}
            <button type="button" className="btn btn-sm btn-ghost" onClick={() => void loadConfig()}>
              Retry Connection
            </button>
          </span>
        </div>
      )}

      {/* ------------------------------------------------------------------ Main Workspaces */}
      {mainView === "pdf" ? (
        <PdfNotesViewer initialUnit={activeNcertUnit || 1} />
      ) : mainView === "teacher" ? (
        <div className="study-view">
          <TeacherDashboard />
        </div>
      ) : mainView === "ask" ? (
        <div className="study-view">
          <AskPane
            classLevel={classLevel}
            subject={subject}
            subjectLabel={subjectLabel}
            lines={lectureLines}
            sourceHint={demoHint}
            courseLabel={course?.label ?? null}
            onSelectSubject={(s) => setSubject(s)}
          />
        </div>
      ) : mainView === "quiz" ? (
        <div className="study-view">
          <QuizPane
            classLevel={classLevel}
            subject={subject}
            subjectLabel={subjectLabel}
            courseLabel={course?.label ?? null}
            chapters={courseChapters}
            lines={lectureLines}
            sourceHint={demoHint}
            onSelectSubject={(s) => setSubject(s)}
          />
        </div>
      ) : (
        /* Workspace 1: Live Capture & Notes */
        <div className={`layout ${notesExpanded ? "notes-expanded" : ""}`}>
          {/* Left Area: Session Controls & Syllabus Map */}
          <aside className="sidebar">
            {/* Session Card */}
            <section className="panel control-panel">
              <header className="panel-header">
                <div className="panel-title-group">
                  <span className="panel-kicker">Lecture Recording</span>
                  <h2>Session Controls</h2>
                </div>
              </header>

              <div className="control-body">
                <div className="capture-action-row">
                  <button
                    type="button"
                    className={`btn capture-btn ${busy ? "btn-danger" : "btn-primary"}`}
                    onClick={busy ? stop : startMic}
                    disabled={demoPlaying || uploading}
                  >
                    {busy ? <StopIcon /> : <MicIcon />}
                    <span>{busy ? "Stop Mic" : "Start Mic"}</span>
                  </button>

                  <button
                    type="button"
                    className="btn capture-btn btn-secondary"
                    onClick={() => fileInput.current?.click()}
                    disabled={busy || uploading || demoPlaying}
                  >
                    <UploadIcon />
                    <span>{uploading ? "Parsing…" : "Upload File"}</span>
                  </button>

                  <input
                    ref={fileInput}
                    type="file"
                    accept=".wav,.mp3,.m4a,.flac,.ogg,.opus,.mp4,.webm,.mkv,audio/*,video/*"
                    hidden
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      event.target.value = "";
                      if (file) void handleUpload(file);
                    }}
                  />
                </div>

                <div className="session-status-card">
                  <div className="status-indicator">
                    <span className={`status-dot ${busy ? "active" : ""}`} />
                    <span>{sessionLabel}</span>
                  </div>
                  {asr && (
                    <span className="badge">
                      {asr.model} · {asr.compute_type}
                    </span>
                  )}
                </div>

                {captionError && (
                  <div className="inline-warning error">
                    <WarningIcon />
                    <span>{captionError}</span>
                  </div>
                )}
                {uploadInfo && (
                  <div className="badge" style={{ fontSize: "0.72rem", padding: "4px 8px", width: "100%", justifyContent: "center" }}>
                    {uploadInfo}
                  </div>
                )}
                {uploadError && (
                  <div className="inline-warning error">
                    <WarningIcon />
                    <span>{uploadError}</span>
                  </div>
                )}
                {demoError && (
                  <div className="inline-warning error">
                    <WarningIcon />
                    <span>{demoError}</span>
                  </div>
                )}
              </div>
            </section>

            {/* Curriculum & Syllabus Navigation */}
            <CurriculumPanel
              config={config}
              classLevel={classLevel}
              subject={subject}
              onSelect={handleSelect}
              syllabus={notes?.curriculum ?? null}
              demo={demo}
              demoPlaying={demoPlaying}
              demoLoading={demoLoading}
              onPlayDemo={playDemo}
              onStopDemo={stopDemo}
              onSelectNcertUnit={loadNcertUnit}
              activeNcertUnit={activeNcertUnit}
            />
          </aside>

          {/* Central Workspace: Live Transcript + Notes Split */}
          <main className="workspace">
            <CaptionPane
              finals={finals}
              partial={partial}
              phase={phase}
              onClear={handleClear}
              onGenerate={generate}
              generatingNotes={notesLoading}
              hasNotes={notes !== null}
            />
            <NotesPane
              notes={notes}
              markdown={markdown}
              loading={notesLoading}
              error={notesError}
              hasLines={finals.length > 0}
              finalsCount={finals.length}
              onGenerate={generate}
              onSelectNcertUnit={loadNcertUnit}
              activeNcertUnit={activeNcertUnit}
              onStartMic={startMic}
              onPlayDemo={playDemo}
              isExpanded={notesExpanded}
              onToggleExpand={() => setNotesExpanded((prev) => !prev)}
              mappedTopic={mappedTopic}
              chapterNumber={chapterNumber}
              classLevel={classLevel}
              subject={subject}
            />
          </main>
        </div>
      )}

      {/* ------------------------------------------------------------------ System Settings Modal */}
      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <SettingsIcon />
                <h3>System &amp; Model Architecture</h3>
              </div>
              <button
                type="button"
                className="btn-icon"
                onClick={() => setShowSettings(false)}
                aria-label="Close"
              >
                <XIcon />
              </button>
            </header>

            <div className="modal-body">
              <div className="setting-item">
                <span className="setting-label">Notes Generation LLM</span>
                <select
                  className="select"
                  value={profile}
                  onChange={(e) => setProfile(e.target.value)}
                  style={{ width: "100%" }}
                >
                  {["extractive", "auto", "potato", "balanced", "full"].map((value) => (
                    <option key={value} value={value}>
                      {PROFILE_LABELS[value] ?? value}
                    </option>
                  ))}
                </select>
                <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "4px" }}>
                  Active model: {config?.notes.model ?? "Qwen 3.5 2B"} ({config?.notes.size_mb ?? 0} MB, {config?.notes.threads ?? 4} threads)
                </span>
              </div>

              <div className="setting-item">
                <span className="setting-label">Speech Recognition Engine (ASR)</span>
                <div className="setting-value-box">
                  <span>faster-whisper</span>
                  <span className="badge">{config?.asr.model ?? "base.en"} · {config?.asr.device ?? "cpu"}</span>
                </div>
              </div>

              <div className="setting-item">
                <span className="setting-label">Syllabus Retrieval &amp; Grounding</span>
                <div className="setting-value-box">
                  <span>Hybrid BM25 + Embeddings</span>
                  <span className="badge badge-accent">100% On-Device</span>
                </div>
              </div>

              <div className="setting-item">
                <span className="setting-label">Data Persistence</span>
                <div className="setting-value-box">
                  <span>Local SQLite Database</span>
                  <span className="badge badge-success">Schema v1</span>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "10px" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowSettings(false)}
                >
                  Close Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ Global Footer Bar */}
      <footer className="footer-bar">
        <span>Offline Intelligent Lecture Assistant · SDG 4 Education · Team 9</span>
        <span>faster-whisper · llama.cpp · SQLite {config ? `· v${config.version}` : ""}</span>
      </footer>
    </div>
  );
}
