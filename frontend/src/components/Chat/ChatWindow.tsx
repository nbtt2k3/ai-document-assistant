'use client';

import { useEffect, useRef } from 'react';
import { Message } from '@/types';
import MessageBubble from './MessageBubble';
import styles from '@/app/page.module.css';

interface ChatWindowProps {
  sessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  onSuggestionClick: (text: string) => void;
}

export default function ChatWindow({
  sessionId,
  messages,
  isStreaming,
  onSuggestionClick,
}: ChatWindowProps) {
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll xuống khi có tin mới
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className={styles.chatContainer}>
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
    </div>
  );
}
