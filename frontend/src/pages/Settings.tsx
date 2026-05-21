import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Settings() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">설정</h1>
      <Card>
        <CardHeader>
          <CardTitle>계정 설정</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">설정 화면 준비 중입니다.</p>
        </CardContent>
      </Card>
    </div>
  );
}
