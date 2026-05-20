import { useState, useEffect, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../api/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // 카카오 로그인 콜백 처리: /?access_token=... 으로 리다이렉트된 경우
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("access_token");
    if (token) {
      localStorage.setItem("access_token", token);
      window.history.replaceState({}, "", "/");
      navigate("/chat");
    }
  }, [navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/chat");
    } catch {
      setError("이메일 또는 비밀번호가 올바르지 않습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>AI 헬스케어</h1>
        <p className="login-subtitle">건강 관리 AI 어시스턴트</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>이메일</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="이메일을 입력하세요"
              required
            />
          </div>
          <div className="form-group">
            <label>비밀번호</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="비밀번호를 입력하세요"
              required
            />
          </div>
          {error && <p className="error-msg">{error}</p>}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "로그인 중..." : "로그인"}
          </button>
        </form>

        <div className="divider"><span>또는</span></div>

        <a href="/api/v1/auth/kakao/login" className="btn-kakao">
          <img src="https://developers.kakao.com/assets/img/about/logos/kakaolink/kakaolink_btn_medium.png" alt="" width={20} height={20} />
          카카오 로그인
        </a>

        <p style={{ textAlign: "center", marginTop: 16, fontSize: 13, color: "#888" }}>
          계정이 없으신가요?{" "}
          <Link to="/register" style={{ color: "#667eea", fontWeight: 600 }}>회원가입</Link>
        </p>
      </div>
    </div>
  );
}
