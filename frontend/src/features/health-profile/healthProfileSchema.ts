import { z } from "zod";
import type { MedicalProfile } from "@/store/authStore";

const numericInRange = (label: string, min: number, max: number) =>
  z
    .string()
    .min(1, `${label}을(를) 선택해주세요.`)
    .refine((v) => {
      const n = Number(v);
      return Number.isFinite(n) && n >= min && n <= max;
    }, `${label}은(는) ${min}~${max} 범위여야 합니다.`);

const optionalNumeric = (label: string, min: number, max: number) =>
  z
    .string()
    .optional()
    .refine((v) => {
      if (!v) return true;
      const n = Number(v);
      return Number.isFinite(n) && n >= min && n <= max;
    }, `${label}은(는) ${min}~${max} 범위여야 합니다.`);

export const healthProfileSchema = z
  .object({
    heightCm: numericInRange("키", 80, 250),
    weightKg: numericInRange("체중", 20, 300),
    existingDiagnoses: z.string().optional(),
    systolic: optionalNumeric("수축기 혈압", 70, 250),
    diastolic: optionalNumeric("이완기 혈압", 40, 150),
    allergies: z.array(z.string()).default([]),
    currentMedications: z.array(z.string()).default([]),
    lifestyleExercise: z.enum(["REGULAR", "IRREGULAR", "NONE"]).default("NONE"),
    lifestyleSmoking: z.boolean().default(false),
    lifestyleAlcohol: z.enum(["NONE", "MODERATE", "HEAVY"]).default("NONE"),
  })
  .superRefine((data, ctx) => {
    const sFilled = !!data.systolic;
    const dFilled = !!data.diastolic;
    if (sFilled !== dFilled) {
      ctx.addIssue({
        code: "custom",
        path: [dFilled ? "systolic" : "diastolic"],
        message: "수축기와 이완기 혈압을 모두 입력해주세요.",
      });
    }
  });

export type HealthProfileFormValues = z.infer<typeof healthProfileSchema>;

export function toMedicalProfile(values: HealthProfileFormValues): MedicalProfile {
  const diagnoses = values.existingDiagnoses?.trim();
  const hasBp = !!values.systolic && !!values.diastolic;

  return {
    heightCm: Number(values.heightCm),
    weightKg: Number(values.weightKg),
    ...(diagnoses ? { existingDiagnoses: diagnoses } : {}),
    ...(hasBp
      ? {
          bloodPressure: {
            systolic: Number(values.systolic),
            diastolic: Number(values.diastolic),
          },
        }
      : {}),
    allergies: values.allergies,
    currentMedications: values.currentMedications,
    lifestyleExercise: values.lifestyleExercise,
    lifestyleSmoking: values.lifestyleSmoking,
    lifestyleAlcohol: values.lifestyleAlcohol,
  };
}

export function fromMedicalProfile(profile: MedicalProfile | null): HealthProfileFormValues {
  return {
    heightCm: profile ? String(profile.heightCm) : "",
    weightKg: profile ? String(profile.weightKg) : "",
    existingDiagnoses: profile?.existingDiagnoses ?? "",
    systolic: profile?.bloodPressure ? String(profile.bloodPressure.systolic) : "",
    diastolic: profile?.bloodPressure ? String(profile.bloodPressure.diastolic) : "",
    allergies: profile?.allergies ?? [],
    currentMedications: profile?.currentMedications ?? [],
    lifestyleExercise: profile?.lifestyleExercise ?? "NONE",
    lifestyleSmoking: profile?.lifestyleSmoking ?? false,
    lifestyleAlcohol: profile?.lifestyleAlcohol ?? "NONE",
  };
}
