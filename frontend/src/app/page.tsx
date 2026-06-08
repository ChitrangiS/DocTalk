"use client";

import { useState } from "react";
import ErrorBoundary from "../components/ErrorBoundary";
import UploadZone from "../components/UploadZone";
import ChatWindow from "../components/ChatWindow";
import PDFPreview from "../components/PDFPreview";
import type { UploadResponse } from "../lib/types";
import {  ThemePicker } from "../components/ThemeToggle";
// ── Header ────────────────────────────────────────────────────

function Header() {
  return (
    <header className="h-14 flex-shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-5">
      <div className="h-full max-w-7xl mx-auto flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-brand flex items-center justify-center shadow-sm">
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0
                   01-2-2V6a2 2 0 012-2h14a2 2 0 012
                   2v8a2 2 0 01-2 2h-3l-4 4z"
              />
            </svg>
          </div>
          <span className="text-[15px] font-semibold text-gray-900 tracking-tight">
            DocTalk
          </span>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          <span className="hidden sm:flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-600">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
            All systems operational
          </span>

          <ThemePicker />

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-gray-600 dark:text-gray-600 dark:hover:text-gray-400 transition-colors"
            aria-label="GitHub"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18..." />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
}

// ── Before upload — hero ──────────────────────────────────────

function HeroUpload({
  onSuccess,
  onFile,
}: {
  onSuccess: (r: UploadResponse) => void;
  onFile: (f: File) => void;
}) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-lg space-y-8">
        {/* Hero text */}
        <div className="text-center space-y-3">
          <div
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full
                          bg-brand-light text-brand text-xs font-medium mb-2"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-brand" />
            Powered by RAG · Llama 3.1 · ChromaDB
          </div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight leading-tight">
            Chat with any PDF
          </h1>
          <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
            Upload a document and ask questions in plain English. Get grounded
            answers with page-level citations.
          </p>
        </div>

        {/* Upload zone */}
        <UploadZone onSuccess={onSuccess} onReset={() => {}} onFile={onFile} />

        {/* Feature pills */}
        <div className="flex flex-wrap justify-center gap-2">
          {[
            "Streaming answers",
            "Page citations",
            "Local embeddings",
            "100% free",
          ].map((f) => (
            <span
              key={f}
              className="px-3 py-1 rounded-full bg-white border border-gray-200
                         text-xs text-gray-500 shadow-sm"
            >
              {f}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── After upload — two-column shell ──────────────────────────

function AppShell({
  uploadResponse,
  previewFile,
  onReset,
}: {
  uploadResponse: UploadResponse;
  previewFile: File | null;
  onReset: () => void;
}) {
  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar */}
      <aside
        className="w-64 flex-shrink-0 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col overflow-y-auto"
      >
        <div className="p-4 space-y-4">
          <PDFPreview file={previewFile} />
          {/* Section label */}
          <p className="text-[10px] font-semibold text-gray-400 dark:text-gray-600 uppercase tracking-widest px-1">
            Document
          </p>

          {/* Document card */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-3.5 space-y-2.5">
            {/* File icon + name */}
            <div className="flex items-start gap-2.5">
              <div
                className="w-8 h-8 rounded-lg bg-red-50 flex items-center
                              justify-center flex-shrink-0"
              >
                <svg
                  className="w-4 h-4 text-red-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0
                       00-3.375-3.375h-1.5A1.125 1.125 0
                       0113.5 7.125v-1.5a3.375 3.375 0
                       00-3.375-3.375H8.25m2.25 0H5.625c-.621
                       0-1.125.504-1.125 1.125v17.25c0 .621.504
                       1.125 1.125 1.125h12.75c.621 0
                       1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                  />
                </svg>
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-800 truncate leading-snug">
                  {uploadResponse.filename}
                </p>
                <p className="text-[10px] text-gray-400 mt-0.5">
                  {uploadResponse.page_count} pages ·{" "}
                  {uploadResponse.chunk_count} chunks
                </p>
              </div>
            </div>

            {/* Status pill */}
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
              <span className="text-[10px] text-gray-500">
                Indexed and ready
              </span>
            </div>

            {/* doc_id */}
            <p className="text-[9px] font-mono text-gray-300 truncate">
              {uploadResponse.doc_id}
            </p>
          </div>

          {/* Upload new */}
          <UploadZone onSuccess={onReset} onReset={onReset} />
        </div>
      </aside>

      {/* Chat panel */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-white dark:bg-gray-900">
        <ErrorBoundary label="Chat">
          <ChatWindow
            docId={uploadResponse.doc_id}
            filename={uploadResponse.filename}
          />
        </ErrorBoundary>
      </main>
    </div>
  );
}

// ── Root page ─────────────────────────────────────────────────

export default function Home() {
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(
    null,
  );
  const [previewFile, setPreviewFile] = useState<File | null>(null);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-950">

      <Header />

      {uploadResponse ? (
        <AppShell
          uploadResponse={uploadResponse}
          previewFile={previewFile}
          onReset={() => {
            setUploadResponse(null);
            setPreviewFile(null);
          }}
        />
      ) : (
        <HeroUpload
          onSuccess={setUploadResponse}
          onFile={setPreviewFile}
        />
      )}
    </div>
  );
}
