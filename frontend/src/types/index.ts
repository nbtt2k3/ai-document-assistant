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
  sources?: SourceItem[];
  isThinking?: boolean;
}

export interface StreamEvent {
  type: 'chunk' | 'final_answer' | 'suggestions' | 'sources' | 'error';
  content: string | string[] | SourceItem[];
}

export interface SourceItem {
  file: string;
  page: number | string;
}
