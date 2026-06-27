'use client';

import { useEffect, useRef, useState } from 'react';
import { Message } from '@/types';
import { BookOpen } from 'lucide-react';
import MessageBubble from './MessageBubble';
import TOCModal from './TOCModal';
import styles from '@/app/page.module.css';

interface ChatWindowProps {
  sessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  onSuggestionClick: (text: string) => void;
  onSummarizeSection: (title: string, level: number) => void;
}

export default function ChatWindow({
  sessionId,
  messages,
  isStreaming,
  onSuggestionClick,
  onSummarizeSection,
}: ChatWindowProps) {
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [isTOCModalOpen, setIsTOCModalOpen] = useState(false);

  // Auto-scroll xuống khi có tin mới
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', overflow: 'hidden' }}>
      {sessionId && messages.length > 0 && (
        <div style={{ 
          padding: '12px 24px', 
          display: 'flex', 
          justifyContent: 'flex-end', 
          borderBottom: '1px solid var(--border-color)',
          background: 'var(--chat-bg)',
          position: 'sticky',
          top: 0,
          zIndex: 10
        }}>
          <button 
            onClick={() => setIsTOCModalOpen(true)}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px', 
              background: 'var(--glass-bg)', border: '1px solid var(--border-color)',
              padding: '8px 16px', borderRadius: '20px', cursor: 'pointer',
              color: 'var(--text-primary)', fontSize: '0.9rem',
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)', transition: 'all 0.2s'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = 'var(--accent-color)';
              e.currentTarget.style.color = 'var(--accent-color)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-color)';
              e.currentTarget.style.color = 'var(--text-primary)';
            }}
          >
            <BookOpen size={16} color="currentColor" />
            <span>Xem Mục lục</span>
          </button>
        </div>
      )}

      <div className={styles.chatContainer} style={{ flex: 1, overflowY: 'auto' }}>

      {messages.length === 0 && (
        <div className={styles.emptyState}>
          <h2>Bắt đầu cuộc trò chuyện</h2>
          <p>Hãy tải tài liệu lên (PDF/DOCX) và hỏi tôi bất kỳ điều gì.</p>
        </div>
      )}

      {messages.map((msg, idx) => (
        <MessageBubble
          key={idx}
          message={msg}
          isStreaming={isStreaming}
          onSuggestionClick={onSuggestionClick}
        />
      ))}

      <div ref={chatEndRef} />

      {isTOCModalOpen && sessionId && (
        <TOCModal 
          sessionId={sessionId}
          onClose={() => setIsTOCModalOpen(false)}
          onSummarize={onSummarizeSection}
        />
      )}
      </div>
    </div>
  );
}
