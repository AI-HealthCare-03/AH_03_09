import { ChevronRightIcon, LogOutIcon, UserIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/store/authStore";

export default function Settings() {
  const navigate = useNavigate();
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
          <CardDescription>내 정보를 확인하거나 카카오 세션을 종료합니다.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/profile")}
            className="justify-between"
          >
            <span className="flex items-center gap-2">
              <UserIcon className="size-4" />
              내 정보
            </span>
            <ChevronRightIcon className="size-4 text-muted-foreground" />
          </Button>
          <Button type="button" variant="outline" onClick={handleLogout}>
            <LogOutIcon className="size-4" />
            로그아웃
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
