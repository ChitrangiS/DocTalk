
export interface UploadResponse {
  doc_id:      string;
  filename:    string;
  page_count:  number;
  chunk_count: number;
  message:     string;
}

export interface DeleteResponse {
  doc_id:  string;
  message: string;
}

// ── Chat ─────────────────────────────────────────────────────────────

export interface SourceChunk {
  page:    number;
  excerpt: string;
  score:   number;
}

// ── API error ────────────────────────────────────────────────────────

export interface ApiError {
  detail: string | { msg: string; type: string }[];
  status: number;
}

// ── Upload state machine ─────────────────────────────────────────────
// Used by UploadZone to track progress through the upload lifecycle.

export type UploadStatus =
  | "idle"        // no file selected
  | "validating"  // client-side validation running
  | "uploading"   // POST /upload/ in-flight
  | "success"     // doc_id received, ready to chat
  | "error";      // something went wrong

export interface UploadState {
  status:    UploadStatus;
  file:      File | null;
  response:  UploadResponse | null;
  error:     string | null;
}

// ── Chat state machine ───────────────────────────────────────────────
// Used by ChatWindow (Day 7).

export type ChatStatus = "idle" | "streaming" | "done" | "error";

export interface ChatMessage {
  id:      string;
  role:    "user" | "assistant";
  content: string;
  sources: SourceChunk[];
  status:  ChatStatus;
}