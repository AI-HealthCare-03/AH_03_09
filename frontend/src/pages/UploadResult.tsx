import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// TODO(feature/fe-document-upload-bhw): replace with document preview + extracted values table.
export default function UploadResult() {
  const { recordId } = useParams<{ recordId: string }>();
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>분석 결과</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">record_id: {recordId}</p>
          <p className="mt-2 text-sm text-muted-foreground">분석 결과 화면 준비 중입니다.</p>
        </CardContent>
      </Card>
    </div>
  );
}
