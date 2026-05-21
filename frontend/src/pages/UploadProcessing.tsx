import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// TODO(feature/fe-document-upload-bhw): replace with TanStack Query polling + per-file progress.
export default function UploadProcessing() {
  const { jobId } = useParams<{ jobId: string }>();
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>업로드 및 OCR 처리 중</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">job_id: {jobId}</p>
          <p className="mt-2 text-sm text-muted-foreground">처리 상태 화면 준비 중입니다.</p>
        </CardContent>
      </Card>
    </div>
  );
}
