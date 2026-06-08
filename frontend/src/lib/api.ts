
import type {
  ApiError,
  DeleteResponse,
  UploadResponse,
} from "./types";

// API base URL from environment variable (embedded at build time by Next.js)
// NEXT_PUBLIC_* variables are statically replaced during build
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://doctalk-production-c6af.up.railway.app";

if (!process.env.NEXT_PUBLIC_API_BASE_URL && typeof window !== "undefined") {
  console.warn(
    "Warning: NEXT_PUBLIC_API_BASE_URL was not set during build. " +
    "Using fallback: " + BASE_URL
  );
}

// ── Error handling helper ────────────────────────────────────────────

async function parseError(res: Response): Promise<ApiError> {  let detail = `HTTP ${res.status}: ${res.statusText}`;
  try {
    const body = await res.json();
    // FastAPI validation errors return { detail: [{msg, type}] }
    // Other errors return { detail: "string" }
    if (typeof body.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      detail = body.detail.map((e: { msg: string }) => e.msg).join(", ");
    }
  } catch {
    // Response body was not JSON — use the status text fallback above
  }
  return { detail, status: res.status };
}

// ── Upload ───────────────────────────────────────────────────────────

export const uploadPDF = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/upload/`, {
    method: "POST",
    body: formData,
  });

  return res.json();
};

export async function uploadPdf(
  file: File,
  onProgress?: (phase: "uploading" | "processing") => void,
): Promise<UploadResponse> {
  // Build multipart form data — required for binary file upload.
  // application/json cannot carry binary blobs efficiently.
  const form = new FormData();
  form.append("file", file);

  onProgress?.("uploading");

  const res = await fetch(`${BASE_URL}/upload/`, {
    method: "POST",
    body:   form,
    // Do NOT set Content-Type manually — the browser sets it automatically
    // with the correct multipart boundary. Setting it manually breaks the upload.
  });

  if (!res.ok) {
    const err = await parseError(res);
    throw err;
  }

  onProgress?.("processing");
  return res.json() as Promise<UploadResponse>;
}

// ── Delete document ──────────────────────────────────────────────────

export async function deleteDocument(docId: string): Promise<DeleteResponse> {
  const res = await fetch(`${BASE_URL}/upload/${encodeURIComponent(docId)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await parseError(res);
    throw err;
  }
  return res.json() as Promise<DeleteResponse>;
}

// ── Chat streaming ───────────────────────────────────────────────────

/**
 * Start a streaming chat request.
 *
 * Returns a ReadableStream of raw SSE bytes.
 * The caller (ChatWindow, Day 7) is responsible for parsing the stream.
 *
 * SSE event format from the backend:
 *   data: {token}\n\n        — answer token
 *   data: [SOURCES]{json}\n\n — citation data
 *   data: [DONE]\n\n          — stream end
 *
 * Throws ApiError if the request fails before the stream starts.
 * Mid-stream errors are yielded as error SSE events by the backend.
 */
export async function streamChat(
  docId:    string,
  question: string,
): Promise<ReadableStream> {
  const res = await fetch(`${BASE_URL}/chat/`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ doc_id: docId, question }),
  });

  if (!res.ok) {
    const err = await parseError(res);
    throw err;
  }

  if (!res.body) {
    throw { detail: "Response body is null — SSE stream unavailable.", status: 500 } as ApiError;
  }

  return res.body;
}

// ── Health check ─────────────────────────────────────────────────────

export async function checkHealth(): Promise<{
  status: string;
  version: string;
  vector_store: { total_vectors: number };
}> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

// ── SSE stream parser ────────────────────────────────────────────────

/**
 * Parse a ReadableStream of SSE bytes into discrete event payloads.
 * Used by ChatWindow (Day 7).
 *
 * Yields event payload strings (without the "data: " prefix or trailing \n).
 * Stops when [DONE] is encountered.
 *
 * Usage:
 *   const stream = await streamChat(docId, question);
 *   for await (const event of parseSseStream(stream)) {
 *     if (event.startsWith('[SOURCES]')) { ... }
 *     else if (event === '[DONE]')       { break; }
 *     else                               { appendToken(event); }
 *   }
 */
export async function* parseSseStream(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<string> {
  const reader  = stream.getReader();
  const decoder = new TextDecoder();
  let   buffer  = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are delimited by double newlines.
      const parts = buffer.split("\n\n");
      // Everything except the last part is a complete event.
      // The last part is an incomplete event — keep it in the buffer.
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data: ")) continue;

        const payload = line.slice("data: ".length);
        yield payload;

        if (payload === "[DONE]") return;
      }
    }
  } finally {
    reader.releaseLock();
  }
}