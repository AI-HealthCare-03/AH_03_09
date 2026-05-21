import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchJobStatus } from "@/api/ocr";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

export default function UploadProcessing() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const { data, isError } = useQuery({
    queryKey: ["ocr-status", jobId],
    queryFn: () => fetchJobStatus(jobId as string),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "DONE" || status === "FAILED") return false;
      return 2000;
    },
  });

  useEffect(() => {
    if (data?.status === "DONE" && data.record_id) {
      navigate(`/upload/review/${jobId}`, { state: { recordId: data.record_id } });
    }
  }, [data, jobId, navigate]);

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          상태 조회에 실패했습니다.{" "}
          <Button variant="link" className="p-0 h-auto" onClick={() => navigate("/home")}>
            홈으로 돌아가기
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (data?.status === "FAILED") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>OCR 처리 실패</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertDescription>
              {data.message ?? "OCR 처리 중 오류가 발생했습니다."}
            </AlertDescription>
          </Alert>
          <Button onClick={() => navigate("/home")}>다시 업로드</Button>
        </CardContent>
      </Card>
    );
  }

  const pct = data?.progress_pct ?? 0;
  const message = data?.message ?? "OCR 처리 대기 중입니다.";

  return (
    <Card>
      <CardHeader>
        <CardTitle>OCR 처리 중</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={pct} />
        <p className="text-sm text-muted-foreground text-center">{message}</p>
      </CardContent>
    </Card>
  );
}
