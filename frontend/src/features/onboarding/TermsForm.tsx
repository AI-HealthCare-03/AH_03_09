import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/store/authStore";
import { TERMS } from "./terms";

type Checked = Record<string, boolean>;

const INITIAL: Checked = Object.fromEntries(TERMS.map((t) => [t.id, false]));

export function TermsForm() {
  const [checked, setChecked] = useState<Checked>(INITIAL);
  const setTermsAccepted = useAuthStore((s) => s.setTermsAccepted);
  const navigate = useNavigate();

  const requiredIds = TERMS.filter((t) => t.required).map((t) => t.id);
  const allRequiredChecked = requiredIds.every((id) => checked[id]);
  const allChecked = TERMS.every((t) => checked[t.id]);

  const toggle = (id: string) => {
    setChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleAll = () => {
    const next = allChecked ? INITIAL : Object.fromEntries(TERMS.map((t) => [t.id, true]));
    setChecked(next);
  };

  const handleSubmit = () => {
    if (!allRequiredChecked) return;
    setTermsAccepted();
    navigate("/onboarding", { replace: true });
  };

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background p-4 text-foreground sm:p-6">
      <section className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-8">
        <header className="flex flex-col gap-2 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">서비스 이용 약관</h1>
          <p className="text-sm text-muted-foreground">
            Medi-Mate 이용을 위해 아래 약관에 동의해주세요.
          </p>
        </header>

        <div className="mt-6 rounded-lg border border-border bg-muted/30 p-4">
          <label htmlFor="terms-all" className="flex cursor-pointer items-center gap-3">
            <Checkbox
              id="terms-all"
              checked={allChecked}
              onCheckedChange={toggleAll}
              aria-label="약관 전체 동의"
            />
            <span className="text-sm font-semibold text-foreground">전체 동의</span>
          </label>
          <p className="mt-2 pl-8 text-xs text-muted-foreground">
            선택 항목 포함 모든 약관에 동의합니다. 선택 항목은 동의하지 않아도 서비스 이용이
            가능합니다.
          </p>
        </div>

        <Separator className="my-5" />

        <ul className="flex flex-col gap-4">
          {TERMS.map((item) => (
            <li key={item.id} className="flex items-start gap-3">
              <Checkbox
                id={`terms-${item.id}`}
                checked={!!checked[item.id]}
                onCheckedChange={() => toggle(item.id)}
                aria-label={item.title}
                className="mt-0.5"
              />
              <label
                htmlFor={`terms-${item.id}`}
                className="flex flex-1 cursor-pointer items-start justify-between gap-3 text-sm"
              >
                <span className="flex items-center gap-2">
                  <span
                    className={
                      item.required
                        ? "rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary"
                        : "rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground"
                    }
                  >
                    {item.required ? "필수" : "선택"}
                  </span>
                  <span className="text-foreground">{item.title}</span>
                </span>
                <TermsDialog title={item.title} body={item.body} />
              </label>
            </li>
          ))}
        </ul>

        <Button
          type="button"
          onClick={handleSubmit}
          disabled={!allRequiredChecked}
          className="mt-8 h-11 w-full text-base"
        >
          동의하고 계속하기
        </Button>
      </section>
    </main>
  );
}

function TermsDialog({ title, body }: { title: string; body: string }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          className="shrink-0 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          내용 보기
        </button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4">
          <DialogTitle className="text-base">{title}</DialogTitle>
          <DialogDescription className="sr-only">{title} 전문</DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] overflow-y-auto whitespace-pre-line px-6 py-5 text-sm leading-relaxed text-muted-foreground">
          {body}
        </div>
      </DialogContent>
    </Dialog>
  );
}
