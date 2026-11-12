# Offline Intelligent Lecture Assistant

On-device lecture assistant for **SDG 4 (Quality Education)** — no cloud, no API keys, no internet
after setup. The repository now covers the full study loop:

1. **Caption** a live lecture or uploaded recording with local Whisper.
2. **Summarise** it into grounded, timestamped notes (TextRank + a small local LLM).
3. **Ask** syllabus questions and get an answer that cites a retrieved NCERT passage — or a
   refusal when nothing clears the threshold.
4. **Practise** with deterministic MCQs and short answers whose difficulty adapts to a per-topic
   mastery estimate stored in SQLite.

It is built for low-end Windows hardware: CPU `int8` Whisper, a 0.8B-parameter notes model floor,
pure-Python BM25 + hashed-embedding retrieval (no FAISS/MiniLM), and an explainable mastery update
instead of a trained model. The default curriculum is NCERT/CBSE Class 8–10 Science and Mathematics.

```text
mic / file ──▶ adaptive VAD ──▶ utterance segmenter ──▶ faster-whisper (local) ──▶ caption events
                (noise floor)     (roll padding,          (int8 CPU by default)     final / partial
                                   forced splits)                                   + JSONL / WebSocket
                                                                                             │
                    ┌────────────────────────────────────────────────────────────────────────┤
                    ▼                            ▼                                           ▼
             grounded notes              syllabus Q&A                             adaptive quiz
          TextRank + Qwen3.5 GGUF      BM25 + hashed vectors                 deterministic bank +
          verifier + timestamps        citations or refusal                 EMA mastery + gaps
                    └────────────────────────────┬───────────────────────────────────────────┘
                                                 ▼
                                    SQLite + React dashboard
```

## One-Click Setup & Run (Windows)

Simply double-click or run:

```cmd
install-run.bat
```

This automated script will:
1. Detect or configure your Python 3.11+ environment.
2. Install dependencies with `uv` in seconds.
3. Automatically download the local offline LLM model (~532 MB) if missing.
4. Launch the local FastAPI server and open your browser to `http://127.0.0.1:8765`.

*(PowerShell users can alternatively run `.\install-run.ps1`)*

---

## Manual Quick Start (Windows)

```powershell
uv venv --python 3.11
.\.venv\Scripts\Activate.ps1
uv pip install -e ".[dev,llm]"

# one-time model downloads, then everything runs offline
ila download-model base.en     # ~145 MB captioning model
ila download-llm                # ~1.3 GB notes model (balanced profile)

ila devices          # find your microphone index
ila live             # live captions in the terminal
```

> `llama-cpp-python` has no PyPI wheel for every platform. If the install falls back to a source
> build (CMake/MSVC errors), use the project's CPU wheel index:
>
> ```powershell
> uv pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --only-binary llama-cpp-python
> ```
>
> Without it, captions and extractive notes still work; only abstractive rewriting is disabled.

Transcribe a recorded lecture and generate notes in one pass:

```powershell
ila transcribe .\lecture.mp3 --out .\lecture.events.jsonl --text-out .\lecture.txt --notes-out .\lecture.notes.md
```

Or generate notes from an existing transcript at any time:

```powershell
ila notes .\lecture.events.jsonl --out .\lecture.notes.md   # timestamps preserved
ila notes .\lecture.txt --profile potato                    # smallest model
ila notes .\lecture.txt --no-llm                            # extractive only, no model load
```

Ask a grounded question or practise with an adaptive quiz from the terminal (both fall back to the
built-in NCERT demo when no transcript file is supplied):

```powershell
ila ask "What is the discriminant?" --class-level 10 --subject maths
ila quiz --class-level 10 --subject maths --student demo-student --length 5
```

Check what this machine can run before a demo:

```powershell
ila doctor
```

No microphone at hand? Generate a spoken fixture with the Windows speech synthesizer:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\make_test_audio.ps1
ila transcribe tests\fixtures\sample_lecture.wav
```

Serve the local API and the built React dashboard:

```powershell
ila serve            # http://127.0.0.1:8765  (dashboard, REST, /ws/captions)
```

### Troubleshooting

* **`Library cublas64_12.dll is not found`** — a CUDA GPU was detected but the CUDA 12 runtime is
  incomplete. ILA verifies the GPU with a short probe and automatically falls back to CPU. Install
  the CUDA 12 libraries or set `ILA_ASR__DEVICE=cpu` to skip the probe.
* **First run is slow** — the Whisper weights are downloaded once into `ILA_HOME/models`.
* **Captions never appear** — run `ila calibrate`; if your speech is less than ~8 dB above the
  measured noise floor, lower `ILA_VAD__START_MARGIN_DB`.
* **Notes are plain transcript sentences** — the notes model is missing or disabled. Run
  `ila doctor`, then `ila download-llm`; or accept the extractive fallback with `--no-llm`.
* **Note generation is very slow** — use `--profile potato`, lower `ILA_LLM__N_THREADS`, or reduce
  `ILA_LLM__BUDGET_S`; the pipeline falls back to extractive notes when the budget runs out.

## What is already solid

| Concern | How it is handled |
| --- | --- |
| Speech boundaries | Adaptive noise floor with hysteresis, 240 ms pre/post-roll, min-silence, min-speech and quiet-point splitting for over-long turns |
| No duplicated or flickering text | Utterances are transcribed once and finalized on pause; partials share an `utterance_id` and are replaced by the final |
| Names and jargon | Each final caption seeds the next Whisper prompt (`initial_prompt`) for spelling continuity |
| Hallucinations on silence | VAD gating **plus** a no-speech/log-probability confidence filter |
| CPU-only machines | faster-whisper with `int8`, configurable `cpu_threads`, measured realtime factor in every run |
| Testability | Segmenter, pipeline, retrieval, quiz and storage are hardware-free and covered by unit tests with synthetic audio |
| Syllabus grounding | Six NCERT Class 8–10 Science/Maths courses; chapter matching steers notes and Q&A |
| Answer safety | Extractive-first answers always cite retrieved passages; a hard score gate refuses unrelated questions |
| Quiz grounding | Every question is generated from a lecture/notes definition or statement; no invented options or answers |
| Adaptive mastery | Explainable bounded EMA per topic, difficulty recalculated after each answer, weakest-topic gaps for teachers |
| Persistence | SQLite via stdlib `sqlite3`: sessions, utterances, notes, quiz state, attempts and mastery |
| Offline deployment | Models live under `ILA_HOME`; set `ILA_ASR__LOCAL_FILES_ONLY=true` to forbid network access |

## Notes generation

Notes are **extractive-first**. TextRank picks the sentences that carry the lecture; only those
sentences are sent to the local model, in chunks that fit a 4k context. The model rewrites them into
a summary, key points and definitions, and every generated line is checked against the transcript:
unsupported lines are dropped and counted. If no model is installed, the runtime is missing, or the
time budget runs out, the selected sentences are returned verbatim with timestamps.

| Profile | Picked when | Model | Download | RAM |
| --- | --- | --- | --- | --- |
| `potato` | < 6.5 GB RAM or < 4 threads | Qwen3.5-0.8B Q4_K_M | ~0.53 GB | ~1.3 GB |
| `balanced` | 8–16 GB RAM (default) | Qwen3.5-2B Q4_K_M | ~1.28 GB | ~2.2 GB |
| `full` | 16 GB+ RAM and 8+ threads | Qwen3.5-4B Q4_K_M | ~2.74 GB | ~3.5 GB |

`ila doctor` detects the machine and reports the chosen profile. Override it with
`ila notes --profile potato` or `ILA_LLM__PROFILE=potato`. A hard time budget
(`ILA_LLM__BUDGET_S`, 90 s by default) limits the total cost per lecture; slower machines fall back
rather than making the user wait. The model file is a single GGUF under `ILA_HOME/models/llm`, and
nothing contacts the network at runtime.

Measured on the dev laptop with threads constrained to emulate a small machine: the 0.8B model with
2 threads generates at ~30 tok/s and peaks under 1 GB RSS; the 2B model with 5 threads reaches
~21 tok/s at ~2 GB. Both fit the "potato PC" target with room for Whisper alongside.

## Syllabus Q&A

Q&A is **retrieval-then-quote**, not free generation. Each final utterance, the generated notes and
the matched NCERT syllabus cards become passages in a `KnowledgeBase`. Retrieval fuses:

* BM25 over stemmed content words, and
* a 384-dimensional hashed lexical embedding (cosine similarity),

so ranking stays fast and deterministic on a CPU with no model download. The answer engine searches
lecture content only, extracts the best supporting sentence, and returns its chapter, timestamp and
retrieval score as citations. If the top passage does not clear `min_score` (0.16 by default), the
answer is a refusal with no citations. An optional local-LLM rewrite is accepted only when its
content words are supported by the retrieved excerpt.

The acceptance set contains 20 questions across all six demos. The current build cites the expected
NCERT chapter for **20/20**, and questions such as "Who won the 2011 cricket World Cup?" or "How do
you bake a chocolate cake?" are refused. Run `ila ask` or use the **Syllabus Q&A** dashboard tab.

## Adaptive quizzes

Questions are deterministic and grounded:

* definition MCQs (`Which option best defines "discriminant"?`),
* cloze MCQs built from a lecture sentence, and
* short-answer questions with keyword-based grading.

Generation filters noisy note headings, placeholders and formula fragments, so the bank is smaller
than a generic quiz generator but every item traces back to a lecture passage. Lecture questions are
preferred; master notes only top up a short bank.

Each answer updates a bounded exponential moving average for the topic:

```text
mastery ← mastery + α · (target − mastery)
```

where `target` is 1 for a correct answer and 0 for an incorrect one, and `α` grows with difficulty
and shrinks with slow responses. Mastery maps back to difficulty 1 (foundation), 2 (core) or 3
(challenge), so a correct streak raises difficulty and a wrong streak eases it.

### Knowledge Gap Diagnostics (Scikit-Learn ML Classifier)

Topic accuracy, normalized response latencies, attempts, and difficulty are evaluated using calibrated
**Decision Tree** and **Logistic Regression** classifiers (`src/ila/gaps.py`) to diagnose learning states:
- `Critical Gap` (Foundation tier, difficulty 1): severe misconception, low accuracy, or high hesitation.
- `Needs Review` (Core tier, difficulty 2): moderate understanding with retention inconsistencies.
- `Proficient` (Challenge tier, difficulty 3): fluent mastery ready for advanced HOTS problems.

### Auto-Remediation & Adaptive Feedback Loop

When a knowledge gap is diagnosed, students or teachers can launch an **Auto-Remediation Drill** (`src/ila/remediation.py`):
1. **Curriculum Concept Primer**: Generates grounded conceptual primers from NCERT textbooks using the local Qwen 3.5 LLM.
2. **Targeted Drill Items**: Produces fill-in-the-blank, true/false, short answer, and MCQ practice focusing on weak topics.
3. **Closing the Feedback Loop**: Immediate submission updates SQLite mastery with accelerated recovery credit (+0.08 remediation boost) and re-evaluates post-remediation diagnostics.

### Teacher Dashboard & SQLite Analytics

Available via the **👩‍🏫 Teacher Analytics & Gaps** dashboard tab (`/api/teacher/overview`):
- Classroom overview KPIs (total sessions, questions answered, average accuracy, response speed, class mastery).
- Topic mastery heatmap table with visual health badges (`Critical Gap`, `Needs Review`, `Proficient`).
- Individual student diagnostic drilldown with gap probabilities.
- SQLite saved lecture sessions history with metadata previews.

## Performance tuning

`int8` `base.en` on a modern laptop CPU transcribes at roughly **2–6× realtime** with beam size 5,
so finals land well under a second after a pause. Useful knobs:

```powershell
ila transcribe .\lecture.mp3 --model small.en        # better accuracy, slower
$env:ILA_ASR__COMPUTE_TYPE = "int8"
$env:ILA_ASR__BEAM_SIZE = "1"                        # fastest, slightly less accurate
$env:ILA_VAD__MIN_SILENCE_MS = "600"                 # fewer, longer captions
ila transcribe .\lecture.mp3 --no-partials           # batch mode: finals only
$env:ILA_LLM__PROFILE = "potato"                       # smallest notes model
$env:ILA_LLM__N_THREADS = "3"                          # leave a core for audio
$env:ILA_LLM__BUDGET_S = "45"                          # cap note generation time
$env:ILA_LLM__N_CTX = "2048"                           # less RAM on very small machines
```

Run `ila calibrate` in the room you will record in; it reports the measured noise floor and the
resulting speech gate.

## Configuration

Every setting is an environment variable (or `.env` entry) using `__` for nested keys:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ILA_ASR__MODEL` | `base.en` | Whisper model (`tiny.en`, `base.en`, `small.en`, `medium.en`, `large-v3`) |
| `ILA_ASR__DEVICE` | `auto` | `cpu`, `cuda`, or `auto` |
| `ILA_ASR__COMPUTE_TYPE` | `int8` | `int8`, `int8_float16`, `float16`, `float32` |
| `ILA_ASR__LANGUAGE` | `en` | Language code, or unset for auto-detect |
| `ILA_ASR__LOCAL_FILES_ONLY` | `false` | `true` guarantees no network access |
| `ILA_VAD__START_MARGIN_DB` | `8` | Speech onset threshold above the noise floor |
| `ILA_VAD__MIN_SILENCE_MS` | `450` | Silence needed to end a caption |
| `ILA_VAD__MAX_SEGMENT_S` | `20` | Hard cap before a quiet-point split |
| `ILA_PARTIALS__ENABLED` | `true` | Live preview captions |
| `ILA_LLM__ENABLED` | `true` | Set `false` for extractive-only notes |
| `ILA_LLM__PROFILE` | `auto` | `potato`, `balanced`, `full`, or `auto` (hardware detection) |
| `ILA_LLM__MODEL_PATH` | unset | Explicit GGUF file, overrides the profile |
| `ILA_LLM__BUDGET_S` | `90` | Wall-clock budget for all model calls per lecture |
| `ILA_LLM__N_CTX` | `4096` | Context window; lower saves RAM |
| `ILA_LLM__N_THREADS` | `0` | `0` = physical cores minus one |
| `ILA_CURRICULUM__CLASS_LEVEL` | `10` | Default NCERT class (8, 9 or 10) |
| `ILA_CURRICULUM__SUBJECT` | `science` | Default subject (`science` or `maths`) |
| `ILA_AUDIO__DEVICE` | system default | Microphone index from `ila devices` |
| `ILA_SERVER__PORT` | `8765` | Local API/dashboard port |
| `ILA_HOME` | `~/.ila` | Model and data directory |
| `ILA_DATA_DIR` | `ILA_HOME/data` | Sessions, notes and `ila.sqlite3` |

`ila info` prints the fully resolved configuration.

## REST API

The dashboard talks only to the local FastAPI server (`127.0.0.1:8765`):

| Endpoint | Purpose |
| --- | --- |
| `GET /api/config` | Resolved ASR/notes/retrieval/quiz/storage metadata and curriculum catalogue |
| `GET /api/demo?class_level=&subject=` | Built-in NCERT demo lecture for offline demos and Q&A/quiz fallback |
| `POST /api/notes` | Grounded notes from caption lines or plain text |
| `POST /api/transcribe` | Upload audio/video (≤ 250 MB); returns finals and optional notes |
| `GET /api/ncert-notes`, `GET /api/ncert-notes/{unit}` | Generated Class 10 Maths master notes and pages |
| `POST /api/ask` | Grounded answer with citations, or a refusal; optional saved `session_id` |
| `POST /api/quiz/start` | Build a grounded quiz and return the first adaptive question |
| `POST /api/quiz/answer` | Grade one answer, update mastery and return the next question |
| `GET /api/students/{id}/gaps` | Weakest three topics and recommended difficulty |
| `POST/GET /api/sessions`, `GET /api/sessions/{id}` | Persist and reload lecture sessions |

Request/response models live in `src/ila/server.py`; the TypeScript contracts are in
`dashboard/src/types.ts`.

## WebSocket contract

Connect to `ws://127.0.0.1:8765/ws/captions`, send one config message, then read events:

```json
{"source": "mic", "device": null, "model": "base.en", "language": "en", "partials": true}
```

```json
{"type": "caption", "kind": "final", "utterance_id": 3, "text": "Entropy measures...",
 "start": 12.4, "end": 15.1, "latency_ms": 312.5, "schema": 1}
```

Messages: `status` → `ready` → `caption`* → `done`, or `error`. Send `{"action": "stop"}` to end
early. See `src/ila/server.py` for the full protocol.

## Layout

```text
src/ila/
  audio.py        microphone + file sources, device discovery, realtime pacing
  segmenter.py    adaptive VAD, roll padding, forced-split logic (pure, unit-tested)
  asr/            provider protocol + faster-whisper implementation
  pipeline.py     source -> segmenter -> ASR -> CaptionEvent stream
  events.py       event + session-summary contract shared with the dashboard
  server.py       FastAPI REST + WebSocket transport for dashboard, Q&A and quizzes
  hardware.py     RAM/CPU detection and profile thresholds (no psutil)
  notes.py        TextRank extraction, grounded LLM prompting, verification, Markdown
  curriculum.py   six NCERT courses, chapter matching and syllabus context
  demo.py         six built-in NCERT demo lectures used for offline demos/fallback
  retrieval.py    BM25 + hashed embeddings, citations, extractive/verified answers
  quiz.py         grounded question bank, grading, adaptive mastery and gaps
  storage.py      stdlib sqlite3 schema for sessions, quiz state, attempts and mastery
  llm/            provider protocol, llama.cpp backend, GGUF catalogue and download
  cli.py          live / transcribe / notes / ask / quiz / doctor / serve / calibrate
dashboard/        React + Vite + TypeScript teacher/student dashboard
tests/            segmentation, pipeline, notes, retrieval, quiz and storage tests
docs/             architecture, roadmap and evaluation plan
```

## Tests

```powershell
uv run --extra dev python -m pytest -q
uv run --extra dev ruff check .
```

The dev extra installs pytest, ruff and httpx into the project environment. Tests never download a
model: they use fake ASR/LLM providers, synthetic audio and temporary SQLite files.

## Roadmap

- **Phase 1 (done):** streaming captioning pipeline — capture, VAD, ASR, event stream, JSONL, WebSocket.
- **Phase 2 (done):** grounded notes — TextRank extraction, local Qwen3.5 rewrite, verifier, Markdown
  export, hardware profiles, SQLite session storage and REST endpoints.
- **Phase 3 (done):** syllabus retrieval and Q&A — NCERT curriculum matching, BM25 + hashed-embedding
  fusion, passage citations, refusal below threshold, CLI and dashboard.
- **Phase 4 (done):** grounded quizzes, adaptive difficulty, per-topic mastery and weakest-topic gaps,
  persisted in SQLite.
- **Phase 5 (in progress):** React dashboard with live captions, notes reader, Q&A and quiz views;
  one-click Windows install; packaging and end-to-end verification on the low-end target machine.

See `docs/architecture.md` for the contracts each phase must honour and `docs/roadmap.md` for the
12-week plan from the Phase-I review.
