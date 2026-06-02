import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { type HealthProfileFormValues, healthProfileSchema } from "./healthProfileSchema";

const EXERCISE_OPTIONS = [
  { value: "NONE", label: "운동 안 함" },
  { value: "IRREGULAR", label: "비규칙적" },
  { value: "REGULAR", label: "규칙적 (주 3회 이상)" },
] as const;

const ALCOHOL_OPTIONS = [
  { value: "NONE", label: "음주 안 함" },
  { value: "MODERATE", label: "가끔 (주 1~2회)" },
  { value: "HEAVY", label: "자주 (주 3회 이상)" },
] as const;

interface Props {
  defaultValues: HealthProfileFormValues;
  onSubmit: (values: HealthProfileFormValues) => void;
  onCancel?: () => void;
  submitLabel?: string;
  isSaving?: boolean;
}

export function HealthProfileForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "저장",
  isSaving = false,
}: Props) {
  const form = useForm<HealthProfileFormValues>({
    resolver: zodResolver(healthProfileSchema),
    mode: "onTouched",
    defaultValues,
  });

  const allergies = form.watch("allergies");
  const currentMedications = form.watch("currentMedications");
  const lifestyleSmoking = form.watch("lifestyleSmoking");

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-6" noValidate>
        {/* 신체 정보 */}
        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="heightCm"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  키 (cm)<span className="text-destructive"> *</span>
                </FormLabel>
                <FormControl>
                  <Input type="number" min={80} max={250} placeholder="예) 170" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="weightKg"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  체중 (kg)<span className="text-destructive"> *</span>
                </FormLabel>
                <FormControl>
                  <Input type="number" min={20} max={300} placeholder="예) 65" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* 기저질환 */}
        <FormField
          control={form.control}
          name="existingDiagnoses"
          render={({ field }) => (
            <FormItem>
              <FormLabel>기저질환</FormLabel>
              <FormControl>
                <Input placeholder="예) 고혈압, 당뇨" {...field} />
              </FormControl>
              <FormDescription>선택 입력입니다. 쉼표로 구분해 입력해주세요.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* 혈압 */}
        <FormItem>
          <FormLabel>혈압 (mmHg)</FormLabel>
          <div className="grid grid-cols-2 gap-2">
            <FormField
              control={form.control}
              name="systolic"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Input type="number" min={70} max={250} placeholder="수축기" {...field} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="diastolic"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Input type="number" min={40} max={150} placeholder="이완기" {...field} />
                  </FormControl>
                </FormItem>
              )}
            />
          </div>
          <FormDescription>
            선택 입력입니다. 입력 시 수축기·이완기 모두 입력해주세요.
          </FormDescription>
          <FormFieldErrors form={form} names={["systolic", "diastolic"]} />
        </FormItem>

        {/* 알레르기 */}
        <TagSection
          label="알레르기"
          placeholder="예: 페니실린, 땅콩 (Enter로 추가)"
          items={allergies}
          onAdd={(val) => {
            if (!allergies.includes(val))
              form.setValue("allergies", [...allergies, val]);
          }}
          onRemove={(idx) =>
            form.setValue("allergies", allergies.filter((_, i) => i !== idx))
          }
        />

        {/* 복용 중인 약물 */}
        <TagSection
          label="복용 중인 약물"
          placeholder="예: 아스피린 100mg (Enter로 추가)"
          items={currentMedications}
          onAdd={(val) =>
            form.setValue("currentMedications", [...currentMedications, val])
          }
          onRemove={(idx) =>
            form.setValue(
              "currentMedications",
              currentMedications.filter((_, i) => i !== idx),
            )
          }
        />

        {/* 생활 습관 */}
        <div className="space-y-4">
          <p className="text-sm font-medium leading-none">생활 습관</p>

          <div className="grid grid-cols-2 gap-4">
            {/* 운동 */}
            <FormField
              control={form.control}
              name="lifestyleExercise"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs text-muted-foreground">운동 습관</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {EXERCISE_OPTIONS.map((o) => (
                        <SelectItem key={o.value} value={o.value}>
                          {o.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormItem>
              )}
            />

            {/* 음주 */}
            <FormField
              control={form.control}
              name="lifestyleAlcohol"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs text-muted-foreground">음주 습관</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {ALCOHOL_OPTIONS.map((o) => (
                        <SelectItem key={o.value} value={o.value}>
                          {o.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormItem>
              )}
            />
          </div>

          {/* 흡연 */}
          <FormItem>
            <FormLabel className="text-xs text-muted-foreground">흡연 여부</FormLabel>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => form.setValue("lifestyleSmoking", false)}
                className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
                  !lifestyleSmoking
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"
                }`}
              >
                비흡연
              </button>
              <button
                type="button"
                onClick={() => form.setValue("lifestyleSmoking", true)}
                className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
                  lifestyleSmoking
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"
                }`}
              >
                흡연
              </button>
            </div>
          </FormItem>
        </div>

        <div className="flex gap-2 pt-2">
          {onCancel ? (
            <Button type="button" variant="outline" onClick={onCancel} className="h-11 flex-1">
              취소
            </Button>
          ) : null}
          <Button type="submit" disabled={isSaving} className="h-11 flex-1 text-base">
            {isSaving ? "저장 중…" : submitLabel}
          </Button>
        </div>
      </form>
    </Form>
  );
}

function TagSection({
  label,
  placeholder,
  items,
  onAdd,
  onRemove,
}: {
  label: string;
  placeholder: string;
  items: string[];
  onAdd: (val: string) => void;
  onRemove: (idx: number) => void;
}) {
  const [inputVal, setInputVal] = useState("");

  const add = () => {
    const trimmed = inputVal.trim();
    if (!trimmed) return;
    onAdd(trimmed);
    setInputVal("");
  };

  return (
    <FormItem>
      <FormLabel>{label}</FormLabel>
      {items.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pb-1">
          {items.map((item, i) => (
            <span
              key={i}
              className="flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-sm"
            >
              {item}
              <button
                type="button"
                onClick={() => onRemove(i)}
                className="ml-0.5 text-slate-400 hover:text-slate-700"
              >
                ✕
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Input
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder={placeholder}
          className="flex-1"
        />
        <Button type="button" variant="outline" size="sm" onClick={add}>
          추가
        </Button>
      </div>
    </FormItem>
  );
}

type FieldName = keyof HealthProfileFormValues;

function FormFieldErrors({
  form,
  names,
}: {
  form: ReturnType<typeof useForm<HealthProfileFormValues>>;
  names: FieldName[];
}) {
  const messages = names
    .map((n) => form.formState.errors[n]?.message)
    .filter((m): m is string => typeof m === "string");
  if (messages.length === 0) return null;
  return (
    <p className="text-sm text-destructive" role="alert">
      {messages[0]}
    </p>
  );
}
