'use client';

import { useState } from 'react';
import { Session } from '@/types';
import { fetchAPI } from '@/lib/api';

// ─── Hook ────────────────────────────────────────────────────────────────────
export function useSession() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Tải tất cả sessions của user
  const loadSessions = async (): Promise<Session[]> => {
    try {
      const res = await fetchAPI('/sessions/');
      const data: Session[] = await res.json();
      setSessions(data);
      if (data.length > 0) {
        setActiveSessionId(data[0].id);
      }
      return data;
    } catch (e) {
      console.error('loadSessions error:', e);
      return [];
    }
  };

  // Tạo session mới
  const createSession = async (): Promise<Session | null> => {
    try {
      const res = await fetchAPI('/sessions/', {
        method: 'POST',
        body: JSON.stringify({ title: 'Cuộc trò chuyện mới' }),
      });
      const data: Session = await res.json();
      setSessions((prev) => [data, ...prev]);
      setActiveSessionId(data.id);
      return data;
    } catch (e) {
      console.error('createSession error:', e);
      return null;
    }
  };

  // Xoá session theo id
  const deleteSession = async (id: string): Promise<boolean> => {
    const confirmed = window.confirm(
      'Bạn có chắc chắn muốn xoá cuộc trò chuyện này không? Toàn bộ tài liệu tải lên cũng sẽ bị xoá khỏi hệ thống.'
    );
    if (!confirmed) return false;

    try {
      const res = await fetchAPI(`/sessions/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        alert('Có lỗi xảy ra khi xoá phiên!');
        return false;
      }

      setSessions((prev) => prev.filter((s) => s.id !== id));

      // Nếu đang active session bị xoá → chuyển sang session kế tiếp
      if (activeSessionId === id) {
        setSessions((prev) => {
          const remaining = prev.filter((s) => s.id !== id);
          setActiveSessionId(remaining.length > 0 ? remaining[0].id : null);
          return remaining;
        });
      }

      return true;
    } catch (err) {
      console.error('deleteSession error:', err);
      alert('Lỗi kết nối khi xoá phiên!');
      return false;
    }
  };

  const selectSession = (id: string) => setActiveSessionId(id);

  return {
    sessions,
    activeSessionId,
    loadSessions,
    createSession,
    deleteSession,
    selectSession,
    setActiveSessionId,
  };
}
