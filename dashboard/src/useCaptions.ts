import { useCallback, useEffect, useRef, useState } from "react";
import type { AsrInfo, CaptionLine, CaptionPhase } from "./types";

interface StartOptions {
  source?: "mic" | "file";
  path?: string;
  model?: string;
  language?: string | null;
  partials?: boolean;
}

interface WsEvent {
  type?: string;
  kind?: "final" | "partial";
  utterance_id?: number;
  text?: string;
  start?: number;
  end?: number;
  latency_ms?: number | null;
  stage?: string;
  message?: string;
  asr?: AsrInfo;
}

export function useCaptions() {
  const [phase, setPhase] = useState<CaptionPhase>("idle");
  const [asr, setAsr] = useState<AsrInfo | null>(null);
  const [finals, setFinals] = useState<CaptionLine[]>([]);
  const [partial, setPartialState] = useState<CaptionLine | null>(null);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const reset = useCallback(() => {
    setFinals([]);
    setPartialState(null);
    setError(null);
    setPhase("idle");
  }, []);

  const appendFinal = useCallback((line: CaptionLine) => {
    setFinals((current) => {
      const index = current.findIndex((item) => item.id === line.id);
      if (index < 0) return [...current, line];
      const next = [...current];
      next[index] = line;
      return next;
    });
  }, []);

  const setPartial = useCallback((line: CaptionLine | null) => {
    setPartialState(line);
  }, []);

  const loadTranscript = useCallback((lines: CaptionLine[]) => {
    setFinals(lines);
    setPartialState(null);
    setPhase("done");
  }, []);

  const stop = useCallback(() => {
    const socket = socketRef.current;
    setPartialState(null);
    setPhase("done");
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: "stop" }));
    } else {
      socket?.close();
      socketRef.current = null;
    }
  }, []);

  /** Detach from the stream immediately, e.g. before client-side demo playback. */
  const disconnect = useCallback(() => {
    const socket = socketRef.current;
    socketRef.current = null;
    if (socket && socket.readyState <= WebSocket.OPEN) {
      socket.close(1000, "session replaced");
    }
  }, []);

  const start = useCallback((options: StartOptions = {}) => {
    const existing = socketRef.current;
    if (existing && existing.readyState <= WebSocket.OPEN) {
      existing.close(1000, "new session");
    }

    setPhase("connecting");
    setError(null);
    setAsr(null);
    setPartialState(null);

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/captions`);
    socketRef.current = socket;

    socket.onopen = () => {
      socket.send(
        JSON.stringify({
          source: options.source ?? "mic",
          path: options.path,
          model: options.model,
          language: options.language,
          partials: options.partials ?? true,
        }),
      );
    };

    socket.onmessage = (raw) => {
      let event: WsEvent;
      try {
        event = JSON.parse(String(raw.data)) as WsEvent;
      } catch {
        return;
      }

      switch (event.type) {
        case "status":
          if (event.stage === "loading_model") setPhase("loading");
          break;
        case "ready":
          if (event.asr) setAsr(event.asr);
          setPhase("live");
          break;
        case "caption": {
          if (
            event.kind !== "final" ||
            event.utterance_id === undefined ||
            event.text === undefined ||
            event.start === undefined ||
            event.end === undefined
          ) {
            if (event.kind === "partial" && event.text !== undefined) {
              const id = event.utterance_id ?? -1;
              setPartialState({
                id,
                text: event.text,
                start: event.start ?? 0,
                end: event.end ?? 0,
                latencyMs: event.latency_ms ?? null,
              });
            }
            break;
          }
          const id = event.utterance_id;
          appendFinal({
            id,
            text: event.text,
            start: event.start,
            end: event.end,
            latencyMs: event.latency_ms ?? null,
          });
          setPartialState((current) => (current && current.id === id ? null : current));
          break;
        }
        case "error":
          setError(event.message ?? "The server reported an error.");
          setPhase("error");
          break;
        case "done":
          setPartialState(null);
          setPhase("done");
          break;
        default:
          break;
      }
    };

    socket.onerror = () => {
      setError(
        "Could not reach the local server. Start it with `ila serve` and try again.",
      );
      setPhase("error");
    };

    socket.onclose = () => {
      if (socketRef.current !== socket) return;
      socketRef.current = null;
      setPartialState(null);
      setPhase((current) =>
        current === "error" || current === "done" ? current : "idle",
      );
    };
  }, [appendFinal]);

  useEffect(
    () => () => {
      socketRef.current?.close(1000, "dashboard closed");
      socketRef.current = null;
    },
    [],
  );

  return {
    phase,
    asr,
    finals,
    partial,
    error,
    start,
    stop,
    disconnect,
    reset,
    loadTranscript,
    appendFinal,
    setPartial,
    setPhase,
  };
}
