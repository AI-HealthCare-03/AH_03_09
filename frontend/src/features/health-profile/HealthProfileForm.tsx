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

const HEIGHT_OPTIONS = Array.from({ length: 250 - 80 + 1 }, (_, i) => String(80 + i));
const WEIGHT_OPTIONS = Array.from({ length: 300 - 20 + 1 }, (_, i) => String(20 + i));
const SYSTOLIC_OPTIONS = Array.from({ length: 250 - 70 + 1 }, (_, i) => String(70 + i));
const DIASTOLIC_OPTIONS = Array.from({ length: 150 - 40 + 1 }, (_, i) => String(40 + i));

interface Props {
  defaultValues: HealthProfileFormValues;
  onSubmit: (values: HealthProfileFormValues) => void;
  onCancel?: () => void;
  submitLabel?: string;
}

export function HealthProfileForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = "저장",
}: Props) {
  const form = useForm<HealthProfileFormValues>({
    resolver: zodResolver(healthProfileSchema),
    mode: "onTouched",
    defaultValues,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-6" noValidate>
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

        <div className="flex gap-2 pt-2">
          {onCancel ? (
            <Button type="button" variant="outline" onClick={onCancel} className="flex-1 h-11">
              취소
            </Button>
          ) : null}
          <Button type="submit" className="flex-1 h-11 text-base">
            {submitLabel}
          </Button>
        </div>
      </form>
    </Form>
  );
}

type Control = ReturnType<typeof useForm<HealthProfileFormValues>>["control"];
type FieldName = keyof HealthProfileFormValues;

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
