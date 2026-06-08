"use client";

import { useRef } from "react";
import { useState } from "react";
import type { ChatMessage } from "../lib/types";
import SourceCards from "./SourceCards";

// ── Streaming cursor ───────────────────────────────────────────

function Cursor() {
  return (
    <span
      aria-hidden="true"
      className="inline-block w-[2px] h-[14px] ml-[2px] bg-gray-400 align-middle
                 animate-[blink_1s_step-end_infinite] rounded-full"
    />
  );
}

// ── Timestamp ─────────────────────────────────────────────────

function Timestamp({ date }: { date: Date }) {
  return (
    <time
      dateTime={date.toISOString()}
      className="block text-[10px] text-gray-400 mt-1 select-none"
    >
      {date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
    </time>
  );
}

// ── User bubble ───────────────────────────────────────────────

function UserBubble({ content, date }: { content: string; date: Date }) {
  return (
    <div className="flex flex-col items-end gap-0.5">
      <div
        className="max-w-[75%] px-4 py-2.5 rounded-2xl rounded-tr-sm
                   bg-brand text-white text-sm leading-relaxed
                   shadow-sm animate-[fadeSlideUp_0.2s_ease-out]"
      >
        {content}
      </div>
      <Timestamp date={date} />
    </div>
  );
}

// ── Assistant avatar ──────────────────────────────────────────

function Avatar() {
  return (
    <div
      aria-hidden="true"
      className="w-7 h-7 rounded-full bg-brand flex-shrink-0
                 flex items-center justify-center shadow-sm mt-0.5"
    >
      <svg
        className="w-3.5 h-3.5 text-white"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0
             00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0
             003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0
             003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0
             00-3.09 3.09z"
        />
      </svg>
    </div>
  );
}
// ── Copy button ───────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for browsers that block clipboard without user gesture
      const el = document.createElement("textarea");
      el.value = text;
      el.style.position = "fixed";
      el.style.opacity = "0";
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <button
      onClick={handleCopy}
      aria-label={copied ? "Copied" : "Copy answer"}
      className="opacity-0 group-hover:opacity-100 focus:opacity-100
                 transition-all duration-150 flex items-center gap-1
                 px-2 py-1 rounded-lg text-[10px] font-medium
                 text-gray-400 hover:text-gray-600
                 hover:bg-gray-100 active:scale-95"
    >
      {copied ? (
        <>
          <svg className="w-3 h-3 text-green-500" fill="none" viewBox="0 0 24 24"
               stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-green-500">Copied</span>
        </>
      ) : (
        <>
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24"
               stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03
                 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0
                 a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332
                 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077
                 1.907 2.185V19.5a2.25 2.25 0 01-2.25
                 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057
                 1.907-2.185a48.208 48.208 0 011.927-.184" />
          </svg>
          Copy
        </>
      )}
    </button>
  );
}
// ── Assistant bubble ──────────────────────────────────────────

function AssistantBubble({
  message,
  date,
}: {
  message: ChatMessage;
  date: Date;
}) {
  const isStreaming = message.status === "streaming";
  const isError     = message.status === "error";
  const isDone      = message.status === "done";
  const isEmpty     = !message.content && isStreaming;

  return (
    <div className="flex items-start gap-2.5 animate-[fadeSlideUp_0.2s_ease-out]">
      <Avatar />

      <div className="flex flex-col gap-1 max-w-[82%]">
        {/* Bubble */}
        <div
          className={`
            px-4 py-3 rounded-2xl rounded-tl-sm text-sm leading-relaxed
            shadow-sm border
            ${isError
              ? "bg-red-50 border-red-200 text-red-700"
              : "bg-white border-gray-200 text-gray-800"
            }
          `}
        >
          {isEmpty ? (
            // Waiting for first token — three dot pulse
            <span className="flex items-center gap-1 h-5" aria-label="Thinking">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-gray-400
                             animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </span>
          ) : (
            <p className="whitespace-pre-wrap">
              {message.content}
              {isStreaming && <Cursor />}
            </p>
          )}
        </div>
        {/* Copy button — only when done and has content */}<div className="flex items-center gap-2 pl-1">
          {isDone && !isError && message.content && (
            <CopyButton text={message.content} />
          )}
          <Timestamp date={date} />
        </div>            
        {/* Sources — only when done */}
        {isDone && message.sources.length > 0 && (
          <SourceCards sources={message.sources} />
        )}

        <Timestamp date={date} />
      </div>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────

export default function MessageBubble({ message }: { message: ChatMessage }) {
  // Stable timestamp — set once on mount, never changes on re-render
  const dateRef = useRef(new Date());

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <UserBubble content={message.content} date={dateRef.current} />
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <AssistantBubble message={message} date={dateRef.current} />
    </div>
  );
}