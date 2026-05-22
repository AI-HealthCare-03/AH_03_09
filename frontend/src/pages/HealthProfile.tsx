import {
  ActivityIcon,
  BeakerIcon,
  CigaretteIcon,
  GlassWaterIcon,
  HeartPulseIcon,
  PencilIcon,
  PillIcon,
  RulerIcon,
  StethoscopeIcon,
  WeightIcon,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { HealthProfileForm } from "@/features/health-profile/HealthProfileForm";
import {
  fromMedicalProfile,
  type HealthProfileFormValues,
  toMedicalProfile,
} from "@/features/health-profile/healthProfileSchema";
import { type MedicalProfile, useAuthStore } from "@/store/authStore";

// TODO: BE에 MedicalProfile 모델 + GET/PUT /api/v1/users/me/medical 생기면 마이그레이션.

export default function HealthProfile() {
  const medicalProfile = useAuthStore((s) => s.medicalProfile);
  const setMedicalProfile = useAuthStore((s) => s.setMedicalProfile);
  const [editing, setEditing] = useState(false);

  const handleSubmit = (values: HealthProfileFormValues) => {
    setMedicalProfile(toMedicalProfile(values));
    setEditing(false);
    toast.success("내 건강정보를 저장했어요.");
  };

  const showForm = editing || medicalProfile === null;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">내 건강정보</h1>
        <p className="text-sm text-muted-foreground">
          입력하신 정보는 AI 가이드와 챗봇 답변의 정확도를 높이는 데 사용됩니다.
        </p>
      </header>

      {showForm || medicalProfile === null ? (
        <Card className="rounded-2xl">
          <CardHeader>
            <CardTitle className="text-lg">
              {medicalProfile !== null ? "정보 수정" : "정보 입력"}
            </CardTitle>
            <CardDescription>
              본인의 신체·건강 정보를 입력해 주세요. 모든 항목은 본인 외에는 공개되지 않습니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <HealthProfileForm
              defaultValues={fromMedicalProfile(medicalProfile)}
              onSubmit={handleSubmit}
              onCancel={medicalProfile !== null ? () => setEditing(false) : undefined}
              submitLabel={medicalProfile !== null ? "변경 사항 저장" : "저장하고 시작하기"}
            />
          </CardContent>
        </Card>
      ) : (
        <ProfileView profile={medicalProfile} onEdit={() => setEditing(true)} />
      )}
    </div>
  );
}

function ProfileView({ profile, onEdit }: { profile: MedicalProfile; onEdit: () => void }) {
  const bmi = computeBmi(profile.heightCm, profile.weightKg);
  const diagnoses = profile.existingDiagnoses
    ?.split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={RulerIcon} label="키" value={`${profile.heightCm}`} unit="cm" />
        <StatCard icon={WeightIcon} label="체중" value={`${profile.weightKg}`} unit="kg" />
        <StatCard
          icon={ActivityIcon}
          label="BMI"
          value={bmi.value}
          unit={bmi.label}
          accent={bmi.accent}
        />
      </div>

      <Card className="rounded-2xl">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div className="space-y-1">
            <CardTitle className="text-base">건강 상태</CardTitle>
            <CardDescription>기저질환, 혈압, 알레르기, 복용 약물을 확인해 보세요.</CardDescription>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={onEdit}>
            <PencilIcon className="size-4" />
            수정
          </Button>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <Row icon={StethoscopeIcon} label="기저질환">
            {diagnoses && diagnoses.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {diagnoses.map((d) => (
                  <Badge key={d} variant="secondary" className="rounded-full">
                    {d}
                  </Badge>
                ))}
              </div>
            ) : (
              <span className="text-muted-foreground/60">입력된 정보 없음</span>
            )}
          </Row>
          <Separator />
          <Row icon={HeartPulseIcon} label="혈압 (mmHg)">
            {profile.bloodPressure ? (
              <span className="font-medium tabular-nums">
                {profile.bloodPressure.systolic}
                <span className="text-muted-foreground"> / </span>
                {profile.bloodPressure.diastolic}
              </span>
            ) : (
              <span className="text-muted-foreground/60">입력된 정보 없음</span>
            )}
          </Row>
          <Separator />
          <Row icon={BeakerIcon} label="알레르기">
            {profile.allergies && profile.allergies.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {profile.allergies.map((a) => (
                  <Badge key={a} variant="secondary" className="rounded-full">
                    {a}
                  </Badge>
                ))}
              </div>
            ) : (
              <span className="text-muted-foreground/60">입력된 정보 없음</span>
            )}
          </Row>
          <Separator />
          <Row icon={PillIcon} label="복용 중인 약물">
            {profile.currentMedications && profile.currentMedications.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {profile.currentMedications.map((m) => (
                  <Badge key={m} variant="outline" className="rounded-full">
                    {m}
                  </Badge>
                ))}
              </div>
            ) : (
              <span className="text-muted-foreground/60">입력된 정보 없음</span>
            )}
          </Row>
        </CardContent>
      </Card>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="text-base">생활 습관</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <Row icon={ActivityIcon} label="운동 습관">
            <span>
              {profile.lifestyleExercise === "REGULAR"
                ? "규칙적 (주 3회 이상)"
                : profile.lifestyleExercise === "IRREGULAR"
                  ? "비규칙적"
                  : "운동 안 함"}
            </span>
          </Row>
          <Separator />
          <Row icon={CigaretteIcon} label="흡연 여부">
            <span>{profile.lifestyleSmoking ? "흡연" : "비흡연"}</span>
          </Row>
          <Separator />
          <Row icon={GlassWaterIcon} label="음주 습관">
            <span>
              {profile.lifestyleAlcohol === "MODERATE"
                ? "가끔 (주 1~2회)"
                : profile.lifestyleAlcohol === "HEAVY"
                  ? "자주 (주 3회 이상)"
                  : "음주 안 함"}
            </span>
          </Row>
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  unit,
  accent,
}: {
  icon: typeof RulerIcon;
  label: string;
  value: string;
  unit: string;
  accent?: string;
}) {
  return (
    <Card className="rounded-2xl">
      <CardContent className="flex items-center gap-3 p-5">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
          <Icon className="size-5" />
        </span>
        <div className="flex flex-col">
          <span className="text-xs text-muted-foreground">{label}</span>
          <span className="text-lg font-semibold tabular-nums">
            {value}
            <span className={`ml-1 text-sm font-normal ${accent ?? "text-muted-foreground"}`}>
              {unit}
            </span>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function Row({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof RulerIcon;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </span>
      <div className="flex-1 space-y-1">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="text-foreground">{children}</div>
      </div>
    </div>
  );
}

function computeBmi(heightCm: number, weightKg: number) {
  const m = heightCm / 100;
  const v = weightKg / (m * m);
  const value = v.toFixed(1);
  if (v < 18.5) return { value, label: "저체중", accent: "text-warning" };
  if (v < 23) return { value, label: "정상", accent: "text-success" };
  if (v < 25) return { value, label: "과체중", accent: "text-warning" };
  return { value, label: "비만", accent: "text-destructive" };
}
