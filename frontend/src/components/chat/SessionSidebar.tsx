import { HomeIcon, LogOutIcon, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useDeleteSession, useSessions } from "@/hooks/useSessions";
import { useChatStore } from "@/store/chatStore";

interface Props {
  onLogout: () => void;
}

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  dateStyle: "short",
  timeStyle: "short",
});

export default function SessionSidebar({ onLogout }: Props) {
  const navigate = useNavigate();
  const currentSessionId = useChatStore((s) => s.currentSessionId);
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);
  const setGuideId = useChatStore((s) => s.setGuideId);
  const { data: sessions, isLoading } = useSessions();
  const deleteMut = useDeleteSession();

  const handleNew = () => {
    setCurrentSessionId(null);
    setGuideId(null);
  };

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (!window.confirm("이 대화를 삭제하시겠습니까? 삭제 후 복구할 수 없습니다.")) return;
    await deleteMut.mutateAsync(sessionId);
    if (currentSessionId === sessionId) {
      setCurrentSessionId(null);
    }
  };

  return (
    <aside className="hidden w-64 flex-col border-r border-slate-200 bg-white md:flex">
      <div className="flex flex-col gap-2 border-b border-slate-200 p-4">
        <button
          type="button"
          onClick={handleNew}
          className="w-full rounded-md bg-slate-900 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
        >
          + 새 대화
        </button>
        <button
          type="button"
          onClick={() => navigate("/home")}
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
        >
          <HomeIcon className="size-4" />
          홈으로
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <p className="p-4 text-sm text-slate-500">불러오는 중…</p>
        ) : sessions && sessions.length > 0 ? (
          <ul className="divide-y divide-slate-100">
            {sessions.map((s) => (
              <li key={s.id} className="group relative">
                <button
                  type="button"
                  onClick={() => setCurrentSessionId(s.id)}
                  className={`block w-full px-4 py-3 pr-10 text-left text-sm hover:bg-slate-50 ${
                    s.id === currentSessionId ? "bg-slate-100 font-medium" : ""
                  }`}
                >
                  <div className="truncate">{s.title}</div>
                  <div className="mt-1 text-xs text-slate-400">
                    {dateFormatter.format(new Date(s.updated_at))}
                  </div>
                </button>
                <button
                  type="button"
                  onClick={(e) => handleDelete(e, s.id)}
                  disabled={deleteMut.isPending}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-500 group-hover:opacity-100 disabled:opacity-40"
                  aria-label="대화 삭제"
                >
                  <Trash2 className="size-4" />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="p-4 text-sm text-slate-500">대화가 없습니다.</p>
        )}
      </div>

      <div className="border-t border-slate-200 p-3">
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-500 hover:text-destructive hover:bg-slate-50 [&>svg]:size-5"
        >
          <LogOutIcon />
          로그아웃
        </button>
      </div>
    </aside>
  );
}
