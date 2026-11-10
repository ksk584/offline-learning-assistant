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

- Store finals in SQLite (`sessions`, `utterances`).
- TextRank extractive summarization over each session; keyword extraction (TF-IDF / YAKE).
- Markdown note export: summary, key points, keywords, timestamps linking back to utterances.
- API: `GET /api/sessions`, `GET /api/sessions/{id}/notes`.

**Acceptance:** a 50-minute lecture yields notes a student can revise from, with no invented
content (extractive only), plus timestamps that jump to the right utterance.

## Phase 3 — Syllabus retrieval and Q&A (weeks 7–8)

- Parse the course syllabus (PDF/docx) into `topics` with codes and descriptions.
- Embed syllabus chunks and lecture notes with MiniLM (ONNX runtime, CPU) into FAISS.
- Hybrid retrieval: dense (FAISS) + lexical (BM25) with score fusion; cosine threshold tuning.
- Q&A: retrieve → answer with a small local model or extractive answer span; always cite sources.
- API: `POST /api/ask {session_id?, topic_code?, question}`.

**Acceptance:** 20-question evaluation set; ≥80% of answers cite the correct syllabus topic; no
answer without a retrieved source above the confidence threshold.

## Phase 4 — Quizzes and adaptive remediation (weeks 9–10)

- Question bank seeded from topics + notes (MCQ + short answer), stored in `questions`.
- Quiz session flow with local attempts log (correctness, attempts, response time, difficulty).
- Topic-wise mastery estimate; decision tree / logistic regression over the attempt features.
- Adaptive difficulty + targeted practice generation for weak topics.
- API: `POST /api/quiz/start`, `POST /api/quiz/answer`, `GET /api/students/{id}/gaps`.

**Acceptance:** mastery estimates change in the expected direction on a scripted answer pattern;
quiz difficulty adapts; teacher view lists the three weakest topics per student.

## Phase 5 — Dashboard and packaging (weeks 11–12)

- React + Vite dashboard: live caption pane (WebSocket), session list, notes viewer, Q&A panel,
  quiz builder, class-level gap heatmap.
- End-to-end test on the low-end target machine, fully offline.
- Installer/packaging: one command to launch backend + bundled frontend; model prefetch script.
- Report, demo script, and journal paper draft (Scopus submission per the review plan).

**Acceptance:** cold start to first caption under 30 s on the target machine with no network, and a
complete teacher workflow demo without a terminal.

## Immediate next actions

1. Record a 10-minute lecture with the intended microphone; run
   `ila transcribe lecture.wav --out events.jsonl`.
2. Hand-correct that clip for a WER baseline (`base.en` vs `small.en`).
3. Decide the Phase 2 SQLite schema details with the team (session boundaries, course ids).
4. Set up the React app (`npm create vite@latest dashboard -- --template react-ts`) against
   `/ws/captions` with mock data first.
