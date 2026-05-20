import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-50 text-slate-900">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">404</h1>
        <p className="mt-2 text-sm text-slate-500">페이지를 찾을 수 없습니다.</p>
        <Link to="/login" className="mt-4 inline-block text-sm text-blue-600 hover:underline">
          로그인으로 돌아가기
        </Link>
      </div>
    </main>
  );
}
