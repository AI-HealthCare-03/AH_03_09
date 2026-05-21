import {
  ActivityIcon,
  ArrowRightIcon,
  FileTextIcon,
  MessageCircleHeartIcon,
  PillIcon,
  ShieldCheckIcon,
  SparklesIcon,
  UploadCloudIcon,
} from "lucide-react";
import { KakaoLoginButton } from "@/features/auth/KakaoLoginButton";

export function HeroSection() {
  return (
    <main className="relative isolate min-h-dvh overflow-hidden bg-background text-foreground">
      <BackgroundDecoration />
      <div className="mx-auto flex min-h-dvh max-w-6xl flex-col px-6 py-8 sm:px-8 lg:px-12 lg:py-12">
        <Nav />

        <section className="grid flex-1 items-center gap-10 py-10 lg:grid-cols-[1.05fr_1fr] lg:gap-14 lg:py-14">
          <div className="flex flex-col gap-6 text-center lg:text-left">
            <span className="inline-flex w-fit items-center gap-2 self-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary lg:self-start">
              <SparklesIcon className="size-3.5" />
              의료 AI 어시스턴트 · Medi-Mate
            </span>
            <h1 className="text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl lg:text-[3.5rem]">
              복잡한 의료 문서,
              <br />
              <span className="bg-linear-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                AI가 한 번에
              </span>{" "}
              정리합니다.
            </h1>
            <p className="max-w-xl self-center text-base leading-relaxed text-muted-foreground sm:text-lg lg:self-start">
              처방전·진단서·건강검진 결과지를 올리면 AI가 자동으로 분류·요약하고, 궁금한 점은 챗봇이
              답해드려요. 카카오 계정으로 3초만에 시작하세요.
            </p>

            <div className="flex w-full max-w-sm flex-col gap-3 self-center lg:self-start">
              <KakaoLoginButton label="카카오로 시작하기" size="lg" />
              <p className="text-xs text-muted-foreground">
                별도 가입 없이 카카오 계정 정보로 즉시 시작합니다.
              </p>
            </div>

            <ul className="mt-2 flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-muted-foreground lg:justify-start">
              {["OCR 자동 분석", "24시간 AI 챗봇", "개인정보 암호화", "무료로 시작"].map((item) => (
                <li key={item} className="flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-primary" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <BentoPreview />
        </section>

        <FeatureBento />

        <footer className="mt-10 flex flex-col gap-1 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>본 서비스는 의료진의 진단을 대체하지 않습니다. 응급 상황 시 즉시 119에 연락하세요.</p>
          <p>© {new Date().getFullYear()} Medi-Mate</p>
        </footer>
      </div>
    </main>
  );
}

function Nav() {
  return (
    <header className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-base font-semibold tracking-tight sm:text-lg">
        <span className="grid size-7 place-items-center rounded-lg bg-primary text-primary-foreground text-xs font-bold">
          M
        </span>
        Medi-Mate
      </span>
      <a
        href="/login"
        className="text-sm font-medium text-muted-foreground transition hover:text-foreground"
      >
        로그인
      </a>
    </header>
  );
}

function BentoPreview() {
  return (
    <div className="relative hidden lg:block">
      <div className="grid grid-cols-6 grid-rows-5 gap-3">
        {/* 큰 카드: 업로드 mock */}
        <div className="col-span-4 row-span-3 rounded-2xl border bg-card p-5 shadow-sm">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <UploadCloudIcon className="size-3.5 text-primary" />
            문서 업로드
          </div>
          <div className="mt-3 grid gap-2.5">
            <MockFile name="처방전.pdf" status="분석 완료" tone="success" />
            <MockFile name="혈액검사.png" status="요약 중" tone="warning" />
            <MockFile name="진단서.pdf" status="대기 중" tone="muted" />
          </div>
          <div className="mt-4 rounded-lg bg-primary/8 p-3">
            <p className="text-[11px] font-medium text-primary">AI 요약</p>
            <p className="mt-0.5 text-xs leading-relaxed text-foreground/80">
              총 3건의 의료 문서가 분석되었어요. 가장 최근 처방은 5/18 내과 진료입니다.
            </p>
          </div>
        </div>

        {/* 중간 카드: 혈압 */}
        <div className="col-span-2 row-span-2 rounded-2xl border bg-card p-4 shadow-sm">
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <ActivityIcon className="size-3 text-success" />
            혈압
          </div>
          <div className="mt-2 text-xl font-semibold tabular-nums">
            118<span className="text-base font-normal text-muted-foreground">/76</span>
          </div>
          <div className="mt-3 flex items-end gap-1 h-10">
            {[
              { day: "월", h: 40 },
              { day: "화", h: 65 },
              { day: "수", h: 55 },
              { day: "목", h: 80 },
              { day: "금", h: 70 },
              { day: "토", h: 90 },
              { day: "일", h: 60 },
            ].map(({ day, h }) => (
              <div
                key={day}
                className="flex-1 rounded-sm bg-primary/30"
                style={{ height: `${h}%` }}
              />
            ))}
          </div>
        </div>

        {/* 중간 카드: 복약 */}
        <div className="col-span-2 row-span-3 rounded-2xl border bg-card p-4 shadow-sm">
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <PillIcon className="size-3 text-warning" />
            오늘의 복약
          </div>
          <div className="mt-3 space-y-2.5">
            {[
              { name: "타이레놀", time: "08:00", done: true },
              { name: "오메가-3", time: "09:00", done: true },
              { name: "비타민D", time: "20:00", done: false },
            ].map((m) => (
              <div key={m.name} className="flex items-center gap-2">
                <span className={`size-2 rounded-full ${m.done ? "bg-success" : "bg-border"}`} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium">{m.name}</p>
                  <p className="text-[10px] text-muted-foreground">{m.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 큰 카드: 챗봇 mock */}
        <div className="col-span-4 row-span-2 rounded-2xl border bg-card p-4 shadow-sm">
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <MessageCircleHeartIcon className="size-3 text-primary" />
            AI 챗봇
          </div>
          <div className="mt-2.5 space-y-1.5">
            <div className="max-w-[80%] rounded-lg rounded-bl-sm bg-muted px-3 py-1.5 text-xs">
              처방받은 약 부작용이 뭔가요?
            </div>
            <div className="ml-auto max-w-[85%] rounded-lg rounded-br-sm bg-primary px-3 py-1.5 text-xs text-primary-foreground">
              타이레놀(아세트아미노펜)은 일반적으로 안전하나 과량 복용 시 간 손상…
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MockFile({
  name,
  status,
  tone,
}: {
  name: string;
  status: string;
  tone: "success" | "warning" | "muted";
}) {
  const toneClass =
    tone === "success"
      ? "bg-success/15 text-success"
      : tone === "warning"
        ? "bg-warning/15 text-warning"
        : "bg-muted text-muted-foreground";
  return (
    <div className="flex items-center gap-2.5 rounded-lg border bg-background/50 p-2.5">
      <span className="grid size-8 place-items-center rounded-md bg-muted text-muted-foreground">
        <FileTextIcon className="size-4" />
      </span>
      <span className="flex-1 truncate text-xs font-medium">{name}</span>
      <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${toneClass}`}>
        {status}
      </span>
    </div>
  );
}

const FEATURES = [
  {
    icon: FileTextIcon,
    title: "의료 문서 자동 정리",
    description: "처방전·진단서·검진 결과를 업로드하면 AI가 분류·요약·구조화합니다.",
    accent: "from-primary/15 to-primary/0",
    iconBg: "bg-primary/10 text-primary",
    span: "sm:col-span-2",
  },
  {
    icon: MessageCircleHeartIcon,
    title: "AI 건강 챗봇",
    description: "약 복용, 검사 수치, 증상까지 한국어로 자연스럽게.",
    accent: "from-success/15 to-success/0",
    iconBg: "bg-success/10 text-success",
    span: "",
  },
  {
    icon: ShieldCheckIcon,
    title: "내 정보는 내가 관리",
    description: "민감 정보는 본인 외에는 공개되지 않으며 언제든 삭제할 수 있어요.",
    accent: "from-warning/15 to-warning/0",
    iconBg: "bg-warning/10 text-warning",
    span: "",
  },
  {
    icon: ArrowRightIcon,
    title: "복용·검사 일정 관리",
    description: "분석된 처방 정보로 복약 시간과 다음 진료를 알려드려요.",
    accent: "from-primary/15 to-primary/0",
    iconBg: "bg-primary/10 text-primary",
    span: "sm:col-span-2",
  },
] as const;

function FeatureBento() {
  return (
    <section aria-label="주요 기능" className="grid gap-3 sm:grid-cols-3">
      {FEATURES.map(({ icon: Icon, title, description, accent, iconBg, span }) => (
        <article
          key={title}
          className={`group relative overflow-hidden rounded-2xl border bg-card p-5 shadow-sm transition hover:shadow-md ${span}`}
        >
          <div
            className={`pointer-events-none absolute inset-0 -z-10 bg-linear-to-br ${accent} opacity-70`}
          />
          <span className={`grid size-10 place-items-center rounded-xl ${iconBg}`}>
            <Icon className="size-5" />
          </span>
          <h2 className="mt-4 text-base font-semibold">{title}</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{description}</p>
        </article>
      ))}
    </section>
  );
}

function BackgroundDecoration() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute -top-40 -left-40 size-[32rem] rounded-full bg-primary/10 blur-3xl" />
      <div className="absolute top-1/3 -right-32 size-[28rem] rounded-full bg-success/8 blur-3xl" />
      <div className="absolute -bottom-32 left-1/3 size-[24rem] rounded-full bg-primary/5 blur-3xl" />
    </div>
  );
}
