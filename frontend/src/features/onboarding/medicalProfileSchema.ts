import { isValid, parse, subYears } from "date-fns";
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

export const medicalProfileSchema = z
  .object({
    nickname: z
      .string()
      .trim()
      .min(2, "닉네임은 2자 이상이어야 합니다.")
      .max(20, "닉네임은 20자 이내여야 합니다."),
    gender: z.enum(["M", "F"], { message: "성별을 선택해주세요." }),
    birthYear: z.string().min(1, "출생 연도를 선택해주세요."),
    birthMonth: z.string().min(1, "출생 월을 선택해주세요."),
    birthDay: z.string().min(1, "출생 일을 선택해주세요."),
    heightCm: numericInRange("키", 80, 250),
    weightKg: numericInRange("체중", 20, 300),
    existingDiagnoses: z.string().optional(),
    systolic: optionalNumeric("수축기 혈압", 70, 250),
    diastolic: optionalNumeric("이완기 혈압", 40, 150),
  })
  .superRefine((data, ctx) => {
    const dateStr = `${data.birthYear}-${data.birthMonth}-${data.birthDay}`;
    const date = parse(dateStr, "yyyy-M-d", new Date());
    if (!isValid(date)) {
      ctx.addIssue({
        code: "custom",
        path: ["birthDay"],
        message: "올바른 날짜가 아닙니다.",
      });
      return;
    }
    const minAgeBoundary = subYears(new Date(), 14);
    if (date > minAgeBoundary) {
      ctx.addIssue({
        code: "custom",
        path: ["birthYear"],
        message: "만 14세 이상만 가입할 수 있습니다.",
      });
    }

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

export type MedicalProfileFormValues = z.infer<typeof medicalProfileSchema>;

export function toMedicalProfile(values: MedicalProfileFormValues): MedicalProfile {
  const birthdate = `${values.birthYear}-${values.birthMonth.padStart(2, "0")}-${values.birthDay.padStart(2, "0")}`;
  const diagnoses = values.existingDiagnoses?.trim();
  const hasBp = !!values.systolic && !!values.diastolic;

  return {
    nickname: values.nickname,
    gender: values.gender,
    birthdate,
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
  };
}
