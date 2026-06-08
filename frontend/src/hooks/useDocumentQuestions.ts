"use client";

import { useEffect, useRef, useState } from "react";
import { parseSseStream, streamChat } from "../lib/api";

// Prompt that instructs the LLM to produce exactly 3 short questions.
// Strict format ("one per line, no extras") makes parsing reliable.
const META_PROMPT =
  "Based on this document, write exactly 3 short questions a reader " +
  "would want to ask. One question per line. No numbering, no bullet " +
  "points, no extra text. Only the 3 questions.";

interface UseDocumentQuestionsResult {
  questions: string[];
  loading:   boolean;
  error:     string | null;
  refresh:   () => void;
}

export function useDocumentQuestions(
  docId: string
): UseDocumentQuestionsResult {
  const [questions, setQuestions] = useState<string[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState<string | null>(null);
  const runRef = useRef(0); // Prevents stale responses on docId change

  async function generate() {
    const run = ++runRef.current;
    setLoading(true);
    setError(null);
    setQuestions([]);

    try {
      const stream = await streamChat(docId, META_PROMPT);
      let fullText = "";

      for await (const event of parseSseStream(stream)) {
        if (run !== runRef.current) return; // stale — abort
        if (event === "[DONE]" || event.startsWith("[SOURCES]")) break;
        fullText += event.replace(/\\n/g, "\n");
      }

      // Parse: split on newlines, trim, drop empty lines, take first 3
      const parsed = fullText
        .split("\n")
        .map((l) => l.trim())
        .filter((l) => l.length > 8 && !l.match(/^\d+[\.\)]/)) // strip "1." prefixes
        .slice(0, 3);

      if (run !== runRef.current) return;

      if (parsed.length === 0) {
        setError("Could not generate questions.");
      } else {
        setQuestions(parsed);
      }
    } catch {
      if (run !== runRef.current) return;
      setError("Could not generate questions.");
    } finally {
      if (run === runRef.current) setLoading(false);
    }
  }

  useEffect(() => {
    if (!docId) return;
    generate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId]);

  return { questions, loading, error, refresh: generate };
}