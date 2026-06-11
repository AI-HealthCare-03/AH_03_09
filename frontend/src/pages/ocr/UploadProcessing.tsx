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
      if (elapsed < 30000) pct = Math.floor(elapsed / 500);
      else if (elapsed < 90000) pct = Math.floor(60 + (elapsed - 30000) / 3000);
      else pct = Math.min(92, Math.floor(80 + (elapsed - 90000) / 7500));
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
    // retake_recommended이면 자동이동 없이 선택지 화면 표시
    if (data.retake_recommended) return;
    const timer = setTimeout(() => {
      navigate(`/upload/result/${data.record_id}`);
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

  if (data?.status === "DONE" && data.retake_recommended) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>OCR 처리 완료 — 재촬영 권고</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <AlertDescription>
              이미지 인식률이 낮습니다. 결과가 불만족스러우면 결과 화면에서 더 선명한 사진으로 새 파일을 업로드해 보세요.
            </AlertDescription>
          </Alert>
          <Button
            variant="outline"
            onClick={() => navigate(`/upload/result/${data.record_id}`)}
          >
            결과 확인하기
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (data?.status === "FAILED") {
    const isExhausted = (data.reanalyze_count ?? 0) >= 5;
    const isPdfResolution = data.message?.includes("PDF 파일의 해상도");
    const errorMessage = isPdfResolution
      ? data.message
      : isExhausted
        ? "파일에 문제가 있어 처리할 수 없습니다. 다른 파일로 재업로드해 주세요."
        : "OCR 처리 중 오류가 발생했습니다. OCR 서비스의 일시적 오류일 수 있으니 재시도해 주세요.";

    return (
      <Card>
        <CardHeader>
          <CardTitle>OCR 처리 실패</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
          {isPdfResolution || isExhausted ? (
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
  const isDelayed = displayPct >= 60 && !isDone;
  const isStuck = displayPct >= 92 && !isDone;
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
        <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          {isStuck && (
            <span className="size-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
          )}
          {message}
        </p>
        {isDelayed && (
          <Alert>
            <AlertDescription>
              처리 시간이 길어지고 있습니다. 문서 상태에 따라 최대 2분이 소요될 수 있습니다.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
