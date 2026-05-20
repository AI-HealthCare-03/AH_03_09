import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signup } from "../api/auth";

export default function RegisterPage() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    name: "",
    gender: "MALE" as "MALE" | "FEMALE",
    birth_date: "",
    phone_number: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const set = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signup(form);
      navigate("/", { state: { registered: true } });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "회원가입에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card" style={{ maxWidth: 480 }}>
        <h1>회원가입</h1>
        <p className="login-subtitle">AI 헬스케어 서비스에 오신 것을 환영합니다</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>이메일</label>
            <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="이메일" required />
          </div>
          <div className="form-group">
            <label>비밀번호 <span style={{ color: "#aaa", fontWeight: 400 }}>(8자 이상, 영문+숫자+특수문자)</span></label>
            <input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} placeholder="비밀번호" required minLength={8} />
          </div>
          <div className="form-group">
            <label>이름</label>
            <input type="text" value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="이름" required maxLength={20} />
          </div>
          <div className="form-row">
            <div className="form-group" style={{ flex: 1 }}>
              <label>성별</label>
              <select value={form.gender} onChange={(e) => set("gender", e.target.value)} className="form-select">
                <option value="MALE">남성</option>
                <option value="FEMALE">여성</option>
              </select>
            </div>
            <div className="form-group" style={{ flex: 2 }}>
              <label>생년월일</label>
              <input type="date" value={form.birth_date} onChange={(e) => set("birth_date", e.target.value)} required />
            </div>
          </div>
          <div className="form-group">
            <label>전화번호 <span style={{ color: "#aaa", fontWeight: 400 }}>(-없이 입력)</span></label>
            <input type="tel" value={form.phone_number} onChange={(e) => set("phone_number", e.target.value)} placeholder="01012345678" required />
          </div>
          {error && <p className="error-msg">{error}</p>}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "가입 중..." : "회원가입"}
          </button>
        </form>
        <p style={{ textAlign: "center", marginTop: 16, fontSize: 13, color: "#888" }}>
          이미 계정이 있으신가요?{" "}
          <Link to="/" style={{ color: "#667eea", fontWeight: 600 }}>로그인</Link>
        </p>
      </div>
    </div>
  );
}
