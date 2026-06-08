"use client";

import { useTheme, type Theme } from "../hooks/useTheme";

// ── Icons ─────────────────────────────────────────────────────

function SunIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24"
         stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386
           6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591
           1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75
           3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24"
         stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M21.752 15.002A9.718 9.718 0 0118 15.75
           9.75 9.75 0 018.25 6c0-1.33.266-2.597.748-3.752
           A9.753 9.753 0 003 12c0 5.385 4.365 9.75
           9.75 9.75 4.592 0 8.461-3.172 9.502-7.498z" />
    </svg>
  );
}

function SystemIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24"
         stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5
           21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25
           2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013
           15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25
           2.25 0 003 5.25m18 0H3" />
    </svg>
  );
}

// ── Simple toggle (icon button) ───────────────────────────────

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { isDark, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={`p-2 rounded-lg transition-all duration-150
                  text-gray-400 hover:text-gray-600 hover:bg-gray-100
                  dark:text-gray-500 dark:hover:text-gray-300
                  dark:hover:bg-gray-800 ${className}`}
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

// ── Three-way picker (light / system / dark) ──────────────────

const OPTIONS: { value: Theme; label: string; icon: React.ReactNode }[] = [
  { value: "light",  label: "Light",  icon: <SunIcon /> },
  { value: "system", label: "System", icon: <SystemIcon /> },
  { value: "dark",   label: "Dark",   icon: <MoonIcon /> },
];

export function ThemePicker({ className = "" }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  return (
    <div className={`flex items-center gap-0.5 p-0.5 rounded-lg
                     bg-gray-100 dark:bg-gray-800 ${className}`}>
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => setTheme(opt.value)}
          aria-label={opt.label}
          aria-pressed={theme === opt.value}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md
                      text-xs font-medium transition-all duration-150
                      ${theme === opt.value
                        ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm"
                        : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                      }`}
        >
          <span className="w-3.5 h-3.5">{opt.icon}</span>
          <span className="hidden sm:inline">{opt.label}</span>
        </button>
      ))}
    </div>
  );
}