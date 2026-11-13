import type {
  AppConfig,
  AskResponse,
  DemoLecture,
  DemoLine,
  GapsResponse,
  NcertNoteDetail,
  NotesResponse,
  QuizAnswerResponse,
  QuizStartResponse,
  RemediationAnswerResult,
  RemediationPack,
  StoredLectureNotesResponse,
  TeacherOverview,
  TeacherStudentDetail,
  TranscribeResponse,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let detail = response.statusText || `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string; message?: string };
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // Keep the status text when the body is not JSON.
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export function getConfig(): Promise<AppConfig> {
  return request<AppConfig>("/api/config");
}

export function getDemo(classLevel: number, subject: string): Promise<DemoLecture> {
  const params = new URLSearchParams({
    class_level: String(classLevel),
    subject,
  });
  return request<DemoLecture>(`/api/demo?${params.toString()}`);
}

export interface NotesRequest {
  lines: DemoLine[];
  title: string;
  class_level: number;
  subject: string;
  profile: string;
  use_llm: boolean;
  use_syllabus?: boolean;
}

export function createNotes(payload: NotesRequest): Promise<NotesResponse> {
  return request<NotesResponse>("/api/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export interface TranscribeOptions {
  classLevel: number;
  subject: string;
  profile: string;
  useLlm: boolean;
}

export function transcribeFile(
  file: File,
  options: TranscribeOptions,
): Promise<TranscribeResponse> {
  const body = new FormData();
  body.append("file", file);
  body.append("class_level", String(options.classLevel));
  body.append("subject", options.subject);
  body.append("profile", options.profile);
  body.append("use_llm", String(options.useLlm));
  return request<TranscribeResponse>("/api/transcribe", {
    method: "POST",
    body,
  });
}

export interface NcertNoteItem {
  unit: number;
  title: string;
  chapter: number;
  filename: string;
  words: number;
  pages: number;
}

export function getNcertNotesList(): Promise<NcertNoteItem[]> {
  return request<NcertNoteItem[]>("/api/ncert-notes");
}

export function getNcertUnitNote(unit: number): Promise<NcertNoteDetail> {
  return request<NcertNoteDetail>(`/api/ncert-notes/${unit}`);
}

// ------------------------------------------------------------------- Q&A
export interface AskOptions {
  question: string;
  lines?: DemoLine[];
  classLevel: number;
  subject: string;
  chapter?: number | null;
  topK?: number;
  useLlm?: boolean;
  profile?: string;
}

export function askQuestion(options: AskOptions): Promise<AskResponse> {
  return request<AskResponse>("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: options.question,
      lines: options.lines ?? [],
      class_level: options.classLevel,
      subject: options.subject,
      chapter: options.chapter ?? null,
      top_k: options.topK ?? 5,
      use_llm: options.useLlm ?? true,
      profile: options.profile ?? "potato",
    }),
  });
}

// ---------------------------------------------------------------- quizzes
export interface StartQuizOptions {
  studentId: string;
  classLevel: number;
  subject: string;
  topic?: string | null;
  length?: number;
  difficulty?: number | null;
  lines?: DemoLine[];
}

export function startQuiz(options: StartQuizOptions): Promise<QuizStartResponse> {
  return request<QuizStartResponse>("/api/quiz/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      student_id: options.studentId,
      class_level: options.classLevel,
      subject: options.subject,
      topic: options.topic ?? null,
      length: options.length ?? 5,
      difficulty: options.difficulty ?? null,
      lines: options.lines ?? [],
    }),
  });
}

export interface AnswerQuizOptions {
  quizId: string;
  questionId: string;
  answer?: string;
  answerIndex?: number | null;
  responseMs?: number | null;
}

export function answerQuiz(options: AnswerQuizOptions): Promise<QuizAnswerResponse> {
  return request<QuizAnswerResponse>("/api/quiz/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      quiz_id: options.quizId,
      question_id: options.questionId,
      answer: options.answer ?? "",
      answer_index: options.answerIndex ?? null,
      response_ms: options.responseMs ?? null,
    }),
  });
}

export function getGaps(studentId: string, limit = 3): Promise<GapsResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return request<GapsResponse>(
    `/api/students/${encodeURIComponent(studentId)}/gaps?${params.toString()}`,
  );
}

// ----------------------------------------------------------- Auto-Remediation
export interface GenerateRemediationOptions {
  studentId: string;
  topic?: string | null;
  classLevel?: number;
  subject?: string;
  count?: number;
  lines?: DemoLine[];
}

export function generateRemediation(options: GenerateRemediationOptions): Promise<RemediationPack> {
  return request<RemediationPack>("/api/remediation/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      student_id: options.studentId,
      topic: options.topic ?? null,
      class_level: options.classLevel,
      subject: options.subject,
      count: options.count ?? 3,
      lines: options.lines ?? [],
    }),
  });
}

export interface SubmitRemediationOptions {
  packId: string;
  studentId: string;
  itemId: string;
  answer: string;
  selectedIndex?: number | null;
  responseMs?: number;
}

export function submitRemediation(options: SubmitRemediationOptions): Promise<RemediationAnswerResult> {
  return request<RemediationAnswerResult>("/api/remediation/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pack_id: options.packId,
      student_id: options.studentId,
      item_id: options.itemId,
      answer: options.answer,
      selected_index: options.selectedIndex ?? null,
      response_ms: options.responseMs ?? 4000,
    }),
  });
}

// ---------------------------------------------------------- Teacher Dashboard
export function getTeacherOverview(): Promise<TeacherOverview> {
  return request<TeacherOverview>("/api/teacher/overview");
}

export function getTeacherStudents(): Promise<{ students: string[] }> {
  return request<{ students: string[] }>("/api/teacher/students");
}

export function getTeacherStudentDetail(studentId: string): Promise<TeacherStudentDetail> {
  return request<TeacherStudentDetail>(`/api/teacher/students/${encodeURIComponent(studentId)}`);
}

export function getStoredLectureNotes(
  chapterNumber: number,
  classLevel: number = 10,
  subject: string = "maths",
): Promise<StoredLectureNotesResponse> {
  const params = new URLSearchParams({
    class_level: String(classLevel),
    subject,
  });
  return request<StoredLectureNotesResponse>(`/api/lecture-notes/${chapterNumber}?${params.toString()}`);
}
