# Offline Intelligent Lecture Assistant

On-device lecture assistant for **SDG 4 (Quality Education)** — no cloud, no API keys, no internet
after setup. Phase 1 (this repo, today) is the **captioning pipeline**: capture audio, find speech
boundaries, transcribe locally with Whisper, and stream caption events.

Planned phases build on the same event stream: structured notes (TextRank), syllabus-aware Q&A
(MiniLM + FAISS), adaptive quizzes (scikit-learn), all shown in a React teacher dashboard.

```text
mic / file ──▶ adaptive VAD ──▶ utterance segmenter ──▶ faster-whisper (local) ──▶ caption events
                (noise floor)     (roll padding,          (int8 CPU by default)     final / partial
                                   forced splits)                                   + JSONL / WebSocket
```

## Quick start (Windows, ~5 minutes after the model download)

```powershell
uv venv --python 3.11
.\.venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"

# one-time model download (~145 MB for base.en), then everything runs offline
ila download-model base.en
ila devices          # find your microphone index
ila live             # live captions in the terminal
```

Transcribe a recorded lecture (wav / mp3 / mp4 — anything PyAV can decode):

```powershell
ila transcribe .\lecture.mp3 --out .\lecture.events.jsonl --text-out .\lecture.txt
```

Serve the local API for the future dashboard:

```powershell
ila serve            # http://127.0.0.1:8765  (WebSocket: /ws/captions)
```

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

## Performance tuning

`int8` `base.en` on a modern laptop CPU transcribes at roughly **2–6× realtime** with beam size 5,
so finals land well under a second after a pause. Useful knobs:

```powershell
ila transcribe .\lecture.mp3 --model small.en        # better accuracy, slower
$env:ILA_ASR__COMPUTE_TYPE = "int8"
$env:ILA_ASR__BEAM_SIZE = "1"                        # fastest, slightly less accurate
$env:ILA_VAD__MIN_SILENCE_MS = "600"                 # fewer, longer captions
ila transcribe .\lecture.mp3 --no-partials           # batch mode: finals only
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
  cli.py          live / transcribe / serve / devices / models / calibrate
tests/            segmentation and pipeline tests with synthetic speech-like audio
docs/             architecture, roadmap and evaluation plan
```

## Tests

```powershell
uv run pytest
uv run ruff check .
```

Tests never download a model: they use a fake ASR provider and synthetic audio.

## Roadmap

- **Phase 1 (now):** streaming captioning pipeline — capture, VAD, ASR, event stream, JSONL, WebSocket.
- **Phase 2:** note generation (TextRank + keyword extraction) stored in SQLite.
- **Phase 3:** syllabus parsing, MiniLM embeddings + FAISS, retrieval-augmented Q&A.
- **Phase 4:** quiz generation, topic-wise gap tracking (scikit-learn), adaptive difficulty.
- **Phase 5:** React teacher dashboard wired to `/ws/captions` + REST endpoints; packaging.

See `docs/architecture.md` for the contracts each phase must honour and `docs/roadmap.md` for the
12-week plan from the Phase-I review.
