import type { Metadata } from "next";
import { Inter } from "next/font/google";
// Ignore missing type declarations for CSS imports in this file
// TypeScript config may require a global declaration file (e.g. global.d.ts)
// @ts-igonre
import "./global.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DocTalk — Chat with your PDF",
  description:
    "Upload any PDF and ask natural language questions. Powered by RAG.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.className}>
      <body className="min-h-screen bg-gray-50 text-gray-900">
        {children}
      </body>
    </html>
  );
}