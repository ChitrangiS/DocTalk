"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { parseSseStream, streamChat } from "../lib/api";
import type { ApiError, ChatMessage, SourceChunk } from "../lib/types";
import MessageBubble from "./MessageBubble";
import { useDocumentQuestions } from "../hooks/useDocumentQuestions";
import { MessageSkeleton, Skeleton } from "./Skeleton";
import { useChatHistory } from "../hooks/useChatHistory";
interface ChatWindowProps {
  docId: string;
  filename: string; // ← new prop — passed from page.tsx
}

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

function userMessage(content: string): ChatMessage {
  return { id: makeId(), role: "user", content, sources: [], status: "done" };
}

const MAX_CHARS = 1000;



// ── Panel header ──────────────────────────────────────────────

function ChatHeader({
  filename,
  hasHistory,
  onClear,
}: {
  filename:   string;
  hasHistory: boolean;
  onClear:    () => void;
}) {
  const [confirming, setConfirming] = useState(false);

  function handleClear() {
    if (!confirming) {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 2500);
      return;
    }
    onClear();
    setConfirming(false);
  }

  return (
    <div className="flex items-center justify-between px-4 py-3
                    border-b border-gray-100 bg-white flex-shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        <div className="w-7 h-7 rounded-lg bg-red-50 flex items-center
                        justify-center flex-shrink-0">
          <svg className="w-3.5 h-3.5 text-red-500" fill="none"
               viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125
                 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0
                 00-3.375-3.375H8.25m2.25 0H5.625c-.621
                 0-1.125.504-1.125 1.125v17.25c0 .621.504
                 1.125 1.125 1.125h12.75c.621 0 1.125-.504
                 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        </div>
        <span className="text-sm font-medium text-gray-800 truncate">
          {filename}
        </span>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Clear history — two-step confirm */}
        {hasHistory && (
          <button
            onClick={handleClear}
            className={`text-[10px] font-medium px-2.5 py-1 rounded-lg
                        transition-all duration-150
                        ${confirming
                          ? "bg-red-50 text-red-600 hover:bg-red-100"
                          : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                        }`}
          >
            {confirming ? "Tap again to clear" : "Clear history"}
          </button>
        )}

        {/* Model badge */}
        <span className="inline-flex items-center gap-1 px-2 py-0.5
                         rounded-full bg-brand-light text-brand
                         text-xs font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-brand" />
          Llama 3.1
        </span>
      </div>
    </div>
  );
}
// ── Empty state ───────────────────────────────────────────────

function EmptyState({
  questions,
  loading,
  error,
  onSelect,
  onRefresh,
  disabled,
}: {
  questions: string[];
  loading: boolean;
  error: string | null;
  onSelect: (q: string) => void;
  onRefresh: () => void;
  disabled: boolean;
}) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-5 px-6 text-center">
      {/* Hero text */}
      <div className="space-y-1.5">
        <p className="text-sm font-semibold text-gray-800">
          Ask anything about your document
        </p>
        <p className="text-xs text-gray-400 max-w-xs">
          Answers are grounded in the PDF content and include page citations.
        </p>
      </div>

      {/* Suggested questions */}
      <div className="flex flex-col gap-2 w-full max-w-sm">
        {loading && (
          <>
            <Skeleton className="h-10 w-full" rounded="lg" />
            <Skeleton className="h-10 w-full" rounded="lg" />
            <Skeleton className="h-10 w-5/6 mx-auto" rounded="lg" />
            <p className="text-[10px] text-gray-400 mt-1">
              Generating questions…
            </p>
          </>
        )}

        {!loading && error && (
          <div className="space-y-3">
            <p className="text-xs text-gray-400">{error}</p>
            <button
              onClick={onRefresh}
              disabled={disabled}
              className="text-xs text-brand underline underline-offset-2
                         hover:text-brand-dark disabled:opacity-50"
            >
              Try again
            </button>
          </div>
        )}

        {!loading &&
          !error &&
          questions.map((q) => (
            <button
              key={q}
              onClick={() => onSelect(q)}
              disabled={disabled}
              className="group text-left text-xs text-gray-600 bg-gray-50
                       hover:bg-brand-light hover:text-brand
                       border border-gray-200 hover:border-brand/30
                       rounded-xl px-4 py-3 transition-all duration-150
                       disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span className="flex items-center gap-2">
                <svg
                  className="w-3 h-3 text-gray-400 group-hover:text-brand flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M8.625 12a.375.375 0 11-.75 0 .375.375 0
                     01.75 0zm0 0H8.25m4.125 0a.375.375 0
                     11-.75 0 .375.375 0 01.75 0zm0
                     0H12m4.125 0a.375.375 0 11-.75 0
                     .375.375 0 01.75 0zm0 0h-.375M21
                     12c0 4.556-4.03 8.25-9 8.25a9.764
                     9.764 0 01-2.555-.337A5.972 5.972
                     0 015.41 20.97a5.969 5.969 0
                     01-.474-.065 4.48 4.48 0
                     00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93
                     16.178 3 14.189 3 12c0-4.556
                     4.03-8.25 9-8.25s9 3.694 9 8.25z"
                  />
                </svg>
                {q}
              </span>
            </button>
          ))}

        {/* Refresh button — only shown after successful load */}
        {!loading && !error && questions.length > 0 && (
          <button
            onClick={onRefresh}
            disabled={disabled || loading}
            className="flex items-center justify-center gap-1 text-[10px]
                       text-gray-400 hover:text-gray-600 mt-1 mx-auto
                       transition-colors disabled:opacity-40"
          >
            <svg
              className="w-3 h-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985
                   19.644v-4.992m0 0h4.992m-4.993
                   0l3.181 3.183a8.25 8.25 0
                   0013.803-3.7M4.031 9.865a8.25
                   8.25 0 0113.803-3.7l3.181
                   3.182m0-4.991v4.99"
              />
            </svg>
            Regenerate
          </button>
        )}
      </div>
    </div>
  );
}

// ── Input bar ─────────────────────────────────────────────────

function InputBar({
  value,
  onChange,
  onSubmit,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled: boolean;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const remaining = MAX_CHARS - value.length;
  const isNearLimit = remaining < 100;

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    if (e.target.value.length > MAX_CHARS) return;
    onChange(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`;
  }

  // Focus on mount
  useEffect(() => {
    ref.current?.focus();
  }, []);

  const canSubmit = value.trim().length > 0 && !disabled;

  return (
    <div className="flex-shrink-0 px-4 py-3 bg-white border-t border-gray-100">
      <div
        className={`
        flex items-end gap-2 rounded-2xl border-2 bg-white px-4 py-3
        transition-colors duration-150
        ${disabled ? "border-gray-100 bg-gray-50" : "border-gray-200 focus-within:border-brand"}
      `}
      >
        <textarea
          ref={ref}
          rows={1}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask a question…"
          aria-label="Chat input"
          className="flex-1 resize-none bg-transparent text-sm text-gray-900
                     placeholder-gray-400 outline-none leading-relaxed
                     min-h-[24px] max-h-[140px] disabled:opacity-50"
        />

        {/* Character counter */}
        {isNearLimit && (
          <span
            className={`text-[10px] flex-shrink-0 mb-0.5 tabular-nums
            ${remaining <= 0 ? "text-red-500" : "text-gray-400"}`}
          >
            {remaining}
          </span>
        )}

        {/* Send button */}
        <button
          onClick={onSubmit}
          disabled={!canSubmit}
          aria-label="Send message"
          className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center
                     transition-all duration-150 disabled:cursor-not-allowed
                     bg-brand hover:bg-brand-dark disabled:bg-gray-200
                     active:scale-95"
        >
          {disabled ? (
            <span
              className="w-3.5 h-3.5 border-2 border-white/40 border-t-white
                             rounded-full animate-spin"
            />
          ) : (
            <svg
              className="w-3.5 h-3.5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18"
              />
            </svg>
          )}
        </button>
      </div>

      <p className="mt-1.5 text-center text-[10px] text-gray-400">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────

export default function ChatWindow({ docId, filename }: ChatWindowProps) {
  const {
  messages,
  setMessages,
  clearHistory,
  hasHistory,
} = useChatHistory(docId);
const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [awaitingFirstToken, setAwaitingFirstToken] = useState(false);
  const { questions, loading, error, refresh } = useDocumentQuestions(docId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (!q || isStreaming) return;

      setInput("");
      setIsStreaming(true);
      setAwaitingFirstToken(true);

      const assistantId = makeId();
      setMessages((prev) => [
        ...prev,
        userMessage(q),
        {
          id: assistantId,
          role: "assistant",
          content: "",
          sources: [],
          status: "streaming",
        },
      ]);

      try {
        const stream = await streamChat(docId, q);

        for await (const event of parseSseStream(stream)) {
          if (event.startsWith("[SOURCES]")) {
            let sources: SourceChunk[] = [];
            try {
              sources = JSON.parse(event.slice("[SOURCES]".length));
            } catch {}
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, sources } : m)),
            );
          } else if (event === "[DONE]") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, status: "done" } : m,
              ),
            );
            break;
          } else {
            setAwaitingFirstToken(false);
            const token = event.replace(/\\n/g, "\n");
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + token } : m,
              ),
            );
          }
        }
      } catch (err) {
        setAwaitingFirstToken(false);
        const msg =
          typeof (err as ApiError).detail === "string"
            ? ((err as ApiError).detail as string)
            : "Something went wrong. Please try again.";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: msg, status: "error" } : m,
          ),
        );
      } finally {
        setAwaitingFirstToken(false);
        setIsStreaming(false);
      }
    },
    [docId, isStreaming,setMessages],
  );

  return (
    <div className="flex flex-col h-full">
      <ChatHeader
  filename={filename}
  hasHistory={hasHistory}
  onClear={clearHistory}
/>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5 bg-gray-50/50">
        {messages.length === 0 ? (
          <EmptyState
            questions={questions}
            loading={loading}
            error={error}
            onSelect={handleSubmit}
            onRefresh={refresh}
            disabled={isStreaming}
          />
        ) : (
          <>
            {messages.map((msg) => {
              if (
                msg.role === "assistant" &&
                msg.status === "streaming" &&
                msg.content === "" &&
                awaitingFirstToken
              ) {
                return (
                  <div key={msg.id}>
                    <MessageSkeleton />
                  </div>
                );
              }
              return <MessageBubble key={msg.id} message={msg} />;
            })}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      <InputBar
        value={input}
        onChange={setInput}
        onSubmit={() => handleSubmit(input)}
        disabled={isStreaming}
      />
    </div>
  );
}
