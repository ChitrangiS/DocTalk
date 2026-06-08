"use client";

import { type CSSProperties } from "react";

// ── Base skeleton primitive ────────────────────────────────────

interface SkeletonProps {
  className?: string;
  style?:     CSSProperties;
  rounded?:   "sm" | "md" | "lg" | "full";
}

const RADIUS: Record<NonNullable<SkeletonProps["rounded"]>, string> = {
  sm:   "rounded",
  md:   "rounded-lg",
  lg:   "rounded-xl",
  full: "rounded-full",
};

export function Skeleton({ className = "", style, rounded = "md" }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      style={style}
      className={`
        bg-gradient-to-r from-gray-100 via-gray-200 to-gray-100
        bg-[length:200%_100%] animate-shimmer
        ${RADIUS[rounded]} ${className}
      `}
    />
  );
}

// ── Composed skeletons ─────────────────────────────────────────

/** One assistant message bubble placeholder */
export function MessageSkeleton({ isUser = false }: { isUser?: boolean }) {
  if (isUser) {
    return (
      <div className="flex justify-end">
        <Skeleton className="h-9 w-48" rounded="lg" />
      </div>
    );
  }
  return (
    <div className="flex justify-start gap-2">
      <Skeleton className="w-6 h-6 flex-shrink-0 mt-1" rounded="full" />
      <div className="flex flex-col gap-2 max-w-[75%]">
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-56" />
      </div>
    </div>
  );
}

/** Initial chat panel state — shown before first question */
export function ChatPanelSkeleton() {
  return (
    <div className="flex-1 flex flex-col gap-4 px-4 py-4">
      <MessageSkeleton isUser />
      <MessageSkeleton />
      <MessageSkeleton isUser />
      <MessageSkeleton />
    </div>
  );
}

/** Sidebar document info card placeholder */
export function DocumentCardSkeleton() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-4 w-36" />
      <div className="flex gap-2">
        <Skeleton className="h-3 w-14" />
        <Skeleton className="h-3 w-16" />
      </div>
      <Skeleton className="h-3 w-24" />
    </div>
  );
}

/** Source citation cards placeholder */
export function SourcesSkeleton() {
  return (
    <div className="mt-3 flex flex-col gap-2">
      <Skeleton className="h-3 w-12" />
      <div className="flex gap-2 flex-wrap">
        {[0, 1].map((i) => (
          <div key={i} className="rounded-lg border border-gray-200 p-3 w-56 space-y-2">
            <div className="flex gap-2">
              <Skeleton className="h-4 w-14" rounded="full" />
              <Skeleton className="h-4 w-16" />
            </div>
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-4/5" />
          </div>
        ))}
      </div>
    </div>
  );
}