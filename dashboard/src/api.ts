import type {
  AppConfig,
  DemoLecture,
  DemoLine,
  NcertNoteDetail,
  NotesResponse,
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
