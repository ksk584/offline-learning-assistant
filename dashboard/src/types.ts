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
