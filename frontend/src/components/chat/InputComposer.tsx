import { type FormEvent, useState } from "react";

interface Props {
  onSubmit: (content: string) => Promise<void> | void;
  disabled?: boolean;
}

export default function InputComposer({ onSubmit, disabled }: Props) {
  const [value, setValue] = useState("");
  const [composing, setComposing] = useState(false);

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    setValue("");
    await onSubmit(trimmed);
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    void submit();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="shrink-0 border-t border-slate-200 bg-white p-4"
      style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
    >
      <div className="flex gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onCompositionStart={() => setComposing(true)}
          onCompositionEnd={() => setComposing(false)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !composing) {
              e.preventDefault();
              void submit();
            }
          }}
          placeholder={disabled ? "AI가 답변 중입니다…" : "메시지를 입력하세요…"}
          rows={1}
          className="flex-1 resize-none rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-md bg-slate-900 px-4 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          전송
        </button>
      </div>
    </form>
  );
}
