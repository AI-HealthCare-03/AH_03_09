import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";

// TODO(feature/fe-onboarding-bhw): replace with full terms agreement UI.
export default function Terms() {
  const setTermsAccepted = useAuthStore((s) => s.setTermsAccepted);
  const navigate = useNavigate();

  return (
    <div className="mx-auto max-w-md p-6">
      <h1 className="mb-2 text-xl font-semibold">약관 동의</h1>
      <p className="mb-6 text-sm text-muted-foreground">약관 동의 화면 준비 중입니다.</p>
      <Button
        type="button"
        onClick={() => {
          setTermsAccepted();
          navigate("/onboarding", { replace: true });
        }}
        className="w-full"
      >
        임시: 약관에 모두 동의하고 다음으로
      </Button>
    </div>
  );
}
