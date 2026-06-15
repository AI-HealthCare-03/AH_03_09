import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { completeOnboarding } from "@/api/auth";
import { updateHealthProfile } from "@/api/healthProfile";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { HealthProfileForm } from "@/features/health-profile/HealthProfileForm";
import {
  type HealthProfileFormValues,
  fromMedicalProfile,
  toMedicalProfile,
} from "@/features/health-profile/healthProfileSchema";
import { useAuthStore } from "@/store/authStore";

type Step = "consent" | "health-profile";

export default function Onboarding() {
  const navigate = useNavigate();
  const setMedicalProfile = useAuthStore((s) => s.setMedicalProfile);
  const setIsOnboarded = useAuthStore((s) => s.setIsOnboarded);

  const [step, setStep] = useState<Step>("consent");
  const [termsChecked, setTermsChecked] = useState(false);
  const [privacyChecked, setPrivacyChecked] = useState(false);

  const completeMutation = useMutation({ mutationFn: completeOnboarding });
  const profileMutation = useMutation({ mutationFn: updateHealthProfile });

  const finishOnboarding = async () => {
    await completeMutation.mutateAsync();
    setIsOnboarded(true);
    navigate("/home", { replace: true });
  };

  const handleProfileSubmit = async (values: HealthProfileFormValues) => {
    const diagnoses = values.existingDiagnoses
      ? values.existingDiagnoses.split(",").map((s) => s.trim()).filter(Boolean)
      : [];
    const hasBp = !!values.systolic && !!values.diastolic;

    await profileMutation.mutateAsync({
      gender: values.gender ?? undefined,
      birth_date: values.birthDate || undefined,
      height_cm: Number(values.heightCm) || undefined,
      weight_kg: Number(values.weightKg) || undefined,
      blood_pressure_systolic: hasBp ? Number(values.systolic) : undefined,
      blood_pressure_diastolic: hasBp ? Number(values.diastolic) : undefined,
      primary_conditions: diagnoses,
      allergies: values.allergies,
      current_medications: values.currentMedications,
      lifestyle_exercise: values.lifestyleExercise,
      lifestyle_smoking: values.lifestyleSmoking,
      lifestyle_alcohol: values.lifestyleAlcohol,
    });
    setMedicalProfile(toMedicalProfile(values));
    await finishOnboarding();
  };

  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-lg space-y-6">
        <header className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            AI 건강 도우미
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {step === "consent" ? "서비스 이용 동의" : "건강정보 입력"}
          </p>
        </header>

        <StepIndicator step={step} />

        {step === "consent" ? (
          <ConsentStep
            termsChecked={termsChecked}
            privacyChecked={privacyChecked}
            onTermsChange={setTermsChecked}
            onPrivacyChange={setPrivacyChecked}
            onNext={() => setStep("health-profile")}
          />
        ) : (
          <HealthProfileStep
            onSubmit={handleProfileSubmit}
            onSkip={finishOnboarding}
            isSaving={profileMutation.isPending || completeMutation.isPending}
          />
        )}
      </div>
    </main>
  );
}

function StepIndicator({ step }: { step: Step }) {
  return (
    <div className="flex items-center justify-center gap-2">
      <StepDot active={step === "consent"} done={step === "health-profile"} label="동의" />
      <div className="h-px w-10 bg-slate-200" />
      <StepDot active={step === "health-profile"} done={false} label="건강정보" />
    </div>
  );
}

function StepDot({ active, done, label }: { active: boolean; done: boolean; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`grid size-7 place-items-center rounded-full text-xs font-semibold ${
          done
            ? "bg-primary text-primary-foreground"
            : active
              ? "border-2 border-primary text-primary"
              : "border-2 border-slate-200 text-slate-400"
        }`}
      >
        {done ? "✓" : active ? "●" : "○"}
      </div>
      <span className={`text-xs ${active || done ? "text-primary font-medium" : "text-slate-400"}`}>
        {label}
      </span>
    </div>
  );
}

function ConsentStep({
  termsChecked,
  privacyChecked,
  onTermsChange,
  onPrivacyChange,
  onNext,
}: {
  termsChecked: boolean;
  privacyChecked: boolean;
  onTermsChange: (v: boolean) => void;
  onPrivacyChange: (v: boolean) => void;
  onNext: () => void;
}) {
  return (
    <Card className="rounded-2xl">
      <CardHeader>
        <CardTitle className="text-lg">서비스 이용 동의</CardTitle>
        <CardDescription>아래 내용을 확인하신 후 동의해 주세요.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <ConsentBox title="서비스 이용약관 (필수)">
          본 서비스는 AI 기반 복약 가이드 및 건강 정보를 제공합니다. 제공되는 정보는 참고용이며,
          실제 치료·진단을 대체하지 않습니다. 서비스 이용 중 입력하신 데이터는 개인 맞춤형 가이드
          생성에만 활용되며, 외부에 제공되지 않습니다. 만 14세 미만은 서비스를 이용하실 수 없습니다.
        </ConsentBox>

        <ConsentBox title="개인정보 수집 및 이용 동의 (필수)">
          수집 항목: 카카오 계정 정보(이름, 이메일), 건강정보(성별, 생년월일, 신체정보, 기저질환,
          알레르기, 복용 약물, 생활 습관), 진료 문서(처방전·약봉투 이미지 및 OCR 결과).
          수집 목적: AI 복약 가이드 생성, 챗봇 답변 맞춤화. 보유 기간: 회원 탈퇴 시까지.
          수집된 개인정보는 외부 기관·제3자에게 제공되지 않습니다.
        </ConsentBox>

        <div className="space-y-3">
          <label className="flex cursor-pointer items-center gap-3">
            <Checkbox
              checked={termsChecked}
              onCheckedChange={(v) => onTermsChange(v === true)}
            />
            <span className="text-sm font-medium text-slate-700">서비스 이용약관에 동의합니다. (필수)</span>
          </label>
          <label className="flex cursor-pointer items-center gap-3">
            <Checkbox
              checked={privacyChecked}
              onCheckedChange={(v) => onPrivacyChange(v === true)}
            />
            <span className="text-sm font-medium text-slate-700">개인정보 수집 및 이용에 동의합니다. (필수)</span>
          </label>
        </div>

        <Button
          className="h-11 w-full text-base"
          disabled={!termsChecked || !privacyChecked}
          onClick={onNext}
        >
          다음
        </Button>
      </CardContent>
    </Card>
  );
}

function ConsentBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      <div className="max-h-28 overflow-y-auto rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs leading-relaxed text-slate-500">
        {children}
      </div>
    </div>
  );
}

function HealthProfileStep({
  onSubmit,
  onSkip,
  isSaving,
}: {
  onSubmit: (values: HealthProfileFormValues) => Promise<void>;
  onSkip: () => Promise<void>;
  isSaving: boolean;
}) {
  return (
    <Card className="rounded-2xl">
      <CardHeader>
        <CardTitle className="text-lg">건강정보 입력</CardTitle>
        <CardDescription>
          입력하신 정보는 AI 복약 가이드와 챗봇 답변의 정확도를 높이는 데 사용됩니다.
          나중에 건강정보 메뉴에서 수정할 수 있습니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <HealthProfileForm
          defaultValues={fromMedicalProfile(null)}
          onSubmit={onSubmit}
          submitLabel="저장하고 시작하기"
          isSaving={isSaving}
        />
        <Button
          type="button"
          variant="ghost"
          className="w-full text-slate-500"
          onClick={onSkip}
          disabled={isSaving}
        >
          건너뛰기 (나중에 입력)
        </Button>
      </CardContent>
    </Card>
  );
}
