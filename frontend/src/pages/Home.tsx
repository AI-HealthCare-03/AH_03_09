import { BookOpenIcon, MessageCircleIcon, ScanSearchIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";

const features = [
  {
    id: "ocr",
    to: "/upload",
    icon: ScanSearchIcon,
    title: "OCR 스캐너",
    description: "처방전·약봉투를 업로드하면 약물 정보를 자동으로 추출합니다.",
    accent: "bg-violet-100 text-violet-600",
  },
  {
    id: "guide",
    to: "/health-guide",
    icon: BookOpenIcon,
    title: "건강 가이드",
    description: "처방 내용을 기반으로 맞춤형 복약·생활 가이드를 받아보세요.",
    accent: "bg-blue-100 text-blue-600",
  },
  {
    id: "chat",
    to: "/chat",
    icon: MessageCircleIcon,
    title: "AI 챗봇",
    description: "복약 관련 궁금한 점을 AI에게 무엇이든 질문하세요.",
    accent: "bg-emerald-100 text-emerald-600",
  },
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center gap-10 py-8">
      <div className="max-w-lg space-y-3 text-center">
        <div className="mb-2 inline-flex size-16 items-center justify-center rounded-2xl bg-primary text-2xl font-bold text-primary-foreground">
          M
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Medi-Mate</h1>
        <p className="text-muted-foreground">
          AI 기반 복약 관리 서비스로 처방전과 약봉투를 스마트하게 관리하세요.
        </p>
      </div>

      <div className="grid w-full max-w-2xl gap-4 sm:grid-cols-3">
        {features.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => navigate(f.to)}
            className="flex flex-col items-start rounded-xl border bg-card p-5 text-left transition-all hover:border-primary/60 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className={`mb-4 flex size-10 items-center justify-center rounded-lg ${f.accent}`}>
              <f.icon className="size-5" />
            </div>
            <span className="mb-1 font-semibold">{f.title}</span>
            <span className="text-xs leading-relaxed text-muted-foreground">{f.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
