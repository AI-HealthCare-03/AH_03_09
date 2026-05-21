import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchMe, WITHDRAW_CONFIRMATION_TEXT, withdrawMe } from "@/api/user";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

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

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          setConfirming(false);
          setConfirmationText("");
          onClose();
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>내 정보</DialogTitle>
        </DialogHeader>

        {isLoading && <p className="text-sm text-muted-foreground">불러오는 중…</p>}
        {error && <p className="text-sm text-destructive">정보를 불러오지 못했습니다.</p>}

        {data && (
          <dl className="space-y-2 text-sm">
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
          <Button
            type="button"
            variant="outline"
            onClick={() => setConfirming(true)}
            className="w-full border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            회원탈퇴
          </Button>
        ) : (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm">
            <p className="text-destructive">
              회원탈퇴 시 모든 대화 기록이 삭제됩니다. 계속하려면 아래에{" "}
              <strong>{WITHDRAW_CONFIRMATION_TEXT}</strong>를 입력하세요.
            </p>
            <Input
              type="text"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              placeholder={WITHDRAW_CONFIRMATION_TEXT}
              className="mt-3 bg-background"
            />
            {withdrawMut.isError && (
              <p className="mt-2 text-destructive">
                {withdrawMut.error instanceof Error
                  ? withdrawMut.error.message
                  : "오류가 발생했습니다."}
              </p>
            )}
            <div className="mt-3 flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setConfirming(false);
                  setConfirmationText("");
                }}
                className="flex-1"
              >
                취소
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={() => withdrawMut.mutate(confirmationText)}
                disabled={confirmationText !== WITHDRAW_CONFIRMATION_TEXT || withdrawMut.isPending}
                className="flex-1"
              >
                {withdrawMut.isPending ? "처리 중…" : "탈퇴"}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex gap-3">
      <dt className="w-20 shrink-0 text-muted-foreground">{label}</dt>
      <dd className="text-foreground">
        {value || <span className="text-muted-foreground/60">—</span>}
      </dd>
    </div>
  );
}
