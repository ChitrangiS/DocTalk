"use client";

import { useEffect } from "react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({
  error,
  reset,
}: ErrorPageProps) {
  useEffect(() => {
    console.error("[AppError]", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md rounded-xl border bg-white p-6 shadow">
        <h1 className="mb-3 text-xl font-semibold">
          Something went wrong
        </h1>

        <p className="mb-4 text-gray-600">
          {error.message ||
            "An unexpected error occurred."}
        </p>

        {error.digest && (
          <p className="mb-4 text-xs text-gray-500">
            Error ID: {error.digest}
          </p>
        )}

        <button
          onClick={() => reset()}
          className="rounded-lg border px-4 py-2 text-sm hover:bg-gray-50"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}