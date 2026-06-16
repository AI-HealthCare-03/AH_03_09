import { ArrowLeftIcon, ChevronLeftIcon, ChevronRightIcon, LogOutIcon, PlusIcon, Trash2 } from "lucide-react";
import { useState } from "react";
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
  const [isOpen, setIsOpen] = useState(true);
  const currentSessionId = useChatStore((s) => s.currentSessionId);
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);
  const { data: sessions, isLoading } = useSessions();
  const deleteMut = useDeleteSession();

  const handleNew = () => {
    setCurrentSessionId(null);
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
    <aside className={`relative hidden flex-col border-r border-slate-200 bg-white transition-all duration-200 md:flex ${isOpen ? "w-64" : "w-12"}`}>
      {/* 토글 버튼 — h-14 중앙 (top-7 = 28px) */}
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="absolute -right-3 top-7 z-10 grid size-6 place-items-center rounded-full border border-slate-200 bg-white text-slate-400 shadow-sm hover:text-slate-600"
        aria-label={isOpen ? "사이드바 닫기" : "사이드바 열기"}
      >
        {isOpen ? <ChevronLeftIcon className="size-3.5" /> : <ChevronRightIcon className="size-3.5" />}
      </button>

      {isOpen ? (
        <>
          {/* 로고 — AppSidebar 홈 버튼과 동일한 패턴 */}
          <div className="flex h-14 items-center border-b border-slate-200 px-4">
            <button
              type="button"
              onClick={() => navigate("/home")}
              className="flex items-center gap-2 rounded-md px-1.5 py-1 hover:bg-slate-50"
              aria-label="홈으로"
            >
              <span className="grid size-7 shrink-0 place-items-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
                M
              </span>
              <span className="text-sm font-semibold text-slate-800">Medi-Mate</span>
            </button>
          </div>
          <div className="border-b border-slate-100 px-2 py-1">
            <button
              type="button"
              onClick={() => navigate("/home")}
              className="flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm font-medium hover:bg-slate-100 [&>svg]:size-5"
            >
              <ArrowLeftIcon />
              뒤로가기
            </button>
            <button
              type="button"
              onClick={handleNew}
              className="flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm font-medium hover:bg-slate-100 [&>svg]:size-5"
            >
              <PlusIcon />
              새 대화
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
                      className={`block w-full px-4 py-3 pr-10 text-left text-sm font-medium text-slate-700 hover:bg-slate-50 ${
                        s.id === currentSessionId ? "bg-slate-100 font-semibold" : ""
                      }`}
                    >
                      <div className="truncate">{s.title}</div>
                      <div className="mt-1 text-xs font-normal text-slate-400">
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

          {/* p-4 — InputComposer border-t p-4 와 동일 높이 */}
          <div className="border-t border-slate-200 p-4">
            <button
              type="button"
              onClick={onLogout}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-500 hover:bg-slate-50 hover:text-destructive [&>svg]:size-5"
            >
              <LogOutIcon />
              로그아웃
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="flex h-14 items-center justify-center border-b border-slate-200">
            <button
              type="button"
              onClick={() => navigate("/home")}
              className="grid size-7 shrink-0 place-items-center rounded-md bg-primary text-xs font-bold text-primary-foreground hover:opacity-80"
              aria-label="홈으로"
            >
              M
            </button>
          </div>
          <div className="border-b border-slate-100 py-1 flex flex-col items-center gap-0.5">
            <button
              type="button"
              onClick={() => navigate("/home")}
              className="grid size-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-50 hover:text-slate-700"
              aria-label="홈으로"
            >
              <ArrowLeftIcon className="size-4" />
            </button>
            <button
              type="button"
              onClick={handleNew}
              className="grid size-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-50 hover:text-slate-700"
              aria-label="새 대화"
            >
              <PlusIcon className="size-4" />
            </button>
          </div>
          <div className="flex-1" />
          <div className="border-t border-slate-200 p-4 flex items-center justify-center">
            <button
              type="button"
              onClick={onLogout}
              className="grid size-9 place-items-center rounded-lg text-slate-500 hover:bg-red-50 hover:text-red-500"
              aria-label="로그아웃"
            >
              <LogOutIcon className="size-4" />
            </button>
          </div>
        </>
      )}
    </aside>
  );
}
