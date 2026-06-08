"use client";

type Status =
  | "idle"
  | "validating"
  | "uploading"
  | "processing"
  | "success"
  | "error";

interface StatusBadgeProps {
  status: Status;
  label?: string;
  className?: string;
}


const STATUS_STYLES: Record<Status, string> = {
  idle: "bg-gray-100 text-gray-500",
  validating: "bg-blue-50 text-blue-600",
  uploading: "bg-yellow-50 text-yellow-700 animate-pulse",
  processing: "bg-yellow-50 text-yellow-700 animate-pulse",
  success: "bg-green-50 text-green-700",
  error: "bg-red-50 text-red-600",
};

const STATUS_LABELS: Record<Status, string> = {
  idle: "Ready",
  validating: "Validating...",
  uploading: "Uploading...",
  processing: "Processing...",
  success: "Ready",
  error: "Error",
};



export default function StatusBadge({
  status,
  label,
  className = "",
}: StatusBadgeProps) {
  const text = label ?? STATUS_LABELS[status];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLES[status]} ${className}`}
    >
      {(status === "uploading" || status === "processing") && <span>●</span>}
      {status === "success" && <span>✓</span>}
      {status === "error" && <span>✕</span>}
      {text}
    </span>
  );
}