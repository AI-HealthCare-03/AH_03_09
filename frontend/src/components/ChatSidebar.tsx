import { useEffect, useState } from "react";
import { fetchSessions, createSession, deleteSession } from "../api/chat";
import type { ChatSessionResponse } from "@/types/api";

interface Props {
  selectedId: string | null;
  onSelect: (session: ChatSessionResponse) => void;
  onNewSession: (session: ChatSessionResponse) => void;
  refreshKey: number;
}

export default function ChatSidebar({ selectedId, onSelect, onNewSession, refreshKey }: Props) {
  const [sessions, setSessions] = useState<ChatSessionResponse[]>([]);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    setLoadError(false);
    fetchSessions()
      .then((data) => setSessions(data))
      .catch(() => setLoadError(true));
  }, [refreshKey]);

  const handleNew = async () => {
    const session = await createSession("새 채팅");
    setSessions((prev) => [session, ...prev]);
    onNewSession(session);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await deleteSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-title">채팅 목록</span>
        <button className="btn-new" onClick={handleNew} title="새 채팅">
          ＋
        </button>
      </div>
      <ul className="session-list">
        {loadError && (
          <li className="session-error">목록을 불러오지 못했습니다.</li>
        )}
        {sessions.map((s) => (
          <li
            key={s.id}
            className={`session-item ${s.id === selectedId ? "active" : ""}`}
            onClick={() => onSelect(s)}
          >
            <span className="session-title">{s.title}</span>
            <button
              className="btn-delete"
              onClick={(e) => handleDelete(e, s.id)}
              title="삭제"
            >
              ✕
            </button>
          </li>
        ))}
        {sessions.length === 0 && !loadError && (
          <li className="session-empty">채팅을 시작해보세요</li>
        )}
      </ul>
    </aside>
  );
}
