import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

// TODO(feature/fe-landing-bhw): replace with hero + 카카오 로그인 CTA.
export default function Landing() {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (accessToken) {
    return <Navigate to="/home" replace />;
  }
  return (
    <div className="grid min-h-dvh place-items-center bg-background p-4">
      <div className="flex flex-col items-center gap-4 text-center">
        <h1 className="text-3xl font-bold">Medi-Mate</h1>
        <p className="text-muted-foreground">의료 문서 분석 + AI 헬스케어 챗봇</p>
        <a
          href="/login"
          className="inline-flex h-10 items-center rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          시작하기
        </a>
        <p className="text-xs text-muted-foreground">랜딩 페이지 준비 중</p>
      </div>
    </div>
  );
}
