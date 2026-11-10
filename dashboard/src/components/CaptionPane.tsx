import { useEffect, useRef } from "react";
import type { CaptionLine, CaptionPhase } from "../types";
import { formatDuration, formatTime } from "../format";
import { MicIcon, TrashIcon } from "./icons";

interface CaptionPaneProps {
  finals: CaptionLine[];
  partial: CaptionLine | null;
  phase: CaptionPhase;
  onClear: () => void;
}

export function CaptionPane({ finals, partial, phase, onClear }: CaptionPaneProps) {
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
        return "Connecting to the local caption stream…";
      case "loading":
        return "Loading the on-device Whisper model. The first load can take a few seconds.";
      case "live":
        return "Listening. Speak naturally and pause briefly to finalize a caption.";
      case "error":
        return "The caption stream stopped with an error. Check the message above and try again.";
      case "done":
        return "Session finished. Generate notes from the transcript, or start another capture.";
      default:
        return "Start the microphone, play an NCERT demo, or upload a recording. Finals are stored as transcript lines; partials are only previews.";
    }
  })();

  return (
    <section className="panel caption-panel">
      <header className="panel-header">
        <div>
          <p className="panel-kicker">On-device captions</p>
          <h2>Live transcript</h2>
        </div>
        <div className="panel-actions">
          <span className={`stream-state ${active ? "active" : ""}`}>
            <span className="stream-dot" />
            {active ? "capturing" : phase === "done" ? "ended" : "idle"}
          </span>
          <button
            type="button"
            className="icon-btn"
            onClick={onClear}
            title="Clear transcript"
            aria-label="Clear transcript"
            disabled={!finals.length && !partial}
          >
            <TrashIcon />
          </button>
        </div>
      </header>

      <div className="caption-scroll" ref={scrollRef}>
        {!finals.length && !partial ? (
          <div className="empty-state caption-empty">
            <span className="empty-icon">
              <MicIcon />
            </span>
            <p>{emptyCopy}</p>
            <span className="empty-hint">
              Finals arrive after a pause; partial captions are replaced, never duplicated.
            </span>
          </div>
        ) : (
          <>
            {finals.map((line, index) => (
              <article className="caption-line" key={`${line.id}-${index}`}>
                <time>{formatTime(line.start)}</time>
                <div className="caption-body">
                  <p>{line.text}</p>
                  {line.latencyMs !== null && line.latencyMs !== undefined ? (
                    <span className="latency">{Math.round(line.latencyMs)} ms</span>
                  ) : null}
                </div>
              </article>
            ))}
            {partial ? (
              <article className="caption-line partial">
                <time>{formatTime(partial.start)}</time>
                <div className="caption-body">
                  <p>
                    {partial.text}
                    <span className="caret" />
                  </p>
                </div>
              </article>
            ) : null}
          </>
        )}
      </div>

      <footer className="caption-footer">
        <span>
          <strong>{finals.length}</strong> utterance{finals.length === 1 ? "" : "s"}
        </span>
        <span>
          <strong>{formatDuration(duration)}</strong> captured
        </span>
        <span className="footer-note">finals only → notes</span>
      </footer>
    </section>
  );
}
