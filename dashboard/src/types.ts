export interface AsrInfo {
  engine: string;
  model: string;
  device: string;
  compute_type: string;
}

export interface ChapterSummary {
  number: number;
  title: string;
}

export interface CourseCatalogue {
  class_level: number;
  subject: string;
  label: string;
  chapters: ChapterSummary[];
}

export interface DemoSummary {
  id: string;
  title: string;
  class_level: number;
  subject: string;
  chapter: string;
}

export interface AppConfig {
  version: string;
  schema: number;
  offline: boolean;
  asr: {
    model: string;
    language: string | null;
    device: string;
    compute_type: string;
    model_dir: string;
    local_files_only: boolean;
  };
  notes: {
    enabled: boolean;
    profile: string;
    profile_requested: string;
    available: boolean;
    model: string;
    path: string;
    size_mb: number;
    download_gb: number;
    ram_gb: number;
    note: string;
    budget_s: number;
    threads: number;
    selectable: string[];
  };
  hardware: {
    summary: string;
    ram_gb: number;
    logical_cores: number;
    physical_cores: number;
    platform: string;
    suggested_profile: string;
    reason: string;
  };
  curriculum: {
    class_levels: number[];
    subjects: string[];
    subject_labels: Record<string, string>;
    default_class_level: number;
    default_subject: string;
    auto_match: boolean;
    courses: CourseCatalogue[];
    demos: DemoSummary[];
  };
  retrieval: {
    engine: string;
    fusion: string;
    embedding_dim: number;
    offline: boolean;
    answers: string;
  };
  quiz: {
    engine: string;
    mastery: string;
    kinds: string[];
    adaptive: boolean;
  };
  storage: {
    engine: string;
    path: string;
  };
  server: {
    host: string;
    port: number;
    dashboard_built: boolean;
  };
}

export interface DemoLine {
  text: string;
  start: number;
  end: number;
}

export interface DemoLecture {
  id: string;
  title: string;
  class_level: number;
  subject: string;
  chapter: string;
  lines: DemoLine[];
  exact: boolean;
}

export interface NotePoint {
  text: string;
  start: number | null;
  source: "llm" | "extractive" | string;
}

export interface NoteDefinition {
  term: string;
  text: string;
  start: number | null;
}

export interface ChapterMatch {
  number: number;
  title: string;
  score: number;
  matched_terms: string[];
}

export interface SyllabusContext {
  class_level: number;
  subject: string;
  subject_label: string;
  course: string;
  matches: ChapterMatch[];
}

export interface NotesResult {
  title: string;
  summary: string;
  points: NotePoint[];
  definitions: NoteDefinition[];
  keywords: string[];
  used_llm: boolean;
  profile: string;
  model: string | null;
  dropped: number;
  latency_s: number;
  fallback_reason: string | null;
  sentences: number;
  curriculum: SyllabusContext | null;
}

export interface NotesResponse {
  notes: NotesResult;
  markdown: string;
}

export interface TranscribeResponse {
  lines: DemoLine[];
  transcript: string;
  duration_s: number;
  asr: AsrInfo;
  notes: NotesResult | null;
  markdown: string | null;
  notes_error: string | null;
}

export interface CaptionLine {
  id: number;
  text: string;
  start: number;
  end: number;
  latencyMs?: number | null;
}

export type CaptionPhase =
  | "idle"
  | "connecting"
  | "loading"
  | "live"
  | "done"
  | "error";

export interface NcertPage {
  page_number: number;
  section_id: string;
  title: string;
  content: string;
  words: number;
}

export interface NcertNoteDetail {
  unit: number;
  title: string;
  markdown: string;
  notes: NotesResult;
  total_pages: number;
  pages: NcertPage[];
}

// ------------------------------------------------------------------ Q&A
export interface Citation {
  id: string;
  source: string;
  title: string;
  chapter_number: number | null;
  chapter_title: string | null;
  start: number | null;
  end: number | null;
  score: number;
  snippet: string;
}

export interface AnswerTopic {
  chapter_number: number;
  chapter_title: string | null;
  score: number;
}

export interface AnswerSource {
  kind: "demo" | "transcript" | "session" | string;
  title: string;
  session_id?: string | null;
  demo_id?: string;
  exact?: boolean;
  lines?: number;
  course?: string | null;
  text?: string;
}

export interface AskResponse {
  question: string;
  answer: string;
  answerable: boolean;
  confidence: number;
  citations: Citation[];
  topics: AnswerTopic[];
  engine: string;
  latency_s: number;
  source: AnswerSource;
  course: string | null;
  chapter_matches: ChapterMatch[];
}

// --------------------------------------------------------------- quizzes
export interface QuizQuestion {
  id: string;
  kind: "mcq" | "short";
  prompt: string;
  options: string[];
  difficulty: number;
  topic: string;
  chapter_number: number | null;
  chapter_title: string | null;
  source: string;
  start: number | null;
  end: number | null;
}

export interface MasteryRow {
  topic: string;
  mastery: number;
  attempts: number;
  correct: number;
}

export interface QuizProgress {
  answered: number;
  total: number;
  correct: number;
  score: number;
}

export interface QuizStartResponse {
  quiz_id: string;
  student_id: string;
  class_level: number;
  subject: string;
  topic: string | null;
  total: number;
  question: QuizQuestion;
  progress: QuizProgress;
  mastery: MasteryRow[];
  source: AnswerSource;
  topics: string[];
}

export interface Gap {
  topic: string;
  mastery: number;
  attempts: number;
  correct: number;
  recommended_difficulty: number;
  tier?: "critical_gap" | "needs_review" | "proficient";
  tier_label?: string;
  gap_probability?: number;
  model_name?: string;
  diagnostic_reasons?: string[];
  avg_response_ms?: number;
}

export interface GapsResponse {
  student_id: string;
  gaps: Gap[];
  attempts: number;
  overall: number;
}

export interface QuizAnswerResponse {
  quiz_id: string;
  question_id: string;
  correct: boolean;
  expected: string;
  response: string;
  feedback: string;
  explanation: string;
  evaluation_reason?: string;
  evaluator?: string;
  topic: string;
  difficulty: number;
  mastery: MasteryRow & { student_id: string; updated_at: string };
  progress: QuizProgress;
  next_question: QuizQuestion | null;
  completed: boolean;
  target_difficulty: number;
  gaps: GapsResponse;
}

// ----------------------------------------------------------- Auto-Remediation
export type RemediationKind = "cloze" | "true_false" | "short_answer" | "mcq";

export interface KnowledgeGapDiagnosis {
  topic: string;
  mastery: number;
  accuracy: number;
  attempts: number;
  correct: number;
  avg_response_ms: number;
  avg_response_s: number;
  tier: "critical_gap" | "needs_review" | "proficient";
  tier_label: string;
  gap_probability: number;
  recommended_difficulty: number;
  remediation_priority: number;
  model_name: string;
  diagnostic_reasons: string[];
}

export interface RemediationItem {
  id: string;
  kind: RemediationKind;
  prompt: string;
  options: string[];
  topic: string;
  difficulty: number;
  primer: string;
  source: string;
}

export interface RemediationPack {
  pack_id: string;
  student_id: string;
  topic: string;
  primer: string;
  total_items: number;
  items: RemediationItem[];
  diagnosis: KnowledgeGapDiagnosis | null;
  source: string;
}

export interface RemediationAnswerResult {
  correct: boolean;
  expected: string;
  submitted?: string;
  feedback: string;
  explanation: string;
  evaluation_reason?: string;
  evaluator?: string;
  topic: string;
  difficulty: number;
  prev_mastery: number;
  updated_mastery: number;
  post_diagnosis: KnowledgeGapDiagnosis;
}

// ---------------------------------------------------------- Teacher Dashboard
export interface TeacherTopic {
  topic: string;
  attempts: number;
  correct: number;
  accuracy: number;
  avg_response_ms: number;
}

export interface TeacherRecentSession {
  id: string;
  created_at: string;
  title: string;
  class_level: number;
  subject: string;
  duration_s: number | null;
}

export interface TeacherOverview {
  total_sessions: number;
  total_attempts: number;
  total_students: number;
  overall_accuracy: number;
  avg_response_ms: number;
  class_mastery_avg: number;
  topics: TeacherTopic[];
  recent_sessions: TeacherRecentSession[];
}

export interface TeacherStudentDetail {
  student_id: string;
  gaps: (Gap & {
    tier?: string;
    tier_label?: string;
    gap_probability?: number;
    model_name?: string;
    diagnostic_reasons?: string[];
  })[];
  overall: number;
  attempts: number;
  classifier_model: string;
  mastery: MasteryRow[];
  recent_attempts: {
    id: string;
    topic: string;
    correct: boolean;
    difficulty: number;
    response_ms: number;
    created_at: string;
  }[];
}
