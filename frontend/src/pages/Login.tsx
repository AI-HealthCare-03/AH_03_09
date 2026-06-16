import { useLocation } from "react-router-dom";
import { KakaoLoginButton } from "@/features/auth/KakaoLoginButton";

export default function Login() {
  const location = useLocation();
  const hasError = (location.state as { loginError?: boolean } | null)?.loginError;

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background p-6 text-foreground">
      <div className="w-full max-w-sm rounded-xl border border-border bg-card p-8 text-center shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight">Medi-Mate</h1>
        <p className="mt-2 text-sm text-muted-foreground">의료 문서 분석 + AI 헬스케어 챗봇</p>
        {hasError && (
          <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            로그인 처리에 실패했습니다. 다시 시도해 주세요.
          </p>
        )}
        <div className="mt-8">
          <KakaoLoginButton />
        </div>
      </div>
    </main>
  );
}
