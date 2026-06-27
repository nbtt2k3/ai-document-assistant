'use client';

import { useEffect, useState } from 'react';
import { X, BookOpen, Loader2 } from 'lucide-react';
import { getAuthToken } from '@/lib/api';
import styles from './TOCModal.module.css';

interface TOCItem {
  level: number;
  title: string;
}

interface TOCModalProps {
  sessionId: string;
  onClose: () => void;
  onSummarize: (title: string, level: number) => void;
}

const API_BASE = 'http://127.0.0.1:8000/api';

export default function TOCModal({ sessionId, onClose, onSummarize }: TOCModalProps) {
  const [toc, setToc] = useState<TOCItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchTOC = async () => {
      try {
        const token = getAuthToken();
        const res = await fetch(`${API_BASE}/sessions/${sessionId}/toc`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Không thể lấy mục lục');
        const data = await res.json();
        setToc(data.toc || []);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError(String(err));
        }
      } finally {
        setLoading(false);
      }
    };

    fetchTOC();
  }, [sessionId]);

  const handleSummarize = (title: string, level: number) => {
    onSummarize(title, level);
    onClose();
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <div className={styles.titleWrapper}>
            <BookOpen size={20} className={styles.icon} />
            <h3>Mục lục tài liệu</h3>
          </div>
          <button className={styles.closeBtn} onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className={styles.modalBody}>
          {loading ? (
            <div className={styles.loadingState}>
              <Loader2 className={styles.spinner} size={24} />
              <p>Đang tải mục lục...</p>
            </div>
          ) : error ? (
            <div className={styles.errorState}>
              <p>{error}</p>
            </div>
          ) : toc.length === 0 ? (
            <div className={styles.emptyState}>
              <p>Chưa có mục lục nào được nhận diện từ tài liệu này.</p>
              <span className={styles.hint}>Lưu ý: Chỉ tài liệu có định dạng Heading rõ ràng mới hiển thị mục lục.</span>
            </div>
          ) : (
            <ul className={styles.tocList}>
              {toc.map((item, idx) => (
                <li 
                  key={idx} 
                  className={styles.tocItem}
                  style={{ marginLeft: `${(item.level - 1) * 20}px` }}
                >
                  <span className={styles.tocTitle} title={item.title}>
                    {item.title}
                  </span>
                  <button 
                    className={styles.summarizeBtn}
                    onClick={() => handleSummarize(item.title, item.level)}
                  >
                    Tóm tắt
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
