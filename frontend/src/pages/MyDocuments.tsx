import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// TODO(feature/fe-my-documents-bhw): replace with filter + TanStack Table + pagination.
export default function MyDocuments() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">내 문서</h1>
      <Card>
        <CardHeader>
          <CardTitle>업로드한 문서 목록</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">내 문서 화면 준비 중입니다.</p>
        </CardContent>
      </Card>
    </div>
  );
}
