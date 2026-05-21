import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// TODO(feature/fe-document-upload-bhw): replace with classification confirm UI.
export default function UploadReview() {
  const { jobId } = useParams<{ jobId: string }>();
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>문서 유형 확인</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">job_id: {jobId}</p>
          <p className="mt-2 text-sm text-muted-foreground">유형 확인 화면 준비 중입니다.</p>
        </CardContent>
      </Card>
    </div>
  );
}
