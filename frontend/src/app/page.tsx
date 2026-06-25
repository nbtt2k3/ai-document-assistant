'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Menu } from 'lucide-react';

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

  const {
    sessions,
    activeSessionId,
    loadSessions,
    createSession,
    deleteSession,
    selectSession,
    setActiveSessionId,
  } = useSession();

  const {
    messages,
    isStreaming,
    isUploading,
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
  }, []);

  // Load messages khi chuyển session
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
    }
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
    const deleted = await deleteSession(id);
    if (deleted && activeSessionId === id) {
      clearMessages();
    }
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
              messages={messages}
              isStreaming={isStreaming}
              onSuggestionClick={(text) => sendQuery(text)}
            />
            <InputBar
              isStreaming={isStreaming}
              isUploading={isUploading}
              onSend={(text) => sendQuery(text)}
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
    </div>
  );
}
