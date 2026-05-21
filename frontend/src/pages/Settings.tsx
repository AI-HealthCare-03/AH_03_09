import { LogOutIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/store/authStore";

export default function Settings() {
  const clear = useAuthStore((s) => s.clear);

  const handleLogout = () => {
    clear();
    window.location.assign("/");
  };

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">설정</h1>
        <p className="text-sm text-muted-foreground">계정 및 앱 환경을 관리합니다.</p>
      </header>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="text-base">계정</CardTitle>
          <CardDescription>현재 기기에서 카카오 세션을 종료합니다.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" variant="outline" onClick={handleLogout}>
            <LogOutIcon className="size-4" />
            로그아웃
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
