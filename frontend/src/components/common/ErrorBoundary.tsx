import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="flex min-h-dvh items-center justify-center bg-slate-50 text-slate-900">
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-center shadow-sm">
            <h1 className="text-lg font-semibold">문제가 발생했습니다</h1>
            <p className="mt-2 text-sm text-slate-500">새로고침 해주세요.</p>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
