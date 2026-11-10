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

Phase 2 adds a second, batch pipeline over the same contract:

```text
final captions ──▶ TextRank extraction ──▶ chunked prompt ──▶ local GGUF model
                   (TF-IDF + PageRank)     (≤ 2.2k chars)     (Qwen3.5, CPU)
                              │                                      │
                              ▼                                      ▼
                   verbatim fallback ◀──── grounding check ◀── summary + points
                   (timestamps kept)      (drop unsupported)
                              │
                              ▼
                        notes.md / NoteResult
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

### `LlmProvider`

```python
class LlmProvider(Protocol):
    @property
    def info(self) -> LlmInfo: ...
    @property
    def available(self) -> bool: ...
    def complete(self, messages, *, max_tokens=320, temperature=0.2, stop=None) -> str: ...
```

`llama.cpp` (a quantised GGUF model on the CPU) is the current implementation. `NullLlmProvider`
represents the disabled case, and the notes pipeline must work with either. `available` is false
when the native extension or the model file is missing; that is a normal state, not an error.

## Note generation

| Stage | Behaviour |
| --- | --- |
| Extraction | Sentences are vectorized with TF-IDF and ranked with PageRank; near-duplicates are removed. 6–28 sentences survive, depending on lecture length |
| Chunking | Selected sentences are grouped to ≤ 2.2k characters so a 4k context is never stressed |
| Rewrite | The model sees only the chunk and a fixed layout (`SUMMARY` / `POINTS` / `TERMS`); it is instructed not to add outside facts |
| Verification | Each generated line must share ≥ 34% of its content words with the transcript (≥ 25% for the summary); failures are dropped and counted |
| Timing | LLM output is mapped back to the best-matching sentence, so points keep timestamps |
| Fallback | Missing runtime/model, model errors, or an exhausted time budget return the extracted sentences verbatim |

Generated notes are therefore **conservative by construction**: the worst case is a shorter note, not
an invented one. That property is what makes a 0.8B–2B model acceptable for this task.

### Model profiles

| Profile | Trigger | Model | Download | RAM (4k ctx) |
| --- | --- | --- | --- | --- |
| `potato` | < 6.5 GB RAM or < 4 threads | Qwen3.5-0.8B Q4_K_M | 0.53 GB | ~1.3 GB |
| `balanced` | 8–16 GB RAM | Qwen3.5-2B Q4_K_M | 1.28 GB | ~2.2 GB |
| `full` | 16 GB+ RAM, 8+ threads | Qwen3.5-4B Q4_K_M | 2.74 GB | ~3.5 GB |

`ila doctor` reports the detected profile; `ILA_LLM__PROFILE` or `--profile` overrides it. Threads
default to physical cores minus one so capture and transcription keep a core. The whole run is
bounded by `ILA_LLM__BUDGET_S` (90 s), checked between chunks.

Why not a larger model: an 8B Q4 needs ~6 GB and runs at 2–3 tok/s on the target CPUs, which is
slower than simply showing the extracted sentences. The 2B model is the largest that rewrites a
short excerpt in a few seconds on a 4-core laptop.

Measured on the dev laptop (Ryzen 5 6600H, CPU-only, no GPU used), one 232-token prompt:

| Profile | Threads | Load | Generation | Peak RSS |
| --- | --- | --- | --- | --- |
| `potato` (0.8B) | 2 | 1.0 s | 30.5 tok/s (181 tok) | 0.9 GB |
| `balanced` (2B) | 5 | 1.2 s | 21.5 tok/s (184 tok) | 1.95 GB |

Thread counts are constrained to approximate a 2-core and a 4–6 core machine; a real 4 GB laptop
will be slower, but the 0.8B model leaves headroom for the OS, the browser and Whisper. Note that
the notes pipeline sends at most a few hundred prompt tokens per chunk and stops at the time budget,
so this table bounds one call, not a whole lecture.

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
5. **Note groundedness** — for each generated note, the share of content words found in the
   transcript (reported as the average support rate), plus the count of lines dropped by the
   verifier. Also report how often the extractive fallback triggered and why.
6. **Note helpfulness** — a small rubric (1–5) scored by two team members on the same three clips:
   coverage of the main ideas, correctness, and whether the timestamps land on the cited sentence.

Instrumentation already available: every run prints utterances, audio seconds, wall time and
realtime factor; `--out` writes JSONL with per-event latency and confidence.

## Offline guarantees

* Models are downloaded once into `ILA_HOME/models` and loaded with `local_files_only` when set.
* The notes model is a single GGUF file in `ILA_HOME/models/llm`; `ila download-llm` is the only
  code path that can touch the network.
* No telemetry, no remote calls at runtime; `faster-whisper` uses only local CTranslate2 inference
  and `llama.cpp` uses only local CPU inference.
* The server binds to `127.0.0.1` by default and only allows the local Vite origin.
