import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";

// TODO(feature/fe-onboarding-bhw): replace with react-hook-form + Zod medical profile form.
export default function Onboarding() {
  const setOnboardingCompleted = useAuthStore((s) => s.setOnboardingCompleted);
  const navigate = useNavigate();

  return (
    <div className="mx-auto max-w-md p-6">
      <h1 className="mb-2 text-xl font-semibold">사용자 의료 정보 입력</h1>
      <p className="mb-6 text-sm text-muted-foreground">온보딩 폼 준비 중입니다.</p>
      <Button
        type="button"
        onClick={() => {
          setOnboardingCompleted({
            nickname: "임시 사용자",
            gender: "M",
            birthdate: "1990-01-01",
            heightCm: 170,
            weightKg: 65,
          });
          navigate("/home", { replace: true });
        }}
        className="w-full"
      >
        임시: 기본값으로 완료
      </Button>
    </div>
  );
}
