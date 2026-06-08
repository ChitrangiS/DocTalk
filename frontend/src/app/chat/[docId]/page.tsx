"use client";

import { use } from "react";
import ChatWindow from "../../../components/ChatWindow";

interface Props {
  params: Promise<{
    docId: string;
  }>;
}

export default function ChatPage({ params }: Props) {
  const { docId } = use(params);

  return (
    <main className="h-screen overflow-hidden">
      <ChatWindow docId={docId} filename="Document" />
    </main>
  );
}
