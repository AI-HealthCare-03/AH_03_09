import {
  ActivityIcon,
  ArrowRightIcon,
  BeakerIcon,
  BookOpenIcon,
  CalendarIcon,
  CigaretteIcon,
  GlassWaterIcon,
  HeartPulseIcon,
  PencilIcon,
  PillIcon,
  RulerIcon,
  StethoscopeIcon,
  UserIcon,
  WeightIcon,
} from "lucide-react";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { fetchHealthProfile, updateHealthProfile } from "@/api/healthProfile";
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

export default function HealthProfile() {
  const navigate = useNavigate();
  const medicalProfile = useAuthStore((s) => s.medicalProfile);
  const setMedicalProfile = useAuthStore((s) => s.setMedicalProfile);
  const [editing, setEditing] = useState(false);
  const [showGuideBanner, setShowGuideBanner] = useState(false);
  const queryClient = useQueryClient();

  const { data: serverProfile } = useQuery({
    queryKey: ["health-profile"],
    queryFn: fetchHealthProfile,
    staleTime: 1000 * 60 * 5,
  });

  const syncMutation = useMutation({
    mutationFn: updateHealthProfile,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["health-profile"] }),
  });

  const mergedProfile: MedicalProfile | null = medicalProfile || serverProfile
    ? {
        gender: serverProfile?.gender ?? medicalProfile?.gender,
        ageRange: serverProfile?.age_range ?? medicalProfile?.ageRange,
        heightCm: serverProfile?.height_cm ?? medicalProfile?.heightCm ?? 0,
        weightKg: serverProfile?.weight_kg ?? medicalProfile?.weightKg ?? 0,
        bloodPressure:
          serverProfile?.blood_pressure_systolic && serverProfile?.blood_pressure_diastolic
            ? { systolic: serverProfile.blood_pressure_systolic, diastolic: serverProfile.blood_pressure_diastolic }
            : medicalProfile?.bloodPressure,
        existingDiagnoses: serverProfile?.primary_conditions?.join(", ") || medicalProfile?.existingDiagnoses,
        allergies: serverProfile?.allergies ?? medicalProfile?.allergies,
        currentMedications: serverProfile?.current_medications ?? medicalProfile?.currentMedications,
        lifestyleExercise: serverProfile?.lifestyle_exercise ?? medicalProfile?.lifestyleExercise,
        lifestyleSmoking: serverProfile?.lifestyle_smoking ?? medicalProfile?.lifestyleSmoking,
        lifestyleAlcohol: serverProfile?.lifestyle_alcohol ?? medicalProfile?.lifestyleAlcohol,
      }
    : null;

  const handleSubmit = async (values: HealthProfileFormValues) => {
    const diagnoses = values.existingDiagnoses
      ? values.existingDiagnoses.split(",").map((s) => s.trim()).filter(Boolean)
      : [];

    const hasBp = !!values.systolic && !!values.diastolic;

    try {
      await syncMutation.mutateAsync({
        gender: values.gender,
        age_range: values.ageRange || undefined,
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
    } catch {
      toast.error("서버 저장에 실패했어요. 잠시 후 다시 시도해주세요.");
      return;
    }

    setMedicalProfile(toMedicalProfile(values));
    setEditing(false);
    setShowGuideBanner(true);
    toast.success("내 건강정보를 저장했어요.");
  };

  const showForm = editing || mergedProfile === null;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <header className="flex items-start justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">내 건강정보</h1>
          <p className="text-sm text-muted-foreground">
            입력하신 정보는 AI 가이드와 챗봇 답변의 정확도를 높이는 데 사용됩니다.
          </p>
        </div>
        {!showForm && mergedProfile !== null && (
          <Button type="button" variant="outline" size="sm" onClick={() => setEditing(true)}>
            <PencilIcon className="size-4" />
            수정
          </Button>
        )}
      </header>

      {showGuideBanner && (
        <button
          type="button"
          onClick={() => navigate("/health-guide")}
          className="flex w-full items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-left text-sm text-blue-800 transition-colors hover:bg-blue-100"
        >
          <BookOpenIcon className="size-4 shrink-0 text-blue-500" />
          <span className="flex-1">
            건강정보가 변경됐어요. 최신 정보로 가이드를 다시 받아보세요.
          </span>
          <ArrowRightIcon className="size-4 shrink-0 text-blue-500" />
        </button>
      )}

      {showForm ? (
        <Card className="rounded-2xl">
          <CardHeader>
            <CardTitle className="text-lg">
              {mergedProfile !== null ? "정보 수정" : "정보 입력"}
            </CardTitle>
            <CardDescription>
              본인의 신체·건강 정보를 입력해 주세요. 모든 항목은 본인 외에는 공개되지 않습니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <HealthProfileForm
              defaultValues={fromMedicalProfile(mergedProfile)}
              onSubmit={handleSubmit}
              onCancel={mergedProfile !== null ? () => setEditing(false) : undefined}
              submitLabel={mergedProfile !== null ? "변경 사항 저장" : "저장하고 시작하기"}
              isSaving={syncMutation.isPending}
            />
          </CardContent>
        </Card>
      ) : (
        <ProfileView profile={mergedProfile} />
      )}
    </div>
  );
}

function ProfileView({ profile }: { profile: MedicalProfile }) {
  const bmi = computeBmi(profile.heightCm, profile.weightKg);
  const diagnoses = profile.existingDiagnoses
    ?.split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          icon={UserIcon}
          label="성별"
          value={profile.gender === "M" ? "남성" : profile.gender === "F" ? "여성" : profile.gender === "OTHER" ? "기타" : "-"}
          unit=""
        />
        <StatCard
          icon={CalendarIcon}
          label="나이대"
          value={profile.ageRange ?? "-"}
          unit=""
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={RulerIcon} label="키" value={profile.heightCm ? `${profile.heightCm}` : "-"} unit={profile.heightCm ? "cm" : "미입력"} />
        <StatCard icon={WeightIcon} label="체중" value={profile.weightKg ? `${profile.weightKg}` : "-"} unit={profile.weightKg ? "kg" : "미입력"} />
        <StatCard
          icon={ActivityIcon}
          label="BMI"
          value={bmi.value}
          unit={bmi.label}
          accent={bmi.accent}
        />
      </div>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="text-base">건강 상태</CardTitle>
          <CardDescription>기저질환, 혈압, 알레르기, 복용 약물을 확인해 보세요.</CardDescription>
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
  if (!heightCm || !weightKg) return { value: "-", label: "미입력", accent: "text-muted-foreground" };
  const m = heightCm / 100;
  const v = weightKg / (m * m);
  const value = v.toFixed(1);
  if (v < 18.5) return { value, label: "저체중", accent: "text-yellow-600" };
  if (v < 23) return { value, label: "정상", accent: "text-green-600" };
  if (v < 25) return { value, label: "과체중", accent: "text-yellow-600" };
  return { value, label: "비만", accent: "text-destructive" };
}
