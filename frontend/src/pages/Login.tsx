import { useState } from "react";
import { fetchKakaoLoginUrl } from "@/api/auth";

export default function Login() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleKakaoLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      const { auth_url } = await fetchKakaoLoginUrl();
      window.location.href = auth_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인 URL을 가져오지 못했습니다.");
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-50 text-slate-900">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-semibold">Medi-Mate</h1>
        <p className="mt-2 text-sm text-slate-500">건강 정보 챗봇</p>
        <button
          type="button"
          onClick={handleKakaoLogin}
          disabled={loading}
          className="mt-8 w-full rounded-md bg-[#FEE500] py-3 text-sm font-medium text-[#191919] hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "이동 중…" : "카카오로 로그인"}
        </button>
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      </div>
    </main>
  );
}
