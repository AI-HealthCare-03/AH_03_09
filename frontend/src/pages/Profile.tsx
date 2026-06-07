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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/store/authStore";
import type { UserInfoResponse } from "@/types/api";

const dateFormatter = new Intl.DateTimeFormat("ko-KR", { dateStyle: "long" });

export default function Profile() {
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();

  const [withdrawOpen, setWithdrawOpen] = useState(false);
  const [logoutOpen, setLogoutOpen] = useState(false);
  const [termsOpen, setTermsOpen] = useState<"terms" | "privacy" | null>(null);

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
        <CardHeader>
          <CardTitle className="text-base">약관 및 정책</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <Button variant="ghost" className="justify-start text-sm text-slate-600" onClick={() => setTermsOpen("terms")}>
            서비스 이용약관
          </Button>
          <Button variant="ghost" className="justify-start text-sm text-slate-600" onClick={() => setTermsOpen("privacy")}>
            개인정보 수집 및 이용 동의
          </Button>
        </CardContent>
      </Card>

      <Dialog open={termsOpen !== null} onOpenChange={(open) => { if (!open) setTermsOpen(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {termsOpen === "terms" ? "서비스 이용약관" : "개인정보 수집 및 이용 동의"}
            </DialogTitle>
          </DialogHeader>
          <div className="max-h-80 overflow-y-auto text-sm leading-relaxed text-slate-600">
            {termsOpen === "terms" ? (
              <p>
                본 서비스는 AI 기반 복약 가이드 및 건강 정보를 제공합니다. 제공되는 정보는 참고용이며,
                실제 치료·진단을 대체하지 않습니다. 서비스 이용 중 입력하신 데이터는 개인 맞춤형 가이드
                생성에만 활용되며, 외부에 제공되지 않습니다. 만 14세 미만은 서비스를 이용하실 수 없습니다.
              </p>
            ) : (
              <p>
                수집 항목: 카카오 계정 정보(이름, 이메일), 건강정보(성별, 생년월일, 신체정보, 기저질환,
                알레르기, 복용 약물, 생활 습관), 진료 문서(처방전·약봉투 이미지 및 OCR 결과).
                수집 목적: AI 복약 가이드 생성, 챗봇 답변 맞춤화. 보유 기간: 회원 탈퇴 시까지.
                수집된 개인정보는 외부 기관·제3자에게 제공되지 않습니다.
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="text-base">계정 관리</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            variant="outline"
            className="gap-2 text-slate-600"
            onClick={() => setLogoutOpen(true)}
            disabled={logoutMut.isPending}
          >
            <LogOutIcon className="size-4" />
            {logoutMut.isPending ? "로그아웃 중…" : "로그아웃"}
          </Button>

          <Separator />

          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium text-destructive">회원 탈퇴</p>
              <p className="mt-1 text-xs text-destructive/80">
                탈퇴 시 계정 정보, 업로드한 문서, 대화 기록 등 모든 데이터가 영구 삭제되며 복구할 수 없습니다.
              </p>
            </div>
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
          </div>
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
