import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CakeIcon,
  CalendarIcon,
  LogOutIcon,
  MailIcon,
  MessageSquareIcon,
  PhoneIcon,
  UserIcon,
} from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { logout } from "@/api/auth";
import { fetchMe, WITHDRAW_CONFIRMATION_TEXT, withdrawMe } from "@/api/user";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/store/authStore";
import type { UserInfoResponse } from "@/types/api";

const dateFormatter = new Intl.DateTimeFormat("ko-KR", { dateStyle: "long" });

export default function Profile() {
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();

  const [withdrawOpen, setWithdrawOpen] = useState(false);
  const [logoutOpen, setLogoutOpen] = useState(false);

  const logoutMut = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      clear();
      navigate("/");
    },
  });
  const [confirmationText, setConfirmationText] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
  });

  const withdrawMut = useMutation({
    mutationFn: withdrawMe,
    onSuccess: () => {
      clear();
      // SPA 네비게이션 대신 풀 리로드로 랜딩(/)으로 이동 — 잔여 상태 초기화.
      window.location.assign("/");
    },
  });

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">내 정보</h1>
        <p className="text-sm text-muted-foreground">
          카카오 계정에서 가져온 정보입니다. 정보 수정은 카카오 계정에서 가능해요.
        </p>
      </header>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="text-base">기본 정보</CardTitle>
          <CardDescription>로그인한 카카오 계정 정보입니다.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? <ProfileSkeleton /> : null}
          {error ? <p className="text-sm text-destructive">정보를 불러오지 못했습니다.</p> : null}
          {data ? <ProfileFields data={data} /> : null}
        </CardContent>
      </Card>

      <Card className="rounded-2xl">
        <CardContent className="pt-6">
          <Button
            variant="outline"
            className="w-full gap-2 text-slate-600"
            onClick={() => setLogoutOpen(true)}
            disabled={logoutMut.isPending}
          >
            <LogOutIcon className="size-4" />
            {logoutMut.isPending ? "로그아웃 중…" : "로그아웃"}
          </Button>
        </CardContent>
      </Card>

      <AlertDialog open={logoutOpen} onOpenChange={setLogoutOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>로그아웃 하시겠어요?</AlertDialogTitle>
            <AlertDialogDescription>
              로그아웃 후 다시 카카오 로그인이 필요합니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={logoutMut.isPending}>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                logoutMut.mutate();
              }}
              disabled={logoutMut.isPending}
            >
              {logoutMut.isPending ? "로그아웃 중…" : "로그아웃"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Card className="rounded-2xl border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base text-destructive">회원 탈퇴</CardTitle>
          <CardDescription className="text-destructive/90">
            탈퇴 시 계정 정보, 업로드한 문서, 대화 기록 등 모든 데이터가 DB에서 영구 삭제되며 복구할
            수 없습니다. 같은 카카오 계정으로 다시 로그인하면 새로 가입한 상태로 시작됩니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setConfirmationText("");
              setWithdrawOpen(true);
            }}
            className="border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            회원탈퇴 진행
          </Button>
        </CardContent>
      </Card>

      <AlertDialog open={withdrawOpen} onOpenChange={setWithdrawOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>정말 탈퇴하시겠어요?</AlertDialogTitle>
            <AlertDialogDescription>
              탈퇴 시 모든 정보가 사라지며 복구할 수 없습니다. 계속하려면 아래에{" "}
              <strong className="text-foreground">{WITHDRAW_CONFIRMATION_TEXT}</strong>를 입력해
              주세요.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Input
            type="text"
            value={confirmationText}
            onChange={(e) => setConfirmationText(e.target.value)}
            placeholder={WITHDRAW_CONFIRMATION_TEXT}
            autoFocus
          />
          {withdrawMut.isError ? (
            <p className="text-sm text-destructive">
              {withdrawMut.error instanceof Error
                ? withdrawMut.error.message
                : "오류가 발생했습니다."}
            </p>
          ) : null}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={withdrawMut.isPending}>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                withdrawMut.mutate(confirmationText);
              }}
              disabled={confirmationText !== WITHDRAW_CONFIRMATION_TEXT || withdrawMut.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {withdrawMut.isPending ? "처리 중…" : "탈퇴"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function ProfileFields({ data }: { data: UserInfoResponse }) {
  return (
    <dl className="grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2">
      <Field icon={UserIcon} label="이름" value={data.name} />
      <Field icon={MailIcon} label="이메일" value={data.email} />
      <Field icon={MessageSquareIcon} label="카카오 ID" value={data.kakao_id} />
      <Field icon={UserIcon} label="성별" value={formatGender(data.gender)} />
      <Field icon={CakeIcon} label="나이대" value={data.age_range} />
      <Field icon={CakeIcon} label="생년" value={data.birthyear} />
      <Field icon={CakeIcon} label="생일" value={formatBirthday(data.birthday)} />
      <Field icon={PhoneIcon} label="전화번호" value={data.phone_number} />
      <Field
        icon={CalendarIcon}
        label="가입일"
        value={data.created_at ? dateFormatter.format(new Date(data.created_at)) : null}
      />
    </dl>
  );
}

function Field({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof UserIcon;
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </span>
      <div className="flex-1">
        <dt className="text-xs text-muted-foreground">{label}</dt>
        <dd className="font-medium">
          {value || <span className="font-normal text-muted-foreground/60">—</span>}
        </dd>
      </div>
    </div>
  );
}

const SKELETON_KEYS = ["s1", "s2", "s3", "s4", "s5", "s6"];

function ProfileSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {SKELETON_KEYS.map((k) => (
        <div key={k} className="flex items-center gap-3">
          <Skeleton className="size-8 rounded-lg" />
          <div className="flex-1 space-y-1">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
      ))}
    </div>
  );
}

function formatGender(g: string | null): string | null {
  if (g === "M" || g === "male") return "남성";
  if (g === "F" || g === "female") return "여성";
  return g;
}

function formatBirthday(b: string | null): string | null {
  if (!b || b.length !== 4) return b;
  return `${b.slice(0, 2)}월 ${b.slice(2, 4)}일`;
}
