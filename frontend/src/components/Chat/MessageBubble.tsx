'use client';

import ReactMarkdown from 'react-markdown';
import { Message } from '@/types';
import styles from '@/app/page.module.css';

interface MessageBubbleProps {
  message: Message;
  isStreaming: boolean;
  onSuggestionClick: (text: string) => void;
}

export default function MessageBubble({
  message,
  isStreaming,
  onSuggestionClick,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`${styles.messageWrapper} ${isUser ? styles.user : ''}`}>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start',
          maxWidth: '100%',
        }}
      >
        {/* Bubble */}
        <div
          className={`${styles.message} ${isUser ? styles.user : styles.bot} animate-fade-in-up`}
        >
          {message.isThinking ? (
            <div className={styles.thinkingIndicator}>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
              <span className={styles.dot}></span>
            </div>
          ) : isUser ? (
            message.content // Text thô hoặc Markdown nhưng CSS đã ép kiểu plain text
          ) : (
            <ReactMarkdown>{message.content}</ReactMarkdown>
          )}
        </div>

        {/* Suggestion chips */}
        {message.suggestions && message.suggestions.length > 0 && (
          <div className={`${styles.suggestionsContainer} animate-fade-in-up`}>
            {message.suggestions.map((sug, i) => (
              <button
                key={i}
                className={styles.suggestionChip}
                onClick={() => onSuggestionClick(sug)}
                disabled={isStreaming}
              >
                {sug}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
