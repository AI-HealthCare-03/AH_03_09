import { motion, type Variants } from "framer-motion";
import {
  BookOpenIcon,
  FileTextIcon,
  MessageCircleHeartIcon,
  PillIcon,
  ShieldCheckIcon,
  SparklesIcon,
  UploadCloudIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { KakaoLoginButton } from "@/features/auth/KakaoLoginButton";

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.65, ease: "easeOut", delay: 0.15 + i * 0.15 },
  }),
};

export function HeroSection() {
  return (
    <main className="relative isolate min-h-dvh overflow-hidden bg-background text-foreground">
      <BackgroundDecoration />
      <div className="mx-auto flex min-h-dvh max-w-6xl flex-col px-6 py-8 sm:px-8 lg:px-12 lg:py-12">
        <Nav />

        <section className="grid flex-1 items-center gap-10 py-10 lg:grid-cols-[1.05fr_1fr] lg:gap-14 lg:py-14">
          {/* 히어로 텍스트 */}
          <div className="flex flex-col gap-6 text-center lg:text-left">
            {[
              <motion.span
                key="badge"
                custom={0}
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                className="inline-flex w-fit items-center gap-2 self-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary lg:self-start"
              >
                <SparklesIcon className="size-3.5" />
                의료 AI 어시스턴트 · Medi-Mate
              </motion.span>,
              <motion.h1
                key="title"
                custom={1}
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                className="text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl lg:text-[3.5rem]"
              >
                처방전·약봉투를 찍으면,
                <br />
                <span className="bg-linear-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                  AI가 다 알아서
                </span>
              </motion.h1>,
              <motion.p
                key="desc"
                custom={2}
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                className="max-w-xl self-center text-base leading-relaxed text-muted-foreground sm:text-lg lg:self-start"
              >
                처방받은 약이 어떤 약인지 몰라도 괜찮아요. AI가 약물 정보를 한눈에 정리하고,
                맞춤 복약 및 생활 가이드와 AI 챗봇으로 건강을 도와드려요.
              </motion.p>,
              <motion.div
                key="cta"
                custom={3}
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                className="flex w-full max-w-sm flex-col gap-3 self-center lg:self-start"
              >
                <KakaoLoginButton label="카카오로 시작하기" size="lg" />
                <p className="text-xs text-muted-foreground">
                  별도 가입 없이 카카오 계정 정보로 즉시 시작합니다.
                </p>
              </motion.div>,
              <motion.ul
                key="bullets"
                custom={4}
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                className="mt-2 flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-muted-foreground lg:justify-start"
              >
                {["OCR 자동 분석", "맞춤형 복약 가이드", "AI 건강 챗봇", "무료로 시작"].map((item) => (
                  <li key={item} className="flex items-center gap-1.5">
                    <span className="size-1.5 rounded-full bg-primary" />
                    {item}
                  </li>
                ))}
              </motion.ul>,
            ]}
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
    <motion.header
      className="flex items-center justify-between"
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
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
    </motion.header>
  );
}

function BentoPreview() {
  return (
    <div className="relative hidden lg:block">
      <div className="grid grid-cols-6 grid-rows-5 gap-3">

        {/* 큰 카드: 업로드 */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.4, ease: "easeOut" }}
          className="col-span-4 row-span-3 rounded-2xl border bg-card p-5 shadow-sm"
        >
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <UploadCloudIcon className="size-3.5 text-primary" />
            문서 업로드
          </div>
          <div className="mt-3 grid gap-2.5">
            <MockFile name="처방전.pdf" status="완료" tone="success" />
            <MockFile name="약봉투.jpg" status="처리 중" tone="warning" />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-medium text-primary">처방전</span>
            <span className="rounded-full bg-success/10 px-2.5 py-1 text-[10px] font-medium text-success">신뢰도 94%</span>
            <span className="text-[10px] text-muted-foreground">약물 3종 추출</span>
          </div>
        </motion.div>

        {/* 복약 가이드 */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.52, ease: "easeOut" }}
          className="col-span-2 row-span-2 rounded-2xl border bg-card p-4 shadow-sm"
        >
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <BookOpenIcon className="size-3 text-primary" />
            복약 가이드
          </div>
          <div className="mt-2 space-y-1.5">
            <div className="rounded-lg bg-primary/8 px-2.5 py-1.5">
              <p className="text-[11px] font-semibold text-primary">💊 복약</p>
              <p className="mt-0.5 text-[11px] leading-snug text-foreground/80">하루 1회 식후 복용</p>
            </div>
            <div className="rounded-lg bg-success/8 px-2.5 py-1.5">
              <p className="text-[11px] font-semibold text-success">🏃 생활</p>
              <p className="mt-0.5 text-[11px] leading-snug text-foreground/80">규칙적 운동 권장</p>
            </div>
          </div>
        </motion.div>

        {/* 약물 목록 */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.6, ease: "easeOut" }}
          className="col-span-2 row-span-3 rounded-2xl border bg-card p-4 shadow-sm"
        >
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <PillIcon className="size-3 text-warning" />
            약물 목록
          </div>
          <div className="mt-3 space-y-2">
            {[
              { name: "암로디핀정 5mg", detail: "1일 1회 · 식후 30분" },
              { name: "메트포르민 500mg", detail: "1일 2회 · 식후" },
              { name: "아스피린 100mg", detail: "1일 1회 · 아침" },
            ].map(({ name, detail }) => (
              <div key={name} className="rounded-lg border bg-background/50 px-2.5 py-2">
                <p className="truncate text-xs font-medium">{name}</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">{detail}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* AI 챗봇 */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.68, ease: "easeOut" }}
          className="col-span-4 row-span-2 rounded-2xl border bg-card p-4 shadow-sm"
        >
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <MessageCircleHeartIcon className="size-3 text-primary" />
            AI 챗봇
          </div>
          <ChatMock />
        </motion.div>
      </div>
    </div>
  );
}

const USER_MSG = "이 약은 언제 먹어야 하나요?";
const AI_MSG = "암로디핀은 하루 1회 식후에 복용하세요. 규칙적으로 복용하는 것이 중요해요.";

type ChatPhase = "typing-user" | "loading" | "typing-ai" | "pause";

function ChatMock() {
  const [phase, setPhase] = useState<ChatPhase>("typing-user");
  const [userText, setUserText] = useState("");
  const [aiText, setAiText] = useState("");

  useEffect(() => {
    let t: ReturnType<typeof setTimeout>;

    if (phase === "typing-user") {
      if (userText.length < USER_MSG.length) {
        t = setTimeout(() => setUserText(USER_MSG.slice(0, userText.length + 1)), 55);
      } else {
        t = setTimeout(() => setPhase("loading"), 500);
      }
    } else if (phase === "loading") {
      t = setTimeout(() => setPhase("typing-ai"), 1400);
    } else if (phase === "typing-ai") {
      if (aiText.length < AI_MSG.length) {
        t = setTimeout(() => setAiText(AI_MSG.slice(0, aiText.length + 1)), 28);
      } else {
        t = setTimeout(() => setPhase("pause"), 3000);
      }
    } else if (phase === "pause") {
      t = setTimeout(() => {
        setUserText("");
        setAiText("");
        setPhase("typing-user");
      }, 800);
    }

    return () => clearTimeout(t);
  }, [phase, userText, aiText]);

  return (
    <div className="mt-2.5 min-h-13 space-y-1.5">
      {userText && (
        <div className="ml-auto max-w-[80%] rounded-lg rounded-br-sm bg-primary px-3 py-1.5 text-xs text-primary-foreground">
          {userText}
          {phase === "typing-user" && <span className="ml-px animate-pulse">|</span>}
        </div>
      )}
      {phase === "loading" && <LoadingDots />}
      {aiText && (
        <div className="max-w-[85%] rounded-lg rounded-bl-sm bg-muted px-3 py-1.5 text-xs">
          {aiText}
          {phase === "typing-ai" && <span className="ml-px animate-pulse">|</span>}
        </div>
      )}
    </div>
  );
}

function LoadingDots() {
  return (
    <div className="flex max-w-15 items-center gap-1 rounded-lg rounded-bl-sm bg-muted px-3 py-2">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="size-1.5 rounded-full bg-muted-foreground/50"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
          transition={{ duration: 0.7, repeat: Infinity, delay: i * 0.18, ease: "easeInOut" }}
        />
      ))}
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
      <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${toneClass}`}>
        {tone === "warning" && (
          <motion.span
            className="size-1 rounded-full bg-warning"
            animate={{ opacity: [1, 0.2, 1] }}
            transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        {status}
      </span>
    </div>
  );
}

const FEATURES = [
  {
    icon: FileTextIcon,
    title: "처방전·약봉투 자동 분석",
    description: "처방전·약봉투를 업로드하면 AI가 약물 정보를 자동으로 추출하고 구조화합니다.",
    accent: "from-primary/15 to-primary/0",
    iconBg: "bg-primary/10 text-primary",
    span: "sm:col-span-2",
  },
  {
    icon: MessageCircleHeartIcon,
    title: "AI 건강 챗봇",
    description: "약 복용, 부작용, 건강 궁금증을 한국어로 자연스럽게 물어보세요.",
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
    icon: BookOpenIcon,
    title: "맞춤형 복약 가이드",
    description: "처방 내용과 건강정보를 바탕으로 복약·생활·식사·운동 가이드를 제공해요.",
    accent: "from-primary/15 to-primary/0",
    iconBg: "bg-primary/10 text-primary",
    span: "sm:col-span-2",
  },
] as const;

function FeatureBento() {
  return (
    <section aria-label="주요 기능" className="grid gap-3 sm:grid-cols-3">
      {FEATURES.map(({ icon: Icon, title, description, accent, iconBg, span }, i) => (
        <motion.article
          key={title}
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: i * 0.1, ease: "easeOut" }}
          className={`group relative overflow-hidden rounded-2xl border bg-card p-5 shadow-sm transition-transform duration-150 hover:-translate-y-1.5 hover:shadow-md ${span}`}
        >
          <div
            className={`pointer-events-none absolute inset-0 -z-10 bg-linear-to-br ${accent} opacity-70`}
          />
          <span className={`grid size-10 place-items-center rounded-xl ${iconBg}`}>
            <Icon className="size-5" />
          </span>
          <h2 className="mt-4 text-base font-semibold">{title}</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{description}</p>
        </motion.article>
      ))}
    </section>
  );
}

function BackgroundDecoration() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <motion.div
        className="absolute -top-40 -left-40 h-150 w-150 rounded-full bg-primary/20 blur-3xl"
        animate={{ x: [0, 24, 0], y: [0, -20, 0] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-1/3 -right-32 h-130 w-130 rounded-full bg-success/12 blur-3xl"
        animate={{ x: [0, -18, 0], y: [0, 28, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut", delay: 2 }}
      />
      <motion.div
        className="absolute -bottom-32 left-1/3 h-110 w-110 rounded-full bg-primary/12 blur-3xl"
        animate={{ x: [0, 14, 0], y: [0, -18, 0] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 4 }}
      />
    </div>
  );
}
