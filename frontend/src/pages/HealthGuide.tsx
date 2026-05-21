import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// TODO: integrate /api/v1/guides/* endpoints.
export default function HealthGuide() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">건강 가이드</h1>
      <Card>
        <CardHeader>
          <CardTitle>맞춤 건강 가이드</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">건강 가이드 화면 준비 중입니다.</p>
        </CardContent>
      </Card>
    </div>
  );
}
