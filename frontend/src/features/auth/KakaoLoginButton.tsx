import { cn } from "@/lib/utils";
import { useKakaoLogin } from "./useKakaoLogin";

interface KakaoLoginButtonProps {
  label?: string;
  size?: "default" | "lg";
  className?: string;
}

export function KakaoLoginButton({
  label = "카카오로 로그인",
  size = "default",
  className,
}: KakaoLoginButtonProps) {
  const { login, loading, error } = useKakaoLogin();

  return (
    <div className={cn("flex w-full flex-col gap-2", className)}>
      <button
        type="button"
        onClick={login}
        disabled={loading}
        className={cn(
          "inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#FEE500] font-semibold text-[#191919] shadow-sm transition hover:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FEE500] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60",
          size === "lg" ? "h-12 px-6 text-base" : "h-11 px-5 text-sm",
        )}
        aria-label={label}
      >
        <KakaoBubbleIcon />
        {loading ? "이동 중…" : label}
      </button>
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function KakaoBubbleIcon() {
  return (
    <svg viewBox="0 0 18 18" fill="currentColor" aria-hidden="true" className="size-4 shrink-0">
      <path d="M9 0.5C4.03 0.5 0 3.65 0 7.55c0 2.5 1.7 4.7 4.25 5.9-.13.45-.85 2.95-.88 3.1 0 0-.02.15.07.21.1.06.21.01.21.01.21-.03 3.4-2.22 3.95-2.6.46.07.93.1 1.4.1 4.97 0 9-3.15 9-7.05S13.97 0.5 9 0.5z" />
    </svg>
  );
}
