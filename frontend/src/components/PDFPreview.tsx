"use client";

import { useEffect, useMemo, useState } from "react";

interface PDFPreviewProps {
  file: File | null;
}

export default function PDFPreview({ file }: PDFPreviewProps) {
  const [collapsed, setCollapsed] = useState(false);

  // Create blob URL once per file — revoke on cleanup to prevent memory leak
  const blobUrl = useMemo(() => {
    if (!file) return null;
    return URL.createObjectURL(file);
  }, [file]);

  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [blobUrl]);

  if (!file || !blobUrl) {
    return (
      <div className="rounded-xl border border-gray-200 bg-gray-50
                      flex flex-col items-center justify-center
                      h-48 gap-2 text-center px-4">
        <svg className="w-7 h-7 text-gray-300" fill="none"
             viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M19.5 14.25v-2.625a3.375 3.375 0
               00-3.375-3.375h-1.5A1.125 1.125 0
               0113.5 7.125v-1.5a3.375 3.375 0
               00-3.375-3.375H8.25m2.25
               0H5.625c-.621 0-1.125.504-1.125
               1.125v17.25c0 .621.504 1.125
               1.125 1.125h12.75c.621 0
               1.125-.504 1.125-1.125V11.25a9
               9 0 00-9-9z" />
        </svg>
        <p className="text-xs text-gray-400">No document preview</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden
                    flex flex-col bg-white">

      {/* Header bar */}
      <div className="flex items-center justify-between px-3 py-2
                      border-b border-gray-100 bg-gray-50 flex-shrink-0">
        <span className="text-[10px] font-medium text-gray-500 truncate max-w-[140px]">
          {file.name}
        </span>
        <div className="flex items-center gap-1 flex-shrink-0">
          {/* Open in new tab */}
          <a
            href={blobUrl}
            target="_blank"
            rel="noopener noreferrer"
            title="Open in new tab"
            className="p-1 rounded-md text-gray-400 hover:text-gray-600
                       hover:bg-gray-100 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24"
                 stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M13.5 6H5.25A2.25 2.25 0 003
                   8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25
                   2.25 0 0018 18.75V10.5m-10.5
                   6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
          </a>

          {/* Collapse / expand */}
          <button
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? "Expand preview" : "Collapse preview"}
            className="p-1 rounded-md text-gray-400 hover:text-gray-600
                       hover:bg-gray-100 transition-colors"
          >
            <svg className="w-3.5 h-3.5 transition-transform duration-200"
                 style={{ transform: collapsed ? "rotate(180deg)" : "rotate(0deg)" }}
                 fill="none" viewBox="0 0 24 24"
                 stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M4.5 15.75l7.5-7.5 7.5 7.5" />
            </svg>
          </button>
        </div>
      </div>

      {/* iframe — hidden when collapsed */}
      {!collapsed && (
        <iframe
          src={`${blobUrl}#toolbar=0&navpanes=0&scrollbar=1`}
          title={`Preview: ${file.name}`}
          className="w-full border-0"
          style={{ height: 380 }}
          aria-label={`PDF preview of ${file.name}`}
        />
      )}

      {/* Collapsed stub */}
      {collapsed && (
        <div
          className="h-10 flex items-center justify-center
                     text-xs text-gray-400 cursor-pointer hover:bg-gray-50
                     transition-colors"
          onClick={() => setCollapsed(false)}
        >
          Click to expand preview
        </div>
      )}
    </div>
  );
}