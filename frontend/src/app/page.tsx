'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Menu, AlertTriangle } from 'lucide-react';

import { getAuthToken, removeAuthToken } from '@/lib/api';
import { useSession } from '@/hooks/useSession';
import { useChat } from '@/hooks/useChat';
import SessionList from '@/components/Sidebar/SessionList';
import ChatWindow from '@/components/Chat/ChatWindow';
import InputBar from '@/components/Chat/InputBar';
import styles from './page.module.css';

export default function ChatPage() {
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false); // For mobile
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false); // For desktop
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);

  const {
    sessions,
    activeSessionId,
    loadSessions,
    createSession,
    updateSessionTitle,
    deleteSession,
    selectSession,
  } = useSession();

  const {
    messages,
    isStreaming,
    isUploading,
    error: chatError,
    loadMessages,
    uploadFile,
    sendQuery,
    clearMessages,
  } = useChat(activeSessionId);

  // Guard: redirect to login if no token
  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.push('/login');
      return;
    }
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  // Load messages khi chuyển session
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

  const handleLogout = () => {
    removeAuthToken();
    router.push('/login');
  };

  const handleCreateSession = async () => {
    const session = await createSession();
    if (session) {
      clearMessages();
      setIsSidebarOpen(false);
    }
  };

  const handleSelectSession = (id: string) => {
    selectSession(id);
    setIsSidebarOpen(false);
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSessionToDelete(id);
  };

  const confirmDelete = async () => {
    if (!sessionToDelete) return;
    const deleted = await deleteSession(sessionToDelete);
    if (deleted && activeSessionId === sessionToDelete) {
      clearMessages();
    }
    setSessionToDelete(null);
  };

  const handleSendQuery = async (text: string) => {
    if (!text.trim()) return;
    
    // Đổi tên nếu tiêu đề vẫn là mặc định
    const currentSession = sessions.find(s => s.id === activeSessionId);
    if (currentSession && currentSession.title.startsWith('Cuộc trò chuyện')) {
      const newTitle = text.length > 30 ? text.slice(0, 30) + '...' : text;
      updateSessionTitle(activeSessionId!, newTitle);
    }
    
    await sendQuery(text);
  };

  return (
    <div className={styles.layout}>
      {/* Mobile Header */}
      <div className={styles.mobileHeader}>
        <button className={styles.menuBtn} onClick={() => setIsSidebarOpen(true)}>
          <Menu size={24} />
        </button>
        <div className={styles.mobileTitle}>AI RAG Assistant</div>
      </div>

      {/* Sidebar Overlay (mobile) */}
      {isSidebarOpen && (
        <div className={styles.sidebarOverlay} onClick={() => setIsSidebarOpen(false)} />
      )}

      {/* Error Toast */}
      {chatError && (
        <div className={styles.errorToast}>
          <AlertTriangle size={18} />
          {chatError}
        </div>
      )}

      {/* Sidebar */}
      <SessionList
        sessions={sessions}
        activeSessionId={activeSessionId}
        isSidebarOpen={isSidebarOpen}
        isCollapsed={isSidebarCollapsed}
        onSelectSession={handleSelectSession}
        onCreateSession={handleCreateSession}
        onDeleteSession={handleDeleteSession}
        onLogout={handleLogout}
        onCloseSidebar={() => {
          if (window.innerWidth <= 768) {
            setIsSidebarOpen(false);
          } else {
            setIsSidebarCollapsed(true);
          }
        }}
      />

      {/* Main Chat Area */}
      <div className={styles.mainArea}>
        {isSidebarCollapsed && (
          <button 
            className={styles.expandSidebarBtn} 
            onClick={() => setIsSidebarCollapsed(false)}
            title="Mở rộng menu"
          >
            <Menu size={20} />
          </button>
        )}
        
        {activeSessionId ? (
          <>
            <ChatWindow
              sessionId={activeSessionId}
              messages={messages}
              isStreaming={isStreaming}
              onSuggestionClick={handleSendQuery}
            />
            <InputBar
              isStreaming={isStreaming}
              isUploading={isUploading}
              onSend={handleSendQuery}
              onFileSelect={(file) => uploadFile(file)}
            />
          </>
        ) : (
          <div className={styles.emptyState}>
            <h2>Không có phiên bản chat nào</h2>
            <p>Vui lòng tạo phiên chat mới ở bên trái.</p>
          </div>
        )}
      </div>

      {/* Custom Delete Modal */}
      {sessionToDelete && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <AlertTriangle size={24} className={styles.modalIcon} />
              <h3>Xoá cuộc trò chuyện</h3>
            </div>
            <p>Bạn có chắc chắn muốn xoá cuộc trò chuyện này không?<br/>Toàn bộ tài liệu tải lên cũng sẽ bị xoá vĩnh viễn.</p>
            <div className={styles.modalActions}>
              <button className={styles.cancelBtn} onClick={() => setSessionToDelete(null)}>
                Hủy
              </button>
              <button className={styles.confirmBtn} onClick={confirmDelete}>
                Xoá
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
