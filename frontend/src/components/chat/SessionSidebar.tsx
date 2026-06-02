import { useCreateSession, useSessions } from "@/hooks/useSessions";
import { useChatStore } from "@/store/chatStore";

interface Props {
  onProfileClick: () => void;
  onLogout: () => void;
}

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  dateStyle: "short",
  timeStyle: "short",
});

export default function SessionSidebar({ onProfileClick, onLogout }: Props) {
  const currentSessionId = useChatStore((s) => s.currentSessionId);
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);
  const { data: sessions, isLoading } = useSessions();
  const createMut = useCreateSession();

  const handleNew = async () => {
    const session = await createMut.mutateAsync(undefined);
    setCurrentSessionId(session.id);
  };

  return (
    <aside className="flex w-64 flex-col border-r border-slate-200 bg-white">
      <div className="border-b border-slate-200 p-4">
        <button
          type="button"
          onClick={handleNew}
          disabled={createMut.isPending}
          className="w-full rounded-md bg-slate-900 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
        >
          + 새 대화
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <p className="p-4 text-sm text-slate-500">불러오는 중…</p>
        ) : sessions && sessions.length > 0 ? (
          <ul className="divide-y divide-slate-100">
            {/* TODO: 세션 삭제 버튼 추가 — DELETE /api/v1/chat/sessions/{id} 백엔드 구현 완료 */}
            {sessions.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => setCurrentSessionId(s.id)}
                  className={`block w-full px-4 py-3 text-left text-sm hover:bg-slate-50 ${
                    s.id === currentSessionId ? "bg-slate-100 font-medium" : ""
                  }`}
                >
                  <div className="truncate">{s.title}</div>
                  <div className="mt-1 text-xs text-slate-400">
                    {dateFormatter.format(new Date(s.updated_at))}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="p-4 text-sm text-slate-500">대화가 없습니다.</p>
        )}
      </div>

      <div className="space-y-1 border-t border-slate-200 p-3">
        <button
          type="button"
          onClick={onProfileClick}
          className="block w-full rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
        >
          내 정보
        </button>
        <button
          type="button"
          onClick={onLogout}
          className="block w-full rounded-md px-3 py-2 text-left text-sm text-slate-500 hover:bg-slate-50"
        >
          로그아웃
        </button>
      </div>
    </aside>
  );
}
