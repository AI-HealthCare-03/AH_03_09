// Home page
import { useQuery } from "@tanstack/react-query";
import { AlertTriangleIcon, ArrowRightIcon, HeartPulseIcon } from "lucide-react";
import { BookOpenIcon, MessageCircleIcon, ScanSearchIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { fetchDocuments } from "@/api/ocr";
import { fetchMe } from "@/api/user";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuthStore } from "@/store/authStore";
import type { OcrDocumentResponse } from "@/types/api";

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

const DOC_TYPE_LABEL: Record<string, string> = {
  PRESCRIPTION: "처방전",
  DRUG_BAG: "약봉투",
  OTHER: "기타",
};

const STATUS_LABEL: Record<string, string> = {
  PENDING: "대기 중",
  PROCESSING: "처리 중",
  DONE: "완료",
  FAILED: "실패",
};

export default function Home() {
  const navigate = useNavigate();
  const { isOnboarded, medicalProfile } = useAuthStore();

  const { data: meData } = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    staleTime: 5 * 60 * 1000,
  });

  const { data: recentDocs } = useQuery({
    queryKey: ["ocr-documents", "home-recent"],
    queryFn: () => fetchDocuments({ size: 3 }),
    staleTime: 30 * 1000,
  });

  const inProgressDocs = recentDocs?.documents.filter(
    (d) => d.ocr_status === "PENDING" || d.ocr_status === "PROCESSING",
  ) ?? [];

  const showHealthPrompt = isOnboarded && !medicalProfile;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 py-8">
      {/* 환영 메시지 */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">
          안녕하세요{meData?.name ? `, ${meData.name}님` : ""}!
        </h1>
        <p className="text-sm text-muted-foreground">오늘도 건강한 하루 되세요.</p>
      </div>

      {/* 처리 중 문서 배너 */}
      {inProgressDocs.length > 0 && (
        <button
          type="button"
          onClick={() => navigate("/documents")}
          className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-left text-sm text-amber-800 transition-colors hover:bg-amber-100"
        >
          <AlertTriangleIcon className="size-4 shrink-0 text-amber-500" />
          <span className="flex-1">
            처리 중인 문서가 {inProgressDocs.length}개 있어요. 결과를 확인해보세요.
          </span>
          <ArrowRightIcon className="size-4 shrink-0 text-amber-500" />
        </button>
      )}

      {/* 건강정보 미입력 유도 배너 */}
      {showHealthPrompt && (
        <button
          type="button"
          onClick={() => navigate("/health-profile")}
          className="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-left text-sm text-blue-800 transition-colors hover:bg-blue-100"
        >
          <HeartPulseIcon className="size-4 shrink-0 text-blue-500" />
          <span className="flex-1">
            건강정보를 입력하면 더 정확한 복약 가이드를 받을 수 있어요.
          </span>
          <ArrowRightIcon className="size-4 shrink-0 text-blue-500" />
        </button>
      )}

      {/* 기능 카드 */}
      <div className="grid gap-4 sm:grid-cols-3">
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

      {/* 최근 문서 */}
      {(recentDocs?.documents.length ?? 0) > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">최근 문서</h2>
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => navigate("/documents")}>
              전체 보기
            </Button>
          </div>
          <div className="flex flex-col gap-2">
            {recentDocs!.documents.map((doc) => (
              <RecentDocCard key={doc.record_id} doc={doc} onClick={() => {
                if (doc.ocr_status === "DONE") navigate(`/upload/result/${doc.record_id}`);
                else navigate(`/upload/processing/${doc.job_id}`);
              }} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RecentDocCard({ doc, onClick }: { doc: OcrDocumentResponse; onClick: () => void }) {
  const dateStr = new Date(doc.created_at).toLocaleDateString("ko-KR", {
    month: "short",
    day: "numeric",
  });

  return (
    <Card
      className="cursor-pointer rounded-xl transition-shadow hover:shadow-sm"
      onClick={onClick}
    >
      <CardContent className="flex items-center gap-3 p-3">
        <div className="flex flex-1 flex-col gap-0.5 overflow-hidden">
          <span className="truncate text-sm font-medium">{doc.original_filename}</span>
          <span className="text-xs text-muted-foreground">
            {doc.doc_type ? DOC_TYPE_LABEL[doc.doc_type] : "미분류"} · {dateStr}
          </span>
        </div>
        <Badge
          variant={doc.ocr_status === "DONE" ? "default" : doc.ocr_status === "FAILED" ? "destructive" : "secondary"}
          className="shrink-0 text-xs"
        >
          {STATUS_LABEL[doc.ocr_status] ?? doc.ocr_status}
        </Badge>
      </CardContent>
    </Card>
  );
}
