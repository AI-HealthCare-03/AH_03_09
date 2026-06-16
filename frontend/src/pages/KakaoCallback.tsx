import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { exchangeKakaoCode } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";

export default function KakaoCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const setAuthenticated = useAuthStore((s) => s.setAuthenticated);
  const setIsOnboarded = useAuthStore((s) => s.setIsOnboarded);
  const [error, setError] = useState<string | null>(null);
  // Kakao OAuth code는 1회용 — StrictMode dev 더블 실행 시 두 번째 호출이 400으로 떨어지는 것을 막는다.
  const exchangedCodeRef = useRef<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("인증 코드가 없습니다.");
      return;
    }
    if (exchangedCodeRef.current === code) return;
    exchangedCodeRef.current = code;

    exchangeKakaoCode(code)
      .then(({ is_onboarded }) => {
        setAuthenticated(true);
        setIsOnboarded(is_onboarded);
        navigate(is_onboarded ? "/home" : "/onboarding", { replace: true });
      })
      .catch(() => {
        // URL에 만료된 code가 남아 탭 재오픈 시 동일 에러가 반복되는 문제 방지
        // 로그인 페이지로 이동해 재시도 유도
        navigate("/login", { replace: true, state: { loginError: true } });
      });
  }, [searchParams, navigate, setAuthenticated, setIsOnboarded]);

  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-50 text-slate-900">
      {error ? (
        <div className="text-center">
          <p className="text-sm text-red-600">{error}</p>
          <a href="/login" className="mt-4 inline-block text-sm text-blue-600 hover:underline">
            로그인으로 돌아가기
          </a>
        </div>
      ) : (
        <p className="text-sm text-slate-500">카카오 로그인 처리 중…</p>
      )}
    </main>
  );
}
