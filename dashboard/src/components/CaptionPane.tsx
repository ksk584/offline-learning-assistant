import { useEffect, useRef } from "react";
import type { CaptionLine, CaptionPhase } from "../types";
import { formatDuration, formatTime } from "../format";
import { MicIcon, SparkIcon, TrashIcon } from "./icons";

interface CaptionPaneProps {
  finals: CaptionLine[];
  partial: CaptionLine | null;
  phase: CaptionPhase;
  onClear: () => void;
  onGenerate?: () => void;
  generatingNotes?: boolean;
  hasNotes?: boolean;
}

export function CaptionPane({
  finals,
  partial,
  phase,
  onClear,
  onGenerate,
  generatingNotes = false,
  hasNotes = false,
}: CaptionPaneProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const active = phase === "live" || phase === "loading" || phase === "connecting";
  const duration = finals.length ? finals[finals.length - 1].end : 0;

  useEffect(() => {
    const element = scrollRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [finals.length, partial?.text]);

  const emptyCopy = (() => {
    switch (phase) {
      case "connecting":
        return "Connecting to on-device audio stream…";
      case "loading":
        return "Loading Whisper model into local memory…";
      case "live":
        return "Listening to lecture. Spoken utterances will appear here in real-time.";
      case "error":
        return "Audio capture stream encountered an error. Check audio device settings.";
      case "done":
        return "Lecture session completed. Generate grounded notes from this transcript.";
      default:
        return "Start the microphone, upload audio/video, or play an NCERT demo lecture to begin.";
    }
  })();

  return (
    <section className="panel caption-panel">
      {/* Panel Header */}
      <header className="panel-header">
        <div className="panel-title-group">
          <span className="panel-kicker">Speech Recognition</span>
          <h2>Live Transcript</h2>
        </div>

        <div className="panel-actions">
          {finals.length > 0 && onGenerate && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={onGenerate}
              disabled={generatingNotes}
              title="Synthesize and map transcript to NCERT syllabus"
            >
              <SparkIcon />
              <span>{generatingNotes ? "Synthesizing…" : hasNotes ? "Update Notes" : "Generate Notes"}</span>
            </button>
          )}

          <span className={`badge ${active ? "badge-success" : ""}`}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: active ? "var(--success)" : "var(--text-muted)",
              }}
            />
            {active ? "Capturing" : phase === "done" ? "Finished" : "Idle"}
          </span>

          <button
            type="button"
            className="btn-icon"
            onClick={onClear}
            title="Clear transcript"
            aria-label="Clear transcript"
            disabled={!finals.length && !partial}
          >
            <TrashIcon />
          </button>
        </div>
      </header>

      {/* Transcript Scroll Area */}
      <div className="caption-scroll" ref={scrollRef}>
        {!finals.length && !partial ? (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "40px 20px",
              textAlign: "center",
              color: "var(--text-muted)",
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "var(--radius-md)",
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 14,
                color: "var(--text-secondary)",
              }}
            >
              <MicIcon />
            </div>
            <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", maxWidth: 360, marginBottom: 8 }}>
              {emptyCopy}
            </p>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Transcriptions run 100% locally on your device with faster-whisper.
            </span>
          </div>
        ) : (
          <>
            {finals.map((line, index) => (
              <article className="caption-line" key={`${line.id}-${index}`}>
                <time className="caption-time">{formatTime(line.start)}</time>
                <div className="caption-text">
                  <p>{line.text}</p>
                </div>
              </article>
            ))}

            {partial && (
              <article className="caption-line partial">
                <time className="caption-time">{formatTime(partial.start)}</time>
                <div className="caption-text">
                  <p>
                    {partial.text}
                    <span
                      style={{
                        display: "inline-block",
                        width: "2px",
                        height: "1em",
                        backgroundColor: "var(--accent)",
                        marginLeft: "4px",
                        verticalAlign: "middle",
                        animation: "pulse-dot 1s infinite",
                      }}
                    />
                  </p>
                </div>
              </article>
            )}
          </>
        )}
      </div>

      {/* Caption Footer */}
      <footer className="caption-footer">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span>
            <strong style={{ color: "var(--text-primary)" }}>{finals.length}</strong> utterances
          </span>
          <span>·</span>
          <span>
            <strong style={{ color: "var(--text-primary)" }}>{formatDuration(duration)}</strong> captured
          </span>
        </div>

        {finals.length > 0 && onGenerate && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={onGenerate}
            disabled={generatingNotes}
            style={{ fontSize: "0.74rem", color: "var(--accent-text)" }}
          >
            <span>{generatingNotes ? "Writing notes…" : "Convert to Notes →"}</span>
          </button>
        )}
      </footer>
    </section>
  );
}
