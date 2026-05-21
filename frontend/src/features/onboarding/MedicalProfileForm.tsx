import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuthStore } from "@/store/authStore";
import {
  type MedicalProfileFormValues,
  medicalProfileSchema,
  toMedicalProfile,
} from "./medicalProfileSchema";

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: currentYear - 1920 + 1 }, (_, i) =>
  String(currentYear - i),
);
const MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => String(i + 1));
const DAY_OPTIONS = Array.from({ length: 31 }, (_, i) => String(i + 1));
const HEIGHT_OPTIONS = Array.from({ length: 250 - 80 + 1 }, (_, i) => String(80 + i));
const WEIGHT_OPTIONS = Array.from({ length: 300 - 20 + 1 }, (_, i) => String(20 + i));
const SYSTOLIC_OPTIONS = Array.from({ length: 250 - 70 + 1 }, (_, i) => String(70 + i));
const DIASTOLIC_OPTIONS = Array.from({ length: 150 - 40 + 1 }, (_, i) => String(40 + i));

export function MedicalProfileForm() {
  const setOnboardingCompleted = useAuthStore((s) => s.setOnboardingCompleted);
  const navigate = useNavigate();

  const form = useForm<MedicalProfileFormValues>({
    resolver: zodResolver(medicalProfileSchema),
    mode: "onTouched",
    defaultValues: {
      nickname: "",
      gender: undefined as unknown as "M",
      birthYear: "",
      birthMonth: "",
      birthDay: "",
      heightCm: "",
      weightKg: "",
      existingDiagnoses: "",
      systolic: "",
      diastolic: "",
    },
  });

  const onSubmit = (values: MedicalProfileFormValues) => {
    setOnboardingCompleted(toMedicalProfile(values));
    navigate("/home", { replace: true });
  };

  return (
    <main className="min-h-dvh bg-background py-8 text-foreground sm:py-12">
      <section className="mx-auto w-full max-w-xl px-4 sm:px-6">
        <header className="mb-6 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">기본 정보 입력</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            정확한 분석을 위해 의료 정보를 입력해주세요. 입력하신 정보는 본인 외에는 공개되지
            않습니다.
          </p>
        </header>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-col gap-6 rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8"
            noValidate
          >
            <FormField
              control={form.control}
              name="nickname"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    닉네임 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="2~20자 사이로 입력해주세요" maxLength={20} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="gender"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    성별 <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <RadioGroup
                      value={field.value}
                      onValueChange={field.onChange}
                      className="grid grid-cols-2 gap-3"
                    >
                      {[
                        { value: "M", label: "남성" },
                        { value: "F", label: "여성" },
                      ].map((opt) => {
                        const itemId = `gender-${opt.value}`;
                        return (
                          <label
                            key={opt.value}
                            htmlFor={itemId}
                            className="flex h-11 cursor-pointer items-center justify-center gap-2 rounded-md border border-border bg-background text-sm transition hover:bg-accent has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5"
                          >
                            <RadioGroupItem id={itemId} value={opt.value} />
                            <span>{opt.label}</span>
                          </label>
                        );
                      })}
                    </RadioGroup>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormItem>
              <FormLabel>
                생년월일 <span className="text-destructive">*</span>
              </FormLabel>
              <div className="grid grid-cols-3 gap-2">
                <DateSelect
                  name="birthYear"
                  control={form.control}
                  placeholder="년"
                  options={YEAR_OPTIONS}
                  suffix="년"
                />
                <DateSelect
                  name="birthMonth"
                  control={form.control}
                  placeholder="월"
                  options={MONTH_OPTIONS}
                  suffix="월"
                />
                <DateSelect
                  name="birthDay"
                  control={form.control}
                  placeholder="일"
                  options={DAY_OPTIONS}
                  suffix="일"
                />
              </div>
              <FormFieldErrors form={form} names={["birthYear", "birthMonth", "birthDay"]} />
            </FormItem>

            <div className="grid grid-cols-2 gap-4">
              <NumericSelect
                control={form.control}
                name="heightCm"
                label="키 (cm)"
                required
                options={HEIGHT_OPTIONS}
                placeholder="선택"
                suffix="cm"
              />
              <NumericSelect
                control={form.control}
                name="weightKg"
                label="체중 (kg)"
                required
                options={WEIGHT_OPTIONS}
                placeholder="선택"
                suffix="kg"
              />
            </div>

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

            <FormItem>
              <FormLabel>혈압 (mmHg)</FormLabel>
              <div className="grid grid-cols-2 gap-2">
                <NumericSelect
                  control={form.control}
                  name="systolic"
                  options={SYSTOLIC_OPTIONS}
                  placeholder="수축기"
                  suffix="수축기"
                  hideLabel
                />
                <NumericSelect
                  control={form.control}
                  name="diastolic"
                  options={DIASTOLIC_OPTIONS}
                  placeholder="이완기"
                  suffix="이완기"
                  hideLabel
                />
              </div>
              <FormDescription>
                선택 입력입니다. 입력 시 수축기·이완기 모두 선택해주세요.
              </FormDescription>
              <FormFieldErrors form={form} names={["systolic", "diastolic"]} />
            </FormItem>

            <Button type="submit" className="mt-2 h-11 w-full text-base">
              완료하고 시작하기
            </Button>
          </form>
        </Form>
      </section>
    </main>
  );
}

type Control = ReturnType<typeof useForm<MedicalProfileFormValues>>["control"];
type FieldName = keyof MedicalProfileFormValues;

interface DateSelectProps {
  control: Control;
  name: FieldName;
  placeholder: string;
  options: string[];
  suffix: string;
}

function DateSelect({ control, name, placeholder, options, suffix }: DateSelectProps) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormControl>
          <Select value={field.value as string} onValueChange={field.onChange}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
              {options.map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                  {suffix}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormControl>
      )}
    />
  );
}

interface NumericSelectProps {
  control: Control;
  name: FieldName;
  label?: string;
  required?: boolean;
  options: string[];
  placeholder: string;
  suffix: string;
  hideLabel?: boolean;
}

function NumericSelect({
  control,
  name,
  label,
  required,
  options,
  placeholder,
  suffix,
  hideLabel,
}: NumericSelectProps) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          {!hideLabel && label ? (
            <FormLabel>
              {label}
              {required ? <span className="text-destructive"> *</span> : null}
            </FormLabel>
          ) : null}
          <FormControl>
            <Select value={field.value as string} onValueChange={field.onChange}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder={placeholder} />
              </SelectTrigger>
              <SelectContent>
                {options.map((opt) => (
                  <SelectItem key={opt} value={opt}>
                    {opt} {suffix}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormControl>
          {!hideLabel ? <FormMessage /> : null}
        </FormItem>
      )}
    />
  );
}

function FormFieldErrors({
  form,
  names,
}: {
  form: ReturnType<typeof useForm<MedicalProfileFormValues>>;
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
