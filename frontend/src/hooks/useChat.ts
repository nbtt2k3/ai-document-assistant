'use client';

import { useState } from 'react';
import { Message, ParsedBotMessage } from '@/types';
import { getAuthToken } from '@/lib/api';

const API_BASE = 'http://127.0.0.1:8000/api';

// ─── Helper: Parse bot message để tách [SUGGESTIONS] ────────────────────────
export function parseBotMessage(rawContent: string): ParsedBotMessage {
  let displayContent = rawContent;
  let suggestions: string[] = [];
  
  // 1. Thử tìm thẻ [SUGGESTIONS]
  const suggestMatch = rawContent.match(/\[SUGGESTIONS\]([^\n]*)/i);
  if (suggestMatch) {
    displayContent = rawContent.replace(suggestMatch[0], '').trim();
    const rawText = suggestMatch[1].replace(/\d+\.\s/g, '|').replace(/"/g, '');
    suggestions = rawText.split('|').map((s) => s.trim()).filter((s) => s.length > 5 && s.includes('?'));
  } else {
    // 2. Fallback: Bắt các danh sách 1. 2. 3. hoặc gạch đầu dòng ở phần cuối của tin nhắn
    const lines = rawContent.split('\n');
    const potentialSuggestions = [];
    let stopIndex = lines.length - 1;

    while (stopIndex >= 0) {
      const line = lines[stopIndex].trim();
      if (!line) {
        stopIndex--;
        continue;
      }
      
      // Match "1. Câu hỏi?" hoặc "- Câu hỏi?" hoặc "* Câu hỏi?"
      const listMatch = line.match(/^(\d+[\.\)]|\-|\*)\s+(.*?\?.*)$/);
      if (listMatch) {
        potentialSuggestions.unshift(listMatch[2].trim());
        stopIndex--;
      } else {
        break;
      }
    }

    // Nếu tìm thấy từ 2 câu hỏi trở lên ở cuối bài, coi đó là suggestions
    if (potentialSuggestions.length >= 2) {
      suggestions = potentialSuggestions;
      displayContent = lines.slice(0, stopIndex + 1).join('\n').trim();
      
      // Cắt luôn câu dẫn dư thừa như "Here are three questions:"
      const lastLine = displayContent.split('\n').pop()?.trim().toLowerCase() || "";
      if (lastLine.includes("question") || lastLine.includes("câu hỏi") || lastLine.includes("gợi ý") || lastLine.includes("explore further")) {
         displayContent = displayContent.substring(0, displayContent.lastIndexOf('\n')).trim();
      }
    }
  }

  // Xóa ký tự '|' dư thừa ở cuối văn bản nếu có
  if (displayContent.endsWith('|')) {
    displayContent = displayContent.slice(0, -1).trim();
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
        { role: 'user', content: `**${file.name}**` },
      ]);

      // Tự động tóm tắt nội dung file vừa upload
      setTimeout(() => {
        sendQuery(
          `[SYSTEM] File "${file.name}" vừa được tải lên. Hãy đóng vai một trợ lý AI thông minh: \n1. Xác nhận thân thiện rằng bạn đã nhận được file.\n2. Tóm tắt nội dung chính của tài liệu một cách tự nhiên.\n3. QUAN TRỌNG: Hãy nhận diện ngôn ngữ của tài liệu và BẮT BUỘC sử dụng CHÍNH NGÔN NGỮ ĐÓ để viết câu chào, bài tóm tắt và 3 câu hỏi gợi ý.`,
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
      let buffer = '';
      setMessages((prev) => [
        ...prev,
        { role: 'bot', content: '', isThinking: true },
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
              if (parsed.type === 'chunk' || parsed.type === 'final_answer') {
                botResponse =
                  parsed.type === 'chunk' ? botResponse + parsed.content : parsed.content;

                const { content, suggestions } = parseBotMessage(botResponse);
                setMessages((prev) => {
                  const updated = [...prev];
                  for (let i = updated.length - 1; i >= 0; i--) {
                    if (updated[i].role === 'bot') {
                      updated[i] = {
                        ...updated[i],
                        content,
                        suggestions,
                        isThinking: content.trim() === '' && parsed.type !== 'final_answer',
                      };
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
