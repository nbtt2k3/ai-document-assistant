'use client';

import { useState } from 'react';
import { Message } from '@/types';
import { getAuthToken } from '@/lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';

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
      // Suggestions đã được lưu sẵn trong DB và trả về từ API — không cần parse
      setMessages(data);
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
        { role: 'user', content: `**${file.name}**` },
      ]);
      
      // Tự động thông báo cho AI biết đã có file mới
      setTimeout(() => {
        sendQuery(
          `[SYSTEM] File "${file.name}" vừa được tải lên thành công. Dựa vào thông tin này, hãy nói "Tôi đã nhận được tài liệu ${file.name} và đã thêm vào bộ nhớ. Bạn muốn tôi giúp gì?" và KHÔNG CẦN TÓM TẮT.`,
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

  // Cập nhật suggestions của message bot cuối cùng
  const updateLastBotSuggestions = (suggestions: string[]) => {
    setMessages((prev) => {
      const updated = [...prev];
      for (let i = updated.length - 1; i >= 0; i--) {
        if (updated[i].role === 'bot') {
          updated[i] = { ...updated[i], suggestions };
          break;
        }
      }
      return updated;
    });
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
      let buffer = '';
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: '', suggestions: [], isThinking: true },
      ]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        let boundary = buffer.indexOf('\n\n');
        while (boundary !== -1) {
          const chunkStr = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);

          if (chunkStr.startsWith('data: ')) {
            const dataStr = chunkStr.slice(6);
            if (dataStr === '[DONE]') break;

            try {
              const parsed = JSON.parse(dataStr);

              if (parsed.type === 'thought') {
                // Streaming: hiển thị luồng suy nghĩ của AI
                botResponse = botResponse + `> _${parsed.content}_\n\n`;
                setMessages((prev) => {
                  const updated = [...prev];
                  for (let i = updated.length - 1; i >= 0; i--) {
                    if (updated[i].role === 'bot') {
                      updated[i] = {
                        ...updated[i],
                        content: botResponse,
                        isThinking: false,
                      };
                      break;
                    }
                  }
                  return updated;
                });

              } else if (parsed.type === 'chunk') {
                // Streaming: hiển thị raw content, chưa có suggestions
                botResponse = botResponse + parsed.content;
                setMessages((prev) => {
                  const updated = [...prev];
                  for (let i = updated.length - 1; i >= 0; i--) {
                    if (updated[i].role === 'bot') {
                      updated[i] = {
                        ...updated[i],
                        content: botResponse,
                        suggestions: [],
                        isThinking: botResponse.trim() === '',
                      };
                      break;
                    }
                  }
                  return updated;
                });

              } else if (parsed.type === 'final_answer') {
                // Câu trả lời hoàn chỉnh — chỉ cập nhật content, suggestions sẽ đến sau
                botResponse = parsed.content;
                setMessages((prev) => {
                  const updated = [...prev];
                  for (let i = updated.length - 1; i >= 0; i--) {
                    if (updated[i].role === 'bot') {
                      updated[i] = {
                        ...updated[i],
                        content: botResponse,
                        suggestions: [],
                        isThinking: false,
                      };
                      break;
                    }
                  }
                  return updated;
                });

              } else if (parsed.type === 'suggestions') {
                // Câu hỏi gợi ý được sinh riêng bởi backend — cập nhật trực tiếp
                const suggestions: string[] = Array.isArray(parsed.content) ? parsed.content : [];
                updateLastBotSuggestions(suggestions);
              } else if (parsed.type === 'sources') {
                // Nguồn trích dẫn (citations)
                const sources = Array.isArray(parsed.content) ? parsed.content : [];
                setMessages((prev) => {
                  const updated = [...prev];
                  for (let i = updated.length - 1; i >= 0; i--) {
                    if (updated[i].role === 'bot') {
                      updated[i] = { ...updated[i], sources };
                      break;
                    }
                  }
                  return updated;
                });
              }

            } catch (err) {
              console.error('Parse error', err, dataStr);
            }
          }
          boundary = buffer.indexOf('\n\n');
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
