import type { Metadata } from "next";
import ChatPanel from "@/components/chat/chat-panel";
import ConversaShell from "@/components/chat/conversa-shell";

export const metadata: Metadata = {
  title: "Conversa — Sophie AI",
  description: "Chat em tempo real com a Sophie",
};

export default function ConversaPage() {
  return (
    <ConversaShell>
      <main className="flex-1 space-y-6 overflow-x-hidden p-5 md:p-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Conversa
          </h1>
          <p className="font-mono-data text-xs uppercase tracking-widest text-[var(--text-secondary)]">
            Bata um papo com a Sophie em tempo real
          </p>
        </header>
        <ChatPanel />
      </main>
    </ConversaShell>
  );
}
