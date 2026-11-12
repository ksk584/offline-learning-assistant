# Roadmap

Mapped to the Phase-I review timeline (12 weeks). Each phase has an acceptance check so progress is
verifiable rather than "mostly done".

## Phase 1 — Captioning pipeline (weeks 3–4 of the review plan, started early)

- [x] Repo scaffold, config, CLI, local WebSocket transport
- [x] Adaptive VAD + utterance segmentation with roll padding and forced splits
- [x] faster-whisper integration behind an `AsrProvider` interface
- [x] Caption event contract (final/partial), JSONL export, confidence filtering
- [x] Unit tests with synthetic audio; no model needed in CI
- [ ] Baseline measurement on a real 10-minute lecture clip (WER, latency, realtime factor)
- [ ] Threshold tuning on two rooms / two microphones

**Acceptance:** live captions appear within ~1 s of a pause, no duplicated text across three
repeated 5-minute sessions, and a WER number recorded in `docs/architecture.md`.

## Phase 2 — Note generation (weeks 5–6)

- [x] TextRank extractive summarization over each session; keyword extraction (TF-IDF).
- [x] Grounded local LLM rewrite behind an `LlmProvider` (llama.cpp GGUF, CPU-only).
- [x] Hardware profiles (`potato` / `balanced` / `full`) with 0.8B / 2B / 4B Qwen3.5 models.
- [x] Verification pass: unsupported generated lines are dropped and counted; extractive fallback.
- [x] Markdown note export: summary, key points, terms, keywords, timestamps linking to utterances.
- [ ] Store finals in SQLite (`sessions`, `utterances`) and notes in `notes`.
- [ ] API: `GET /api/sessions`, `GET /api/sessions/{id}/notes`.
- [ ] Benchmark the three profiles on the target machine and record tokens/s and peak RSS.

**Acceptance:** a 50-minute lecture yields notes a student can revise from. Every generated point is
supported by the transcript (verifier drop rate recorded), and timestamps jump to the right
utterance. On a machine without a model the same run still returns timestamped extractive notes
instead of failing.

**Measured on the dev laptop (6C/12T, 15.2 GB):** the 2B Q4_K_M loads in ~1.2 s, rewrites one
232-token prompt at ~21 tok/s and peaks at ~1.95 GB RSS; the 0.8B model with 2 threads reaches
~30 tok/s at ~0.9 GB. See `docs/architecture.md` for the profile table and evaluation protocol.

## Phase 3 — Syllabus retrieval and Q&A (weeks 7–8) — done

- [x] Parse the NCERT catalogue into six courses (Class 8–10 Science and Mathematics) with chapter
      titles, keywords and transcript matching (`curriculum.py`).
- [x] Build passages from finals, generated notes and syllabus cards with chapter/timestamp
      provenance (`retrieval.py`).
- [x] Hybrid retrieval: BM25 + 384-dim hashed lexical embeddings with score fusion and term coverage.
      Chosen over MiniLM/FAISS to keep the install offline and CPU-only; the embedder interface is
      swappable for ONNX later.
- [x] Q&A: extractive answer quoted from the top passage, always cited; a hard `min_score` gate
      refuses unrelated questions. Optional local-LLM rewrite is accepted only when its content words
      are supported by the retrieved excerpt.
- [x] API: `POST /api/ask` with transcript/session/demo fallback; CLI `ila ask`; dashboard Q&A tab.

**Acceptance met:** the 20-question set across all six demos cites the expected NCERT chapter
**20/20** (target ≥ 80%), and off-syllabus questions return no citations instead of an answer.

## Phase 4 — Quizzes and adaptive remediation (weeks 9–10) — done

- [x] Deterministic question bank seeded from lecture definitions, cloze sentences and short answers;
      master notes only top up a short bank. No invented content (`quiz.py`).
- [x] Quiz session flow with an append-only attempts log (correctness, response time, difficulty).
- [x] Topic-wise mastery via an explainable bounded EMA per `(student, topic)`; chosen over a
      decision tree/logistic regression so the update is inspectable and needs no training data.
- [x] Adaptive difficulty recomputed after every answer; `gaps` returns the three weakest topics with
      a recommended practice difficulty.
- [x] API: `POST /api/quiz/start`, `POST /api/quiz/answer`, `GET /api/students/{id}/gaps`; CLI
      `ila quiz`; dashboard quiz tab; SQLite persistence.

**Acceptance met:** an all-correct scripted run raises mastery ≈ 0.50 → ≈ 0.98 with difficulty
2 → 3; an all-wrong run lowers mastery and eases difficulty to 1; `gaps` lists the three weakest
topics per student.

## Phase 5 — Dashboard and packaging (weeks 11–12) — in progress

- [x] React + Vite dashboard: live caption pane (WebSocket), demo replay, upload, notes viewer and
      NCERT master-notes reader.
- [x] Q&A panel (citations, refusal state, confidence) and quiz panel (setup, MCQ/short answer,
      mastery bars, weakest topics).
- [x] One-click Windows launcher (`install-run.bat` / `install-run.ps1`) plus `ila serve` for the
      built dashboard and API.
- [x] REST + config metadata for retrieval, quiz and storage; dashboard auto-falls back to the
      selected NCERT demo when no live transcript exists.
- [ ] End-to-end timing on the low-end target machine, fully offline.
- [ ] Class-level gap heatmap and a session replay view.
- [ ] Report, demo script, and journal paper draft (Scopus submission per the review plan).

**Acceptance:** cold start to first caption under 30 s on the target machine with no network, and a
complete teacher workflow demo without a terminal.

## Verification snapshot

* `uv run --extra dev python -m pytest -q` — **132 tests pass** (segmentation, pipeline, notes,
  retrieval, quiz, storage and server include Q&A/quiz/multi-user coverage).
* `uv run --extra dev ruff check .` — clean.
* `npm run build` in `dashboard/` — clean TypeScript build.
* Live server smoke test: demo and transcript Q&A, refusal, quiz start/answer, mastery update, gaps,
  and dashboard HTML/JS/CSS all return 200.

## Immediate next actions

1. Install on the low-end target machine and record cold start → first caption, plus peak RSS while
   Whisper, notes and the quiz run.
2. Record a 10-minute lecture with the intended microphone; hand-correct it for a WER baseline
   (`base.en` vs `small.en`) and add the result to `docs/architecture.md`.
3. Run `ila notes`, `ila ask` and `ila quiz` on that clip; score notes with the rubric and record the
   verifier drop rate and fallback frequency.
4. Add the class-level gap heatmap and a saved-session replay view to the dashboard.
5. Expand the generated master notes beyond Class 10 Maths Units 1–3 so quiz banks have a wider
   grounded pool.
6. Draft the report/demo script and the Scopus paper from the evaluation tables.
