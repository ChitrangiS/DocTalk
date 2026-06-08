"use client";

import { useCallback, useRef, useState } from "react";
import type { UploadResponse } from "../lib/types";

// ── Types ──────────────────────────────────────────────────────

export type UploadPhase =
  | "idle"
  | "validating"
  | "uploading"    // XHR in-flight — progress 0–100
  | "processing"   // server-side pipeline running (indeterminate)
  | "success"
  | "error";

export interface UploadState {
  phase:     UploadPhase;
  progress:  number;          // 0–100, only meaningful during "uploading"
  response:  UploadResponse | null;
  error:     string | null;
}

const INITIAL: UploadState = {
  phase:    "idle",
  progress: 0,
  response: null,
  error:    null,
};

const MAX_SIZE_MB    = 20;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const PDF_MAGIC      = "%PDF-";
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://doctalk-production-c6af.up.railway.app";

// ── Validation ─────────────────────────────────────────────────

async function validateFile(file: File): Promise<string | null> {
  if (!file.name.toLowerCase().endsWith(".pdf"))
    return `Only PDF files are accepted. "${file.name}" is not a PDF.`;
  if (file.size === 0)
    return "The selected file is empty.";
  if (file.size > MAX_SIZE_BYTES)
    return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max: ${MAX_SIZE_MB} MB.`;

  // Magic byte check
  const header = await file.slice(0, 5).arrayBuffer();
  if (!new TextDecoder().decode(header).startsWith(PDF_MAGIC))
    return "File does not appear to be a valid PDF.";

  return null;
}

// ── Hook ───────────────────────────────────────────────────────

export function useUpload() {
  const [state, setState] = useState<UploadState>(INITIAL);
  const xhrRef = useRef<XMLHttpRequest | null>(null);

  const upload = useCallback(async (file: File) => {
    // Validate
    setState({ ...INITIAL, phase: "validating" });
    const validationError = await validateFile(file);
    if (validationError) {
      setState({ ...INITIAL, phase: "error", error: validationError });
      return;
    }

    // Build form data
    const form = new FormData();
    form.append("file", file);

    // XHR — the only browser API that exposes upload progress events
    const xhr = new XMLHttpRequest();
    xhrRef.current = xhr;

    setState((s) => ({ ...s, phase: "uploading", progress: 0 }));

    return new Promise<void>((resolve) => {
      // Upload progress (0 → 100%)
      xhr.upload.onprogress = (e) => {
        if (!e.lengthComputable) return;
        const pct = Math.round((e.loaded / e.total) * 100);
        setState((s) => ({ ...s, phase: "uploading", progress: pct }));
      };

      // Upload complete — server is now processing (indeterminate phase)
      xhr.upload.onload = () => {
        setState((s) => ({ ...s, phase: "processing", progress: 100 }));
      };

      // Response received
      xhr.onload = () => {
        if (xhr.status === 200 || xhr.status === 201) {
          try {
            const response: UploadResponse = JSON.parse(xhr.responseText);
            setState({ phase: "success", progress: 100, response, error: null });
          } catch {
            setState({ ...INITIAL, phase: "error", error: "Invalid response from server." });
          }
        } else {
          let detail = `Upload failed (HTTP ${xhr.status}).`;
          try {
            const body = JSON.parse(xhr.responseText);
            if (typeof body.detail === "string") detail = body.detail;
          } catch { /* keep default */ }
          setState({ ...INITIAL, phase: "error", error: detail });
        }
        resolve();
      };

      xhr.onerror = () => {
        setState({ ...INITIAL, phase: "error", error: "Network error. Check your connection." });
        resolve();
      };

      xhr.onabort = () => {
        setState({ ...INITIAL, phase: "error", error: "Upload cancelled." });
        resolve();
      };

      xhr.open("POST", `${BASE_URL}/upload/`);
      xhr.send(form);
    });
  }, []);

  const cancel = useCallback(() => {
    xhrRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    xhrRef.current?.abort();
    setState(INITIAL);
  }, []);

  return { state, upload, cancel, reset };
}