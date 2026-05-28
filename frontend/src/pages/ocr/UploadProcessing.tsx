import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchJobStatus, reanalyzeDocument } from "@/api/ocr";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

export default function UploadProcessing() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [displayPct, setDisplayPct] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number | null>(null);

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

  const reanalyzeMutation = useMutation({
    mutationFn: () => reanalyzeDocument(data!.record_id),
    onSuccess: () => {
      startTimeRef.current = null;
      setDisplayPct(0);
      queryClient.invalidateQueries({ queryKey: ["ocr-status", jobId] });
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: ["ocr-status", jobId] });
    },
  });

  useEffect(() => {
    const status = data?.status;

    if (status !== "PENDING" && status !== "PROCESSING") {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (status === "DONE") setDisplayPct(100);
      return;
    }

    if (timerRef.current) return;

    if (!startTimeRef.current) startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      const elapsed = Date.now() - startTimeRef.current!;
      let pct: number;
      if (elapsed < 60000) pct = Math.floor(elapsed / 1000);
      else if (elapsed < 120000) pct = Math.floor(60 + (elapsed - 60000) / 3000);
      else pct = Math.min(90, Math.floor(80 + (elapsed - 120000) / 7500));
      setDisplayPct(pct);
    }, 200);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [data?.status]);

  useEffect(() => {
    if (displayPct < 100) return;
    const status = data?.status;
    if (status !== "DONE" || !data?.record_id) return;
    const timer = setTimeout(() => {
      navigate(`/upload/review/${jobId}`, {
        state: { recordId: data.record_id, retakeRecommended: data.retake_recommended },
      });
    }, 1000);
    return () => clearTimeout(timer);
  }, [displayPct, data, jobId, navigate]);

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          문서를 찾을 수 없습니다.{" "}
          <Button variant="link" className="p-0 h-auto" onClick={() => navigate("/upload")}>
            다시 업로드
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (data?.status === "FAILED") {
    const isExhausted = (data.reanalyze_count ?? 0) >= 5;
    return (
      <Card>
        <CardHeader>
          <CardTitle>OCR 처리 실패</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertDescription>
              {isExhausted
                ? "파일에 문제가 있어 처리할 수 없습니다. 다른 파일로 재업로드해 주세요."
                : (data.message ?? "OCR 처리 중 오류가 발생했습니다.")}
            </AlertDescription>
          </Alert>
          {isExhausted ? (
            <Button onClick={() => navigate("/upload")}>재업로드</Button>
          ) : (
            <Button onClick={() => reanalyzeMutation.mutate()} disabled={reanalyzeMutation.isPending}>
              {reanalyzeMutation.isPending ? "요청 중..." : "재추출"}
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  const isDone = data?.status === "DONE" && displayPct === 100;
  const message = isDone
    ? "OCR 처리가 완료되었습니다."
    : (data?.message ?? "OCR 처리 대기 중입니다.");

  return (
    <Card>
      <CardHeader>
        <CardTitle>OCR 처리 중</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={displayPct} />
        <p className="text-sm text-muted-foreground text-center">{message}</p>
      </CardContent>
    </Card>
  );
}
