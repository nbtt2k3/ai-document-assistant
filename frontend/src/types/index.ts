// ─────────────────────────────────────────────
// Shared TypeScript interfaces for the RAG app
// ─────────────────────────────────────────────

export interface Session {
  id: string;
  title: string;
  created_at?: string;
}

export interface Message {
  id?: string;
  role: 'user' | 'bot';
  content: string;
  created_at?: string;
  suggestions?: string[];
  isThinking?: boolean;
}

export interface ParsedBotMessage {
  content: string;
  suggestions: string[];
}

export interface StreamEvent {
  type: 'chunk' | 'final_answer' | 'sources' | 'error';
  content: string | SourceItem[];
}

export interface SourceItem {
  file: string;
  page: number | string;
}
