import { useState } from "react";
import { fetchKakaoLoginUrl } from "@/api/auth";

interface UseKakaoLoginResult {
  login: () => Promise<void>;
  loading: boolean;
  error: string | null;
}

export function useKakaoLogin(): UseKakaoLoginResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = async () => {
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

  return { login, loading, error };
}
