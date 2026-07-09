'use client';

import { useRef, useState } from 'react';
import { Send, Paperclip } from 'lucide-react';
import styles from '@/app/page.module.css';

interface InputBarProps {
  isStreaming: boolean;
  isUploading: boolean;
  onSend: (text: string) => void;
  onFileSelect: (file: File) => void;
}

export default function InputBar({
  isStreaming,
  isUploading,
  onSend,
  onFileSelect,
}: InputBarProps) {
  const [input, setInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
      // Reset input so same file can be re-uploaded
      e.target.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      onFileSelect(file);
    }
  };

  return (
    <div 
      className={`${styles.inputContainer} ${isDragging ? styles.dragging : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isUploading && (
        <div className={styles.uploadingToast}>
          <div className={styles.uploadProgress}>
            <div className={styles.uploadProgressBar}></div>
          </div>
          <span>Đang xử lý tài liệu...</span>
        </div>
      )}
      {isDragging && (
        <div className={styles.dragOverlay}>
          Kéo thả file vào đây để tải lên
        </div>
      )}

      <form className={styles.inputBox} onSubmit={handleSubmit}>
        {/* Hidden file input */}
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          accept=".pdf,.docx,.txt,.xlsx,.csv"
          onChange={handleFileChange}
        />

        {/* Upload button */}
        <button
          type="button"
          className={styles.uploadBtn}
          onClick={() => fileInputRef.current?.click()}
          disabled={isStreaming || isUploading}
          title="Đính kèm tài liệu (PDF, DOCX)"
        >
          <Paperclip size={20} />
        </button>

        {/* Text input */}
        <input
          type="text"
          className={styles.input}
          placeholder="Gửi tin nhắn..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
        />

        {/* Send button */}
        <button
          type="submit"
          className={styles.sendBtn}
          disabled={isStreaming || !input.trim()}
        >
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
