"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../lib/types";

// Bump this if ChatMessage schema ever changes — clears stale stored data
const SCHEMA_VERSION = "v1";
const MAX_MESSAGES_STORED = 100;
const KEY_PREFIX = "doctalk:chat";

function storageKey(docId: string) {
  return `${KEY_PREFIX}:${SCHEMA_VERSION}:${docId}`;
}

// ── Serialisation helpers ─────────────────────────────────────

function loadFromStorage(docId: string): ChatMessage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(storageKey(docId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as ChatMessage[];
  } catch {
    return [];
  }
}

function saveToStorage(docId: string, messages: ChatMessage[]): void {
  if (typeof window === "undefined") return;
  try {
    // Only persist completed messages — never streaming/empty ones
    const toSave = messages
      .filter((m) => m.status === "done" || m.status === "error")
      .filter((m) => m.content.trim().length > 0)
      .slice(-MAX_MESSAGES_STORED);

    localStorage.setItem(storageKey(docId), JSON.stringify(toSave));
  } catch (e) {
    // QuotaExceededError — silently ignore, chat still works without persistence
    if (e instanceof DOMException && e.name === "QuotaExceededError") {
      console.warn("[useChatHistory] localStorage quota exceeded — history not saved.");
    }
  }
}

function clearFromStorage(docId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(storageKey(docId));
  } catch {}
}

// ── Hook ──────────────────────────────────────────────────────

interface UseChatHistoryResult {
  messages:     ChatMessage[];
  setMessages:  React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  clearHistory: () => void;
  hasHistory:   boolean;
}

export function useChatHistory(docId: string): UseChatHistoryResult {
  // Initialise from localStorage synchronously on first render
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadFromStorage(docId)
  );

  // Track docId changes — reload history when user switches documents
  const prevDocId = useRef(docId);
  useEffect(() => {
    if (prevDocId.current !== docId) {
      prevDocId.current = docId;
      setMessages(loadFromStorage(docId));
    }
  }, [docId]);

  // Persist to localStorage whenever messages change
  // Debounced to avoid thrashing on rapid token appends during streaming
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      saveToStorage(docId, messages);
    }, 600);
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
  }, [docId, messages]);

  const clearHistory = useCallback(() => {
    clearFromStorage(docId);
    setMessages([]);
  }, [docId]);

  return {
    messages,
    setMessages,
    clearHistory,
    hasHistory: messages.length > 0,
  };
}