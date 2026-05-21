import { FileText, MessageCircleHeart, ShieldCheck } from "lucide-react";
import { KakaoLoginButton } from "@/features/auth/KakaoLoginButton";

const HIGHLIGHTS = [
  {
    icon: FileText,
    title: "의료 문서 자동 정리",
    description: "처방전·진단서·건강검진 결과를 업로드하면 AI가 분류·요약합니다.",
  },
  {
    icon: MessageCircleHeart,
    title: "AI 건강 챗봇",
    description: "약 복용, 검사 수치, 증상에 대해 한국어로 바로 물어볼 수 있어요.",
  },
  {
    icon: ShieldCheck,
    title: "내 정보는 내가 관리",
    description: "민감한 의료정보는 동의 절차를 거쳐 안전하게 보관됩니다.",
  },
] as const;

export function HeroSection() {
  return (
    <main className="relative isolate min-h-dvh overflow-hidden bg-background text-foreground">
      <BackgroundDecoration />
      <div className="mx-auto flex min-h-dvh max-w-6xl flex-col px-6 py-10 sm:px-8 lg:px-12 lg:py-16">
        <header className="flex items-center justify-between">
          <span className="text-base font-semibold tracking-tight sm:text-lg">Medi-Mate</span>
          <a
            href="/login"
            className="text-sm font-medium text-muted-foreground transition hover:text-foreground"
          >
            로그인
          </a>
        </header>

        <div className="grid flex-1 items-center gap-12 py-12 lg:grid-cols-2 lg:gap-16 lg:py-20">
          <section className="flex flex-col gap-6 text-center lg:text-left">
            <span className="inline-flex w-fit items-center gap-2 self-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary lg:self-start">
              <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
              의료 AI 어시스턴트 · Medi-Mate
            </span>
            <h1 className="text-3xl font-bold leading-tight tracking-tight sm:text-4xl lg:text-5xl">
              복잡한 의료 문서,
              <br />
              <span className="text-primary">AI가 한 번에</span> 정리합니다.
            </h1>
            <p className="max-w-xl self-center text-base leading-relaxed text-muted-foreground sm:text-lg lg:self-start">
              처방전, 진단서, 건강검진 결과지를 올리면 AI가 자동으로 분류·요약하고, 궁금한 점은
              챗봇이 답해드립니다. 카카오 계정으로 1초 만에 시작하세요.
            </p>

            <div className="flex w-full max-w-sm flex-col gap-3 self-center lg:self-start">
              <KakaoLoginButton label="카카오로 시작하기" size="lg" />
              <p className="text-xs text-muted-foreground">
                계속하면 서비스 이용약관과 개인정보 처리방침에 동의하는 절차가 진행됩니다.
              </p>
            </div>
          </section>

          <section
            aria-label="주요 기능"
            className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1 lg:gap-3"
          >
            {HIGHLIGHTS.map(({ icon: Icon, title, description }) => (
              <article
                key={title}
                className="flex items-start gap-4 rounded-xl border border-border bg-card p-5 shadow-sm"
              >
                <span
                  className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary"
                  aria-hidden="true"
                >
                  <Icon className="size-5" />
                </span>
                <div className="flex flex-col gap-1">
                  <h2 className="text-sm font-semibold text-foreground">{title}</h2>
                  <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
                </div>
              </article>
            ))}
          </section>
        </div>

        <footer className="mt-auto flex flex-col gap-1 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>본 서비스는 의료진의 진단을 대체하지 않습니다. 응급 상황 시 즉시 119에 연락하세요.</p>
          <p>© {new Date().getFullYear()} Medi-Mate</p>
        </footer>
      </div>
    </main>
  );
}

function BackgroundDecoration() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute -top-32 -left-32 size-[28rem] rounded-full bg-primary/10 blur-3xl" />
      <div className="absolute -bottom-32 -right-32 size-[28rem] rounded-full bg-primary/5 blur-3xl" />
    </div>
  );
}
