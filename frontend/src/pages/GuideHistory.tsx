import { useEffect, useRef, useState } from "react";

import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import {
  getGuideList,
  getGuideStatus,
  type GuideListItem,
} from "@/api/guides";
import { Loader2, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function GuideHistory() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [pollingState, setPollingState] = useState<string>("");
  const initialJobIdRef = useRef(searchParams.get("job_id") ?? null);

  const isPolling = !!initialJobIdRef.current;

  const { data: guideList, isLoading: listLoading } = useQuery({
    queryKey: ["guide-list"],
    queryFn: getGuideList,
  });

  // job_id가 있으면 폴링 → 완료 시 /health-guide/:guide_id 로 이동
  useEffect(() => {
    const jobId = initialJobIdRef.current;
    if (!jobId) return;

    let cancelled = false;
    setPollingState("loading");

    async function poll(id: string) {
      while (!cancelled) {
        await new Promise((r) => setTimeout(r, 2000));
        try {
          const result = await getGuideStatus(id);
          if (cancelled) break;
          if (result.status === "DONE" && result.guide_id) {
            if (!cancelled) navigate(`/health-guide/${result.guide_id}`, { replace: true });
            break;
          }
          if (result.status === "FAILED") {
            if (!cancelled) setPollingState("가이드 생성에 실패했습니다.");
            break;
          }
        } catch {
          if (!cancelled) setPollingState("상태 확인 중 오류가 발생했습니다.");
          break;
        }
      }
    }

    poll(jobId);
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const showList = !isPolling || (pollingState !== "" && pollingState !== "loading");

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">건강 가이드</h1>
        <Button size="sm" onClick={() => navigate("/upload")}>
          <Upload className="mr-2 size-4" />
          처방전 업로드하기
        </Button>
      </div>

      {pollingState === "loading" && (
        <Card>
          <CardContent className="space-y-2 px-4 py-4 text-sm">
            <div className="flex items-center gap-2">
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
              <p className="font-medium text-gray-800">건강 가이드 생성 중</p>
            </div>
            <p className="text-muted-foreground">
              올려주신 처방전/약정보를 읽고 복약·식사·운동 가이드를 생성하고 있습니다.
            </p>
            <p className="text-muted-foreground">잠시만 기다려 주세요.</p>
          </CardContent>
        </Card>
      )}

      {pollingState !== "" && pollingState !== "loading" && (
        <Card>
          <CardContent className="px-4 py-4">
            <p className="text-sm text-muted-foreground">{pollingState}</p>
          </CardContent>
        </Card>
      )}

      {showList && (
        <Card>
          <CardContent className="px-4 py-4">
            {listLoading && (
              <p className="text-sm text-muted-foreground">목록을 불러오는 중...</p>
            )}
            {!listLoading && !guideList?.items?.length && (
              <div className="flex flex-col items-center gap-4 py-6 text-center">
                <p className="text-sm font-medium text-gray-700">아직 생성된 건강 가이드가 없습니다.</p>
                <p className="text-sm text-muted-foreground">
                  처방전 또는 약봉투를 업로드하면 맞춤 건강 가이드를 받을 수 있습니다.
                </p>
                <Button onClick={() => navigate("/upload")}>
                  <Upload className="mr-2 size-4" />
                  처방전 업로드하기
                </Button>
              </div>
            )}
            {!listLoading && !!guideList?.items?.length && (
              <div className="divide-y">
                {guideList.items.map((item) => (
                  <GuideListRow
                    key={item.guide_id}
                    item={item}
                    onView={() => navigate(`/health-guide/${item.guide_id}`)}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function GuideListRow({
  item,
  onView,
}: {
  item: GuideListItem;
  onView: () => void;
}) {
  const dateStr = new Date(item.created_at).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const medicationLabel =
    item.medication_names.length > 0
      ? item.medication_names.join(", ")
      : item.guide_types.join(" · ");

  return (
    <div className="flex items-center justify-between py-3">
      <div className="space-y-0.5">
        <p className="text-sm font-medium text-gray-800">{dateStr}</p>
        {medicationLabel && (
          <p className="text-xs text-muted-foreground">{medicationLabel}</p>
        )}
      </div>
      <Button variant="outline" size="sm" onClick={onView}>
        보기
      </Button>
    </div>
  );
}
