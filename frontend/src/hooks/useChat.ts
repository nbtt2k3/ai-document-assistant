'use client';

import { useState } from 'react';
import { Message, ParsedBotMessage } from '@/types';
import { getAuthToken } from '@/lib/api';

const API_BASE = 'http://127.0.0.1:8000/api';

// ─── Helper: Parse bot message để tách [SUGGESTIONS] ────────────────────────
export function parseBotMessage(rawContent: string): ParsedBotMessage {
  let displayContent = rawContent;
  let suggestions: string[] = [];
  const suggestMatch = rawContent.match(/\[SUGGESTIONS\]([\s\S]*)/i);
  if (suggestMatch) {
    displayContent = rawContent.replace(suggestMatch[0], '').trim();
    // Tách và dọn dẹp các câu hỏi
    const rawText = suggestMatch[1].replace(/\d+\.\s/g, '|').replace(/"/g, '');
    suggestions = rawText.split('|').map((s) => s.trim()).filter((s) => s.length > 5 && s.includes('?'));
  }
  
  // Xóa ký tự '|' dư thừa ở cuối văn bản nếu có
  if (displayContent.endsWith('|')) {
    displayContent = displayContent.slice(0, -1).trim();
  }

  // Chống lỗi AI cố tình tạo gợi ý ảo khi không có thông tin
  const noInfoPhrases = ["chưa có thông tin", "không có thông tin", "không được đề cập"];
  const isNoInfo = noInfoPhrases.some(phrase => displayContent.toLowerCase().includes(phrase));
  if (isNoInfo) {
    suggestions = [];
  }

  return { content: displayContent, suggestions };
}

// ─── Hook ────────────────────────────────────────────────────────────────────
export function useChat(activeSessionId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Tải tin nhắn của một session
  const loadMessages = async (sessionId: string) => {
    try {
      const token = getAuthToken();
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data: Message[] = await res.json();
      const parsed = data.map((msg) => {
        if (msg.role === 'bot') {
          const { content, suggestions } = parseBotMessage(msg.content);
          return { ...msg, content, suggestions };
        }
        return msg;
      });
      setMessages(parsed);
    } catch (e) {
      console.error('loadMessages error:', e);
    }
  };

  // Upload file và tóm tắt tự động
  const uploadFile = async (file: File) => {
    if (!activeSessionId) return;
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const token = getAuthToken();
      const res = await fetch(`${API_BASE}/sessions/${activeSessionId}/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) throw new Error('Upload failed');

      setMessages((prev) => [
        ...prev,
        { role: 'user', content: `📎 **Đã tải lên tài liệu:** ${file.name}` },
      ]);

      // Tự động tóm tắt nội dung file vừa upload
      setTimeout(() => {
        sendQuery(
          'Tài liệu tôi vừa tải lên có nội dung chính là gì? Hãy tóm tắt ngắn gọn và gợi ý cho tôi 3 câu hỏi để bắt đầu tìm hiểu sâu hơn.',
          true
        );
      }, 500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      alert('Lỗi khi tải file: ' + msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Gửi câu hỏi và nhận SSE streaming
  const sendQuery = async (queryText: string, isSystem = false) => {
    if (!queryText.trim() || !activeSessionId || isStreaming) return;

    const displayQuery = isSystem ? `[SYSTEM] ${queryText}` : queryText;

    if (!isSystem) {
      setMessages((prev) => [...prev, { role: 'user', content: queryText }]);
    }

    setIsStreaming(true);

    try {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE}/sessions/${activeSessionId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ question: displayQuery }),
      });

      if (!response.ok) throw new Error('API Error');
      if (!response.body) throw new Error('No body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      let botResponse = '';
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: '', isThinking: true },
      ]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const dataStr = line.slice(6);
          if (dataStr === '[DONE]') break;

          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.type === 'chunk' || parsed.type === 'final_answer') {
              botResponse =
                parsed.type === 'chunk' ? botResponse + parsed.content : parsed.content;

              const { content, suggestions } = parseBotMessage(botResponse);
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content,
                  suggestions,
                  isThinking: false,
                };
                return updated;
              });
            }
          } catch (err) {
            console.error('Parse error', err, dataStr);
          }
        }
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: 'Có lỗi xảy ra khi kết nối tới server.' },
      ]);
    } finally {
      setIsStreaming(false);
    }
  };

  const clearMessages = () => setMessages([]);

  return {
    messages,
    isStreaming,
    isUploading,
    loadMessages,
    uploadFile,
    sendQuery,
    clearMessages,
  };
}
