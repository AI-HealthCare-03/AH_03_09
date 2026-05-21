import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// TODO(feature/fe-document-upload-bhw): replace with drop zone + queue + result panels.
export default function Home() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">홈</h1>
      <Card>
        <CardHeader>
          <CardTitle>문서 업로드</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">문서 업로드 화면 준비 중입니다.</p>
        </CardContent>
      </Card>
    </div>
  );
}
