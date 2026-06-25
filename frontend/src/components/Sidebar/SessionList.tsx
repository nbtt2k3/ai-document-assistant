'use client';

import { PlusCircle, LogOut, MessageSquare, X, Trash2 } from 'lucide-react';
import { Session } from '@/types';
import styles from '@/app/page.module.css';

interface SessionListProps {
  sessions: Session[];
  activeSessionId: string | null;
  isSidebarOpen: boolean;
  onSelectSession: (id: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (e: React.MouseEvent, id: string) => void;
  onLogout: () => void;
  onCloseSidebar: () => void;
  isCollapsed?: boolean;
}

export default function SessionList({
  sessions,
  activeSessionId,
  isSidebarOpen,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onLogout,
  onCloseSidebar,
  isCollapsed = false,
}: SessionListProps) {
  return (
    <div className={`${styles.sidebar} glass-panel ${isSidebarOpen ? styles.sidebarOpen : ''} ${isCollapsed ? styles.collapsed : ''}`}>
      {/* Header */}
      <div className={styles.sidebarHeader}>
        <button className={styles.newChatBtn} onClick={onCreateSession}>
          <PlusCircle size={20} /> Tạo phiên mới
        </button>
        <button className={styles.collapseSidebarBtn} onClick={onCloseSidebar} title="Thu gọn (Desktop) / Đóng (Mobile)">
          <X size={20} className={styles.closeIconDesktop} />
        </button>
      </div>

      {/* Session list */}
      <div className={styles.sessionList}>
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`${styles.sessionItem} ${activeSessionId === s.id ? styles.active : ''}`}
            onClick={() => {
              onSelectSession(s.id);
              onCloseSidebar();
            }}
          >
            <MessageSquare size={16} />
            <span className={styles.sessionTitle}>{s.title}</span>
            <button
              className={styles.deleteSessionBtn}
              onClick={(e) => onDeleteSession(e, s.id)}
              title="Xoá cuộc trò chuyện"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      {/* Logout */}
      <button
        className={styles.newChatBtn}
        style={{ marginTop: 'auto', marginBottom: 0, justifyContent: 'center' }}
        onClick={onLogout}
      >
        <LogOut size={18} /> Đăng xuất
      </button>
    </div>
  );
}
