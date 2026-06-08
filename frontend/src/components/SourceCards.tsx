"use client";

import type { SourceChunk } from "../lib/types";

interface SourceCardsProps {
  sources: SourceChunk[];
}

export default function SourceCards({ sources }: SourceCardsProps) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-gray-500 mb-2">
        Sources
      </p>

      <div className="space-y-2">
        {sources.map((src, i) => (
          <div
            key={i}
            className="rounded-xl border border-gray-300 bg-gray-50 p-3"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-brand">
                Page {src.page}
              </span>

              <span className="text-xs text-gray-500">
                {Math.round(src.score * 100)}% match
              </span>
            </div>

            <p className="text-xs text-gray-600 line-clamp-3">
              {src.excerpt}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}