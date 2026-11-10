# Architecture

## Goal

A single offline pipeline that turns a lecture into structured study material. Phase 1 ends at the
caption event stream; every later phase consumes that stream rather than re-processing audio.

```text
                   ┌──────────────────────────────────────────────┐
 audio device  ───▶│ audio.py   MicrophoneSource / FileSource     │
 or media file     │           16 kHz mono float32 blocks         │
                   └───────────────┬──────────────────────────────┘
                                   ▼
                   ┌──────────────────────────────────────────────┐
                   │ segmenter.py  adaptive noise floor +         │
                   │   hysteresis VAD, pre/post-roll, forced split│
                   └───────────────┬──────────────────────────────┘
                                   ▼  Utterance(final=False|True)
                   ┌──────────────────────────────────────────────┐
                   │ pipeline.py   prompts, confidence filter,    │
                   │   CaptionEvent with latency + audio metadata │
                   └───────────────┬──────────────────────────────┘
                         ┌─────────┴─────────┐
                         ▼                   ▼
                 CLI printer          server.py  /ws/captions
                 (live, JSONL)        (status → ready → caption* → done)
```

## Contracts

### `AudioSource`

```python
class AudioSource(Protocol):
    sample_rate: int

    def blocks(self) -> Iterator[np.ndarray]: ...  # mono float32, any block size
    def close(self) -> None: ...
```

Sources must never raise on ordinary end-of-stream; they simply stop yielding.

### `AsrProvider`

```python
class AsrProvider(Protocol):
    @property
    def info(self) -> AsrInfo: ...
    def transcribe(self, audio, *, initial_prompt=None, language=None) -> TranscriptResult: ...
```

`faster-whisper` is the current implementation. A whisper.cpp provider only has to satisfy this
protocol and be returned from `ila.asr.create_asr` — nothing else changes.

### `CaptionEvent`

| Field | Meaning |
| --- | --- |
| `utterance_id` | Stable id; a `final` supersedes all partials with the same id |
| `kind` | `final` or `partial` |
| `text` | Whitespace-normalized transcript |
| `start` / `end` | Seconds from the start of the stream |
| `latency_ms` | Wall time spent transcribing that window |
| `audio_s` | Audio length submitted to the model |
| `avg_logprob`, `no_speech_prob` | Confidence signals, useful for filtering and analytics |

Rule for consumers: **render partials, store finals**. A partial is allowed to change or disappear.

## Latency budget (CPU, int8 base.en)

| Stage | Target | Notes |
| --- | --- | --- |
| Blocking | 40 ms | One audio block; the capture loop never waits on the model between blocks |
| Finalization delay | 450 ms | `MIN_SILENCE_MS`; the main tunable trade-off between snappiness and sentence length |
| Transcription | 0.2–0.6 s | For a 3–6 s utterance at 2–6× realtime |
| End-to-end caption | ≈ 0.7–1.2 s | After the speaker pauses |

Partials are re-transcribed every 2 s while the speaker is still going, so the on-screen text moves
without ever being committed.

## Why utterance-based rather than sliding-window

Sliding-window "streaming Whisper" needs word-level agreement logic to avoid duplicate and
rewritten text. On low-end CPUs the correction churn is visible and the implementation is fragile.
Cutting on silence produces clean, stable captions, and the partial channel supplies the live feel.
The forced-split path exists only for speakers who never pause; it cuts at the quietest frame in the
last 1.5 s, which empirically lands between words.

## Threading model

* CLI: single thread, generator-driven. Backpressure is natural.
* Server: one capture/transcription thread per session; events cross into asyncio via
  `loop.call_soon_threadsafe` and a queue. `stop` is a `threading.Event` checked between blocks, so
  shutdown is bounded by one 40 ms block plus the current inference.

## Storage (phase 2+)

SQLite, one file per installation under `ILA_HOME/data/ila.db`:

```sql
sessions(id, title, course, started_at, ended_at, model)
utterances(id, session_id, start_s, end_s, text, avg_logprob, no_speech_prob)
notes(id, session_id, kind, content, created_at)          -- phase 2
topics(id, course_id, code, title, syllabus_text)          -- phase 3
questions(id, topic_id, text, options_json, answer, difficulty, source)  -- phase 4
attempts(id, question_id, student_id, correct, response_ms, created_at)  -- phase 4
```

## Evaluation (report-ready)

1. **ASR quality** — word error rate against 3–5 manually transcribed lecture clips (10 min total),
   reported per noise condition (quiet room, fan, corridor).
2. **Latency** — median/p95 end-to-end caption delay from the `latency_ms` field plus measured
   silence timeout; publish the realtime factor per device.
3. **Segmentation** — count of clipped first words and split sentences over the same clips; tune
   `PRE_ROLL_MS` / `MIN_SILENCE_MS` against this.
4. **Resource use** — peak RSS and CPU utilisation for base.en and small.en on the target low-end
   machine; this is the headline claim of the project, so measure it early.

Instrumentation already available: every run prints utterances, audio seconds, wall time and
realtime factor; `--out` writes JSONL with per-event latency and confidence.

## Offline guarantees

* Models are downloaded once into `ILA_HOME/models` and loaded with `local_files_only` when set.
* No telemetry, no remote calls at runtime; `faster-whisper` uses only local CTranslate2 inference.
* The server binds to `127.0.0.1` by default and only allows the local Vite origin.
