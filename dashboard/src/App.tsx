import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createNotes, getConfig, getDemo, transcribeFile } from "./api";
import { CaptionPane } from "./components/CaptionPane";
import { CurriculumPanel } from "./components/CurriculumPanel";
import { NotesPane } from "./components/NotesPane";
import { PdfNotesViewer } from "./components/PdfNotesViewer";
import {
  BookIcon,
  CpuIcon,
  MicIcon,
  ShieldIcon,
  SparkIcon,
  StopIcon,
  UploadIcon,
  WarningIcon,
} from "./components/icons";
import { formatDuration, messageOf } from "./format";
import type { AppConfig, DemoLecture, NotesResult } from "./types";
import { useCaptions } from "./useCaptions";

const PROFILE_LABELS: Record<string, string> = {
  extractive: "Extractive only · no model",
  auto: "Auto · detect hardware",
  potato: "Potato · 0.8B Q4",
  balanced: "Balanced · 2B Q4",
  full: "Full · 4B Q4",
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
  const [mainView, setMainView] = useState<"pdf" | "capture">("pdf");
  const [activeNcertUnit, setActiveNcertUnit] = useState<number>(1);
  const [uploading, setUploading] = useState(false);
  const [uploadInfo, setUploadInfo] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
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
      setDemoError(messageOf(error));
      setDemoLoading(false);
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

    timers.current.push(
      window.setTimeout(() => {
        setDemoPlaying(false);
        setPhase("done");
      }, Math.max(900, ((lecture.lines.at(-1)?.end ?? 0) - baseline) / DEMO_SPEED * 1000 + 500)),
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
    (level: number, name: string) => {
      if (demoPlaying) {
        clearTimers();
        setDemoPlaying(false);
        setPhase("done");
      }
      setClassLevel(level);
      setSubject(name);
      setDemo(null);
      setDemoError(null);
    },
    [clearTimers, demoPlaying, setPhase],
  );

  const startMic = useCallback(() => {
    clearTimers();
    disconnect();
    reset();
    clearDerived();
    setDemo(null);
    setDemoPlaying(false);
    start({
      source: "mic",
      model: config?.asr.model,
      language: config?.asr.language ?? null,
      partials: true,
    });
  }, [clearDerived, clearTimers, config, disconnect, reset, start]);

  const handleClear = useCallback(() => {
    clearTimers();
    disconnect();
    reset();
    clearDerived();
    setDemoPlaying(false);
  }, [clearDerived, clearTimers, disconnect, reset]);

  const handleUpload = useCallback(
    async (file: File) => {
      clearTimers();
      disconnect();
      reset();
      clearDerived();
      setDemo(null);
      setDemoPlaying(false);
      setUploading(true);

      try {
        const response = await transcribeFile(file, {
          classLevel,
          subject,
          profile,
          useLlm: profile !== "extractive",
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
      });
      setNotes(response.notes);
      setMarkdown(response.markdown);
    } catch (error) {
      setNotesError(messageOf(error));
    } finally {
      setNotesLoading(false);
    }
  }, [classLevel, config, demo, finals, profile, subject]);

  const busy = phase === "connecting" || phase === "loading" || phase === "live";

  const sessionLabel = useMemo(() => {
    if (demoPlaying) return "Playing NCERT demo";
    if (uploading) return "Transcribing uploaded media";
    switch (phase) {
      case "connecting":
        return "Connecting to local server";
      case "loading":
        return "Loading Whisper model";
      case "live":
        return "Capturing (finals arrive on pauses)";
      case "error":
        return "Caption stream error";
      case "done":
        return finals.length ? "Transcript ready" : "Session finished";
      default:
        return "Idle — start a session or replay a demo";
    }
  }, [demoPlaying, finals.length, phase, uploading]);

  const lightClass = demoPlaying || phase === "live"
    ? "live"
    : phase === "connecting" || phase === "loading" || uploading
      ? "busy"
      : phase === "error" || uploadError || demoError
        ? "error"
        : "";

  const notesStatus = config
    ? config.notes.available
      ? `${config.notes.profile} · ${config.notes.model}`
      : "extractive fallback"
    : "checking models…";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">
            <BookIcon />
          </span>
          <div>
            <p className="brand-eyebrow">SDG 4 · Team 9 · fully offline</p>
            <h1>Offline Lecture Assistant</h1>
            <p className="brand-sub">
              Live captions, NCERT syllabus alignment and grounded notes — no cloud, no keys.
            </p>
          </div>
        </div>
        <div className="status-strip">
          <span className={`status-pill ${config?.offline ? "ok" : ""}`}>
            <ShieldIcon />
            {config?.offline ? "On-device" : "Offline"}
          </span>
          <span className="status-pill">
            <CpuIcon />
            {config ? `${config.asr.model} · ${config.asr.device}` : "loading config…"}
          </span>
          <span className={`status-pill ${config?.notes.available ? "ok" : "warn"}`}>
            <SparkIcon />
            {notesStatus}
          </span>
        </div>
      </header>

      {configError ? (
        <div className="inline-warning error config-banner">
          <WarningIcon />
          <span>
            <strong>Backend unreachable.</strong> {configError} Start it with{" "}
            <code>ila serve</code>, then{" "}
            <button type="button" className="link-btn" onClick={() => void loadConfig()}>
              retry
            </button>
            .
          </span>
        </div>
      ) : null}

      <div
        className="view-mode-tabs"
        style={{
          display: "flex",
          gap: "10px",
          padding: "10px 24px",
          background: "rgba(2, 4, 8, 0.9)",
          borderBottom: "1px solid rgba(37, 99, 235, 0.2)",
        }}
      >
        <button
          type="button"
          className={`btn ${mainView === "capture" ? "primary" : "ghost"}`}
          style={{ padding: "8px 18px", fontSize: "0.88rem", fontWeight: 700 }}
          onClick={() => setMainView("capture")}
        >
          🎙️ Live Lecture Capture & Transcribe
        </button>
        <button
          type="button"
          className={`btn ${mainView === "pdf" ? "primary" : "ghost"}`}
          style={{ padding: "8px 18px", fontSize: "0.88rem", fontWeight: 700 }}
          onClick={() => setMainView("pdf")}
        >
          📑 NCERT 10-Page Master Notes (Full Document Reader)
        </button>
      </div>

      {mainView === "pdf" ? (
        <div style={{ flex: 1, padding: "16px 24px", display: "flex", overflow: "hidden", minHeight: "calc(100vh - 160px)" }}>
          <PdfNotesViewer initialUnit={activeNcertUnit || 1} />
        </div>
      ) : (
        <div className="layout">
          <aside className="sidebar">
          <section className="panel control-panel">
            <header className="panel-header">
              <div>
                <p className="panel-kicker">Lecture capture</p>
                <h2>Session</h2>
              </div>
            </header>

            <div className="control-body">
              <div className="button-row">
                <button
                  type="button"
                  className={`btn ${busy ? "danger" : "primary"}`}
                  onClick={busy ? stop : startMic}
                  disabled={demoPlaying || uploading}
                >
                  {busy ? <StopIcon /> : <MicIcon />}
                  {busy ? "Stop session" : "Start microphone"}
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => fileInput.current?.click()}
                  disabled={busy || uploading || demoPlaying}
                >
                  <UploadIcon />
                  {uploading ? "Transcribing…" : "Upload audio or video"}
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

              <div className="field">
                <label htmlFor="notes-profile">Notes model</label>
                <select
                  id="notes-profile"
                  className="select"
                  value={profile}
                  onChange={(event) => setProfile(event.target.value)}
                >
                  {["extractive", "auto", "potato", "balanced", "full"].map((value) => (
                    <option key={value} value={value}>
                      {PROFILE_LABELS[value] ?? value}
                    </option>
                  ))}
                </select>
              </div>

              <div className="session-note">
                <span className={`status-light ${lightClass}`} />
                <span>{sessionLabel}</span>
                {asr ? (
                  <span className="session-detail">
                    {asr.model} · {asr.compute_type}
                  </span>
                ) : null}
              </div>

              {captionError ? (
                <div className="inline-warning error flush">
                  <WarningIcon />
                  <span>{captionError}</span>
                </div>
              ) : null}
              {uploadError ? (
                <div className="inline-warning error flush">
                  <WarningIcon />
                  <span>{uploadError}</span>
                </div>
              ) : null}
              {demoError ? (
                <div className="inline-warning error flush">
                  <WarningIcon />
                  <span>{demoError}</span>
                </div>
              ) : null}
              {uploadInfo ? <p className="notice upload-info">{uploadInfo}</p> : null}

              {config ? (
                config.notes.available ? (
                  <p className="notice">
                    Notes model ready: <strong>{config.notes.model}</strong> ·{" "}
                    {config.notes.size_mb} MB · {config.notes.threads} threads.
                  </p>
                ) : (
                  <p className="notice">
                    No notes model loaded — notes fall back to TextRank. Run{" "}
                    <code>ila download-llm</code> to enable the local writer.
                  </p>
                )
              ) : null}

              <div className="demo-meta">
                {demo ? (
                  <>
                    <strong>{demo.title}</strong>
                    <span>
                      {demo.chapter} · Class {demo.class_level}{" "}
                      {config?.curriculum.subject_labels[demo.subject] ?? demo.subject}
                    </span>
                  </>
                ) : (
                  <>
                    <strong>Built-in NCERT demos</strong>
                    <span>
                      Six lectures, one per class and subject. Replay is client-side and
                      needs no microphone.
                    </span>
                  </>
                )}
              </div>
            </div>
          </section>

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

        <main className="workspace">
          <CaptionPane
            finals={finals}
            partial={partial}
            phase={phase}
            onClear={handleClear}
          />
          <NotesPane
            notes={notes}
            markdown={markdown}
            loading={notesLoading}
            error={notesError}
            hasLines={finals.length > 0}
            onGenerate={generate}
            onSelectNcertUnit={loadNcertUnit}
            activeNcertUnit={activeNcertUnit}
            onStartMic={startMic}
            onPlayDemo={playDemo}
          />
        </main>
      </div>
      )}

      <footer className="footer-bar">
        <span>
          <strong>Offline Intelligent Lecture Assistant</strong> · SDG 4 · Team 9
        </span>
        <span>
          faster-whisper · llama.cpp · React
          {config ? ` · v${config.version}` : ""}
        </span>
      </footer>
    </div>
  );
}
