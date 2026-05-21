import {
  ActivityIcon,
  CheckCircle2Icon,
  ClockIcon,
  FileTextIcon,
  HeartPulseIcon,
  PillIcon,
  SparklesIcon,
  UploadCloudIcon,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { type MedicalProfile, useAuthStore } from "@/store/authStore";

const MOCK_DOCS = [
  { id: 1, type: "처방전", name: "내과 진료", date: "5월 18일", status: "분석 완료" },
  { id: 2, type: "약 봉투", name: "감기약", date: "5월 12일", status: "분석 완료" },
  { id: 3, type: "건강검진", name: "정기 검진 결과", date: "4월 30일", status: "검토 필요" },
];

const MOCK_MEDS = [
  { name: "타이레놀 500mg", schedule: "아침·저녁", progress: 60 },
  { name: "오메가-3", schedule: "아침", progress: 90 },
  { name: "비타민 D", schedule: "아침", progress: 30 },
];

export default function Home() {
  const user = useAuthStore((s) => s.user);
  const medicalProfile = useAuthStore((s) => s.medicalProfile);
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          안녕하세요{user?.name ? `, ${user.name}님` : ""} 👋
        </h1>
        <p className="text-sm text-muted-foreground">
          오늘의 건강 리포트와 새로 업로드할 의료 문서를 확인해 보세요.
        </p>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card
          className="group relative cursor-pointer overflow-hidden rounded-2xl border-2 border-dashed border-border bg-card transition hover:border-primary/40 hover:bg-accent/40 lg:col-span-3"
          onClick={() => navigate("/upload")}
          aria-label="문서 업로드 영역"
        >
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,oklch(0.55_0.18_250/0.08),transparent_60%)]" />
          <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <span className="grid size-14 place-items-center rounded-2xl bg-primary/10 text-primary transition group-hover:scale-105">
              <UploadCloudIcon className="size-7" />
            </span>
            <div className="space-y-1">
              <p className="text-base font-medium">파일을 여기에 드래그하거나 클릭해서 업로드</p>
              <p className="text-xs text-muted-foreground">
                지원 형식: PNG · JPG · PDF · 최대 10MB · 한 번에 최대 5개
              </p>
            </div>
            <Button
              type="button"
              size="lg"
              className="mt-2"
              onClick={(e) => {
                e.stopPropagation();
                navigate("/upload");
              }}
            >
              파일 선택
            </Button>
          </CardContent>
        </Card>

        <ReportCard className="lg:col-span-2" medicalProfile={medicalProfile} />

        <RecentDocsCard />

        <MedicationCard />

        <TipsCard />
      </div>
    </div>
  );
}

function ReportCard({
  className,
  medicalProfile,
}: {
  className?: string;
  medicalProfile: MedicalProfile | null;
}) {
  const today = new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date());

  return (
    <Card className={`relative overflow-hidden rounded-2xl ${className ?? ""}`}>
      <div className="absolute inset-0 -z-10 bg-[linear-gradient(135deg,oklch(0.55_0.18_250/0.1),transparent_55%)]" />
      <CardContent className="space-y-5 p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <Badge variant="secondary" className="rounded-full">
              <SparklesIcon className="size-3" />
              오늘의 건강 리포트
            </Badge>
            <h2 className="mt-2 text-xl font-semibold tracking-tight">{today}</h2>
          </div>
          <Link to="/health-profile" className="text-xs font-medium text-primary hover:underline">
            건강정보 보기 →
          </Link>
        </div>

        <p className="text-sm leading-relaxed text-muted-foreground">
          {medicalProfile
            ? "최근 업로드한 처방전 기준으로 복용 알림과 일일 건강 팁을 정리했어요."
            : "내 건강정보를 입력하면 더 정확한 맞춤 리포트를 받을 수 있어요."}
        </p>

        <div className="grid gap-3 sm:grid-cols-3">
          <Metric
            icon={HeartPulseIcon}
            label="혈압"
            value={
              medicalProfile?.bloodPressure
                ? `${medicalProfile.bloodPressure.systolic}/${medicalProfile.bloodPressure.diastolic}`
                : "—"
            }
            unit="mmHg"
            accent="text-primary"
          />
          <Metric
            icon={ActivityIcon}
            label="BMI"
            value={
              medicalProfile
                ? (medicalProfile.weightKg / (medicalProfile.heightCm / 100) ** 2).toFixed(1)
                : "—"
            }
            unit=""
            accent="text-success"
          />
          <Metric icon={PillIcon} label="복용 중" value="3" unit="종" accent="text-warning" />
        </div>

        <div className="rounded-xl bg-muted/60 p-4">
          <p className="text-xs font-medium text-muted-foreground">오늘의 한 줄</p>
          <p className="mt-1 text-sm leading-relaxed">
            식후 30분, 처방받은 약을 잊지 말고 복용해주세요. 수분 섭취는 하루 1.5L 이상 권장돼요.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  unit,
  accent,
}: {
  icon: typeof ActivityIcon;
  label: string;
  value: string;
  unit: string;
  accent: string;
}) {
  return (
    <div className="rounded-xl border bg-card/60 p-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className={`size-3.5 ${accent}`} />
        {label}
      </div>
      <div className="mt-1 text-xl font-semibold tabular-nums">
        {value}
        {unit ? (
          <span className="ml-1 text-xs font-normal text-muted-foreground">{unit}</span>
        ) : null}
      </div>
    </div>
  );
}

function RecentDocsCard() {
  return (
    <Card className="rounded-2xl">
      <CardContent className="space-y-4 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="grid size-8 place-items-center rounded-lg bg-primary/10 text-primary">
              <FileTextIcon className="size-4" />
            </span>
            <h3 className="text-sm font-semibold">최근 문서</h3>
          </div>
          <Link to="/documents" className="text-xs text-muted-foreground hover:text-foreground">
            전체 보기
          </Link>
        </div>
        <ul className="space-y-3">
          {MOCK_DOCS.map((doc) => (
            <li key={doc.id} className="flex items-center gap-3">
              <span className="grid size-9 place-items-center rounded-lg bg-muted text-muted-foreground">
                <FileTextIcon className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{doc.name}</p>
                <p className="text-xs text-muted-foreground">
                  {doc.type} · {doc.date}
                </p>
              </div>
              <Badge
                variant={doc.status === "분석 완료" ? "secondary" : "outline"}
                className="rounded-full text-xs"
              >
                {doc.status}
              </Badge>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function MedicationCard() {
  return (
    <Card className="rounded-2xl">
      <CardContent className="space-y-4 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="grid size-8 place-items-center rounded-lg bg-warning/15 text-warning">
              <PillIcon className="size-4" />
            </span>
            <h3 className="text-sm font-semibold">복용 알림</h3>
          </div>
          <span className="text-xs text-muted-foreground">이번 주</span>
        </div>
        <ul className="space-y-4">
          {MOCK_MEDS.map((med) => (
            <li key={med.name} className="space-y-1.5">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{med.name}</span>
                <span className="text-xs text-muted-foreground">{med.schedule}</span>
              </div>
              <Progress value={med.progress} className="h-1.5" />
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function TipsCard() {
  return (
    <Card className="rounded-2xl bg-linear-to-br from-primary/10 via-primary/5 to-transparent">
      <CardContent className="space-y-3 p-6">
        <div className="flex items-center gap-2">
          <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
            <SparklesIcon className="size-4" />
          </span>
          <h3 className="text-sm font-semibold">AI 챗봇과 대화</h3>
        </div>
        <p className="text-sm leading-relaxed text-muted-foreground">
          처방받은 약의 부작용, 식이 주의사항, 검사 결과 해석까지 — 궁금한 점을 바로 물어보세요.
        </p>
        <ul className="space-y-2 text-sm">
          <li className="flex items-start gap-2">
            <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-success" />
            <span>처방전 분석 결과 자동 요약</span>
          </li>
          <li className="flex items-start gap-2">
            <ClockIcon className="mt-0.5 size-4 shrink-0 text-warning" />
            <span>복약 시간 맞춤 알림</span>
          </li>
        </ul>
        <Button asChild variant="default" size="sm" className="mt-2 w-full">
          <Link to="/chat">챗봇 열기</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
