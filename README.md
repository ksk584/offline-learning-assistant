# Offline Intelligent Lecture Assistant

On-device lecture assistant for **SDG 4 (Quality Education)** — no cloud, no API keys, no internet
after setup. Phase 1 (this repo, today) is the **captioning pipeline**: capture audio, find speech
boundaries, transcribe locally with Whisper, and stream caption events.

Planned phases build on the same event stream: structured notes (TextRank + a small local
LLM), syllabus-aware Q&A (MiniLM + FAISS), adaptive quizzes (scikit-learn), all shown in a React
teacher dashboard.

```text
mic / file ──▶ adaptive VAD ──▶ utterance segmenter ──▶ faster-whisper (local) ──▶ caption events
                (noise floor)     (roll padding,          (int8 CPU by default)     final / partial
                                   forced splits)                                   + JSONL / WebSocket
                                                                                            │
                                              notes ──▶ grounded local LLM ◀── TextRank ◀──┘
                                              (.md)     (Qwen3.5 GGUF, CPU)     (extractive)
```

## Quick start (Windows, ~5 minutes after the model download)

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

Check what this machine can run before a demo:

```powershell
ila doctor
```

No microphone at hand? Generate a spoken fixture with the Windows speech synthesizer:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\make_test_audio.ps1
ila transcribe tests\fixtures\sample_lecture.wav
```

Serve the local API for the future dashboard:

```powershell
ila serve            # http://127.0.0.1:8765  (WebSocket: /ws/captions)
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
| Testability | Segmenter and pipeline are hardware-free and covered by unit tests with synthetic audio |
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
| `ILA_AUDIO__DEVICE` | system default | Microphone index from `ila devices` |
| `ILA_HOME` | `~/.ila` | Model and data directory |

`ila info` prints the fully resolved configuration.

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
  server.py       FastAPI + WebSocket transport
  hardware.py     RAM/CPU detection and profile thresholds (no psutil)
  notes.py        TextRank extraction, grounded LLM prompting, verification, Markdown
  llm/            provider protocol, llama.cpp backend, GGUF catalogue and download
  cli.py          live / transcribe / notes / doctor / serve / models / calibrate
tests/            segmentation, pipeline, notes and hardware tests (no model downloads)
docs/             architecture, roadmap and evaluation plan
```

## Tests

```powershell
uv run pytest
uv run ruff check .
```

Tests never download a model: they use fake ASR/LLM providers and synthetic audio.

## Roadmap

- **Phase 1 (done):** streaming captioning pipeline — capture, VAD, ASR, event stream, JSONL, WebSocket.
- **Phase 2 (in progress):** note generation — TextRank extraction + grounded local LLM, Markdown
  export; SQLite storage and REST endpoints next.
- **Phase 3:** syllabus parsing, MiniLM embeddings + FAISS, retrieval-augmented Q&A.
- **Phase 4:** quiz generation, topic-wise gap tracking (scikit-learn), adaptive difficulty.
- **Phase 5:** React teacher dashboard wired to `/ws/captions` + REST endpoints; packaging.

See `docs/architecture.md` for the contracts each phase must honour and `docs/roadmap.md` for the
12-week plan from the Phase-I review.
