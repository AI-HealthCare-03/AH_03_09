import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchMe, WITHDRAW_CONFIRMATION_TEXT, withdrawMe } from "@/api/user";

interface Props {
  open: boolean;
  onClose: () => void;
  onWithdrawn: () => void;
}

const dateFormatter = new Intl.DateTimeFormat("ko-KR", { dateStyle: "long" });

export default function ProfileModal({ open, onClose, onWithdrawn }: Props) {
  const [confirming, setConfirming] = useState(false);
  const [confirmationText, setConfirmationText] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    enabled: open,
  });

  const withdrawMut = useMutation({
    mutationFn: withdrawMe,
    onSuccess: onWithdrawn,
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">내 정보</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="text-slate-400 hover:text-slate-600"
          >
            ✕
          </button>
        </div>

        {isLoading && <p className="mt-4 text-sm text-slate-500">불러오는 중…</p>}
        {error && <p className="mt-4 text-sm text-red-600">정보를 불러오지 못했습니다.</p>}

        {data && (
          <dl className="mt-4 space-y-2 text-sm">
            <Row label="이름" value={data.name} />
            <Row label="이메일" value={data.email} />
            <Row label="카카오 ID" value={data.kakao_id} />
            <Row label="성별" value={data.gender} />
            <Row label="나이대" value={data.age_range} />
            <Row
              label="가입일"
              value={data.created_at ? dateFormatter.format(new Date(data.created_at)) : null}
            />
          </dl>
        )}

        {!confirming ? (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="mt-6 w-full rounded-md border border-red-200 py-2 text-sm text-red-600 hover:bg-red-50"
          >
            회원탈퇴
          </button>
        ) : (
          <div className="mt-6 rounded-md border border-red-200 bg-red-50 p-4 text-sm">
            <p className="text-red-700">
              회원탈퇴 시 모든 대화 기록이 삭제됩니다. 계속하려면 아래에{" "}
              <strong>{WITHDRAW_CONFIRMATION_TEXT}</strong>를 입력하세요.
            </p>
            <input
              type="text"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              placeholder={WITHDRAW_CONFIRMATION_TEXT}
              className="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            />
            {withdrawMut.isError && (
              <p className="mt-2 text-red-700">
                {withdrawMut.error instanceof Error
                  ? withdrawMut.error.message
                  : "오류가 발생했습니다."}
              </p>
            )}
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setConfirming(false);
                  setConfirmationText("");
                }}
                className="flex-1 rounded-md border border-slate-300 py-2 text-sm text-slate-700 hover:bg-slate-50"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => withdrawMut.mutate(confirmationText)}
                disabled={confirmationText !== WITHDRAW_CONFIRMATION_TEXT || withdrawMut.isPending}
                className="flex-1 rounded-md bg-red-600 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {withdrawMut.isPending ? "처리 중…" : "탈퇴"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex gap-3">
      <dt className="w-20 shrink-0 text-slate-500">{label}</dt>
      <dd className="text-slate-900">{value || <span className="text-slate-400">—</span>}</dd>
    </div>
  );
}
