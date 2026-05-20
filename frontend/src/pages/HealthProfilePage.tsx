import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getHealthProfile, updateHealthProfile, type HealthProfileData } from "../api/healthProfile";

const EXERCISE_OPTIONS = [
  { value: "REGULAR", label: "규칙적 (주 3회 이상)" },
  { value: "IRREGULAR", label: "비규칙적" },
  { value: "NONE", label: "운동 안 함" },
];

const ALCOHOL_OPTIONS = [
  { value: "NONE", label: "음주 안 함" },
  { value: "MODERATE", label: "가끔 (주 1~2회)" },
  { value: "HEAVY", label: "자주 (주 3회 이상)" },
];

export default function HealthProfilePage() {
  const [profile, setProfile] = useState<HealthProfileData | null>(null);
  const [form, setForm] = useState<HealthProfileData>({
    primary_conditions: [],
    allergies: [],
    current_medications: [],
    lifestyle_exercise: "NONE",
    lifestyle_smoking: false,
    lifestyle_alcohol: "NONE",
  });
  const [inputValues, setInputValues] = useState({ condition: "", allergy: "", medication: "" });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    getHealthProfile()
      .then((res) => {
        setProfile(res.data);
        setForm(res.data);
      })
      .catch(() => navigate("/"));
  }, [navigate]);

  const addItem = (field: "primary_conditions" | "allergies" | "current_medications", key: keyof typeof inputValues) => {
    const val = inputValues[key].trim();
    if (!val) return;
    setForm((prev) => ({ ...prev, [field]: [...prev[field], val] }));
    setInputValues((prev) => ({ ...prev, [key]: "" }));
  };

  const removeItem = (field: "primary_conditions" | "allergies" | "current_medications", idx: number) => {
    setForm((prev) => ({ ...prev, [field]: prev[field].filter((_, i) => i !== idx) }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateHealthProfile(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (!profile) return <div className="chat-placeholder"><p>불러오는 중...</p></div>;

  return (
    <div className="profile-page">
      <div className="profile-card">
        <div className="profile-header">
          <button className="btn-back" onClick={() => navigate("/chat")}>← 챗봇으로</button>
          <h1>건강 프로필</h1>
          <p className="login-subtitle">입력한 정보는 AI 챗봇 답변에 활용됩니다</p>
        </div>

        <section className="profile-section">
          <h3>진단명</h3>
          <TagInput
            items={form.primary_conditions}
            inputValue={inputValues.condition}
            onInputChange={(v) => setInputValues((p) => ({ ...p, condition: v }))}
            onAdd={() => addItem("primary_conditions", "condition")}
            onRemove={(i) => removeItem("primary_conditions", i)}
            placeholder="예: 고혈압, 당뇨"
          />
        </section>

        <section className="profile-section">
          <h3>알레르기</h3>
          <TagInput
            items={form.allergies}
            inputValue={inputValues.allergy}
            onInputChange={(v) => setInputValues((p) => ({ ...p, allergy: v }))}
            onAdd={() => addItem("allergies", "allergy")}
            onRemove={(i) => removeItem("allergies", i)}
            placeholder="예: 페니실린, 땅콩"
          />
        </section>

        <section className="profile-section">
          <h3>복용 중인 약물</h3>
          <TagInput
            items={form.current_medications}
            inputValue={inputValues.medication}
            onInputChange={(v) => setInputValues((p) => ({ ...p, medication: v }))}
            onAdd={() => addItem("current_medications", "medication")}
            onRemove={(i) => removeItem("current_medications", i)}
            placeholder="예: 아스피린 100mg"
          />
        </section>

        <section className="profile-section">
          <h3>생활 습관</h3>
          <div className="profile-lifestyle">
            <div className="form-group">
              <label>운동 습관</label>
              <select
                className="form-select"
                value={form.lifestyle_exercise}
                onChange={(e) => setForm((p) => ({ ...p, lifestyle_exercise: e.target.value as HealthProfileData["lifestyle_exercise"] }))}
              >
                {EXERCISE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>흡연 여부</label>
              <div className="toggle-group">
                <button
                  className={`toggle-btn ${!form.lifestyle_smoking ? "active" : ""}`}
                  onClick={() => setForm((p) => ({ ...p, lifestyle_smoking: false }))}
                  type="button"
                >비흡연</button>
                <button
                  className={`toggle-btn ${form.lifestyle_smoking ? "active" : ""}`}
                  onClick={() => setForm((p) => ({ ...p, lifestyle_smoking: true }))}
                  type="button"
                >흡연</button>
              </div>
            </div>
            <div className="form-group">
              <label>음주 습관</label>
              <select
                className="form-select"
                value={form.lifestyle_alcohol}
                onChange={(e) => setForm((p) => ({ ...p, lifestyle_alcohol: e.target.value as HealthProfileData["lifestyle_alcohol"] }))}
              >
                {ALCOHOL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>
        </section>

        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "저장 중..." : saved ? "✓ 저장됐습니다!" : "저장하기"}
        </button>
      </div>
    </div>
  );
}

function TagInput({ items, inputValue, onInputChange, onAdd, onRemove, placeholder }: {
  items: string[];
  inputValue: string;
  onInputChange: (v: string) => void;
  onAdd: () => void;
  onRemove: (i: number) => void;
  placeholder: string;
}) {
  return (
    <div>
      <div className="tag-list">
        {items.map((item, i) => (
          <span key={i} className="tag">
            {item}
            <button onClick={() => onRemove(i)}>✕</button>
          </span>
        ))}
      </div>
      <div className="tag-input-row">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), onAdd())}
          placeholder={placeholder}
          className="chat-input"
          style={{ flex: 1, maxHeight: "unset" }}
        />
        <button className="btn-send" onClick={onAdd} type="button">추가</button>
      </div>
    </div>
  );
}
