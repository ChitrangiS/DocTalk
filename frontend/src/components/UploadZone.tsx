"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useUpload } from "../hooks/useUpload";
import type { UploadResponse } from "../lib/types";
import StatusBadge from "./StatusBadge";
import type { UploadPhase } from "../hooks/useUpload";

interface UploadZoneProps {
  onSuccess: (response: UploadResponse) => void;
  onReset: () => void;
  onFile?: (file: File) => void;
}

// ── Progress bar ───────────────────────────────────────────────

function ProgressBar({
  phase,
  progress,
}: {
  phase: UploadPhase;
  progress: number;
}) {
  if (phase !== "uploading" && phase !== "processing") return null;

  const isIndeterminate = phase === "processing";

  return (
    <div className="w-full mt-3">
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
          {isIndeterminate ? "Processing document…" : `Uploading… ${progress}%`}
        </span>

        {!isIndeterminate && (
          <span className="text-xs text-gray-400 dark:text-gray-500">{progress}%</span>
        )}
      </div>

      <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
        {isIndeterminate ? (
          <div className="h-full w-1/2 bg-brand rounded-full animate-[indeterminate_1.4s_ease-in-out_infinite]" />
        ) : (
          <div
            className="h-full bg-brand rounded-full transition-all duration-200"
            style={{ width: `${progress}%` }}
          />
        )}
      </div>
    </div>
  );
}

// ── Component ──────────────────────────────────────────────────

export default function UploadZone({
  onSuccess,
  onReset,
  onFile,
}: UploadZoneProps) {
  const { state, upload, reset } = useUpload();
  const { phase, progress, response, error } = state;

  const inputRef = useRef<HTMLInputElement>(null);

  // ✅ FIXED: proper React state
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      onFile?.(file);
      await upload(file);
    },
    [upload, onFile],
  );

  // Notify parent on success
  useEffect(() => {
    if (phase === "success" && response) {
      onSuccess(response);
    }
  }, [phase, response, onSuccess]);

  const handleReset = () => {
    reset();
    onReset();
  };

  const isActive =
    phase === "uploading" || phase === "validating" || phase === "processing";

  const isSuccess = phase === "success";
  const isError = phase === "error";

  // ── Drag handlers ────────────────────────────────────────────

  function handleDragEnter(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();

    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file && !isActive && !isSuccess) handleFile(file);
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  }

  // ── UI class ────────────────────────────────────────────────

  const zoneClass = [
    "relative flex flex-col items-center justify-center",
    "w-full min-h-[200px] rounded-2xl border-2 border-dashed",
    "transition-all duration-200 select-none",

    isSuccess
      ? "border-green-400 bg-green-50 dark:bg-green-950/30 cursor-default"
      : "",

    isError ? "border-red-300 bg-red-50 dark:bg-red-950/30" : "",

    isActive
      ? "border-brand bg-brand-light/40 dark:bg-brand/10 cursor-wait"
      : "",

    isDragging
      ? "border-brand bg-brand-light scale-[1.01] dark:bg-brand/10 cursor-copy"
      : "",

    !isSuccess && !isError && !isActive && !isDragging
      ? `border-gray-300 dark:border-gray-600
       bg-white dark:bg-gray-800
       hover:border-brand hover:bg-brand-light/30
       dark:hover:border-brand dark:hover:bg-brand/10
       cursor-pointer`
      : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="w-full max-w-xl mx-auto">
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={handleInputChange}
        disabled={isActive || isSuccess}
      />

      <div
        className={zoneClass}
        onClick={() => !isActive && !isSuccess && inputRef.current?.click()}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={!isActive && !isSuccess ? handleDrop : undefined}
      >
        <div className="flex flex-col items-center gap-3 px-6 py-8 w-full text-center">
          {/* Icon */}
          {isSuccess ? (
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
              ✓
            </div>
          ) : isError ? (
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
              ✕
            </div>
          ) : isActive ? (
            <div className="w-12 h-12 rounded-full bg-brand-light flex items-center justify-center">
              <svg
                className="w-5 h-5 text-brand animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            </div>
          ) : (
            <div className="w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
  <svg
    className="w-6 h-6 text-gray-400 dark:text-gray-500"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    strokeWidth={2}
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 16V4m0 0l-4 4m4-4l4 4M4 20h16"
    />
  </svg>
</div>
          )}

          {/* Text */}
          {isSuccess && response ? (
            <div>
  <p className="text-sm font-semibold text-green-700 dark:text-green-400">
    {response.filename}
  </p>

  <p className="text-xs text-gray-500 dark:text-gray-400">
    {response.page_count} pages
  </p>
</div>
          ) : isError ? (
            <div>
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          ) : (
            <div>
              <p className="text-sm font-semibold  text-gray-800 dark:text-gray-200">
                {isDragging ? "Drop here" : "Upload PDF"}
              </p>
            </div>
          )}

          <StatusBadge status={phase} />

          <ProgressBar phase={phase} progress={progress} />

          {isError && (
            <button
  onClick={handleReset}
  className="text-xs text-brand underline underline-offset-2 hover:text-brand-dark"
>
              Retry
            </button>
          )}

          {isSuccess && (
            <button
  onClick={handleReset}
  className="text-xs text-gray-400 dark:text-gray-500 underline underline-offset-2 hover:text-gray-600 dark:hover:text-gray-400"
>
              Upload another
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
