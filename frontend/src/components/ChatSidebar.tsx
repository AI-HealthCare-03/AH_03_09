import { useEffect, useState } from "react";
import { getSessions, createSession, deleteSession } from "../api/chat";
import type { ChatSession } from "../types";

interface Props {
  selectedId: number | null;
  onSelect: (session: ChatSession) => void;
  onNewSession: (session: ChatSession) => void;
  refreshKey: number;
}

export default function ChatSidebar({ selectedId, onSelect, onNewSession, refreshKey }: Props) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  useEffect(() => {
    getSessions()
      .then((res) => setSessions(res.data))
      .catch(() => {});
  }, [refreshKey]);

  const handleNew = async () => {
    const res = await createSession("새 채팅");
    setSessions((prev) => [res.data, ...prev]);
    onNewSession(res.data);
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
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
        {sessions.length === 0 && (
          <li className="session-empty">채팅을 시작해보세요</li>
        )}
      </ul>
    </aside>
  );
}
