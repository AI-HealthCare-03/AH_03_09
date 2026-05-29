import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangleIcon } from "lucide-react";
import { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { fetchDocument, fetchJobStatus, patchDocument } from "@/api/ocr";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { DocType } from "@/types/api";

const DOC_TYPE_LABEL: Record<DocType, string> = {
  PRESCRIPTION: "처방전",
  DRUG_BAG: "약봉투",
  OTHER: "기타",
};

const DOC_TYPE_VARIANT: Record<DocType, "default" | "secondary" | "outline"> = {
  PRESCRIPTION: "default",
  DRUG_BAG: "secondary",
  OTHER: "outline",
};

const ALL_DOC_TYPES: DocType[] = ["PRESCRIPTION", "DRUG_BAG", "OTHER"];

export default function UploadReview() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const stateRecordId = location.state?.recordId as number | undefined;
  const retakeRecommended = location.state?.retakeRecommended as boolean | undefined;

  const { data: jobStatus } = useQuery({
    queryKey: ["ocr-status", jobId],
    queryFn: () => fetchJobStatus(jobId as string),
    enabled: !!jobId && !stateRecordId,
  });

  const recordId = stateRecordId ?? jobStatus?.record_id;

  const { data: doc, isLoading } = useQuery({
    queryKey: ["ocr-document", recordId],
    queryFn: () => fetchDocument(recordId as number),
    enabled: !!recordId,
  });

  const [selected, setSelected] = useState<DocType | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const reclassifyMutation = useMutation({
    mutationFn: async (newDocType: DocType) => {
      await patchDocument(recordId as number, { doc_type: newDocType });
    },
    onSuccess: () => {
      navigate(`/upload/result/${recordId}`);
    },
  });

  const handleConfirm = () => {
    if (!selected || selected === doc?.doc_type) {
      navigate(`/upload/result/${recordId}`);
      return;
    }
    setConfirmOpen(true);
  };

  if (isLoading || !doc) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>문서 유형 확인</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-8 w-24" />
        </CardContent>
      </Card>
    );
  }

  const autoDocType = doc.doc_type;
  const currentSelected = selected ?? autoDocType;

  return (
    <Card className="max-w-lg mx-auto">
      <CardHeader>
        <CardTitle>문서 유형 확인</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {retakeRecommended && (
          <Alert variant="destructive">
            <AlertTriangleIcon className="size-4" />
            <AlertDescription>
              이미지 품질이 낮아 인식 정확도가 떨어질 수 있습니다. 더 선명하게 재촬영하시면 정확도가 높아집니다.
            </AlertDescription>
          </Alert>
        )}
        <div>
          <p className="text-sm text-muted-foreground mb-1">파일명</p>
          <p className="font-medium">{doc.original_filename}</p>
        </div>

        <div>
          <p className="text-sm text-muted-foreground mb-1">자동 분류 결과</p>
          {autoDocType ? (
            <Badge variant={DOC_TYPE_VARIANT[autoDocType]}>{DOC_TYPE_LABEL[autoDocType]}</Badge>
          ) : (
            <Badge variant="outline">분류 불가</Badge>
          )}
        </div>

        {doc.hospital_name && (
          <div>
            <p className="text-sm text-muted-foreground mb-1">의료기관</p>
            <p>{doc.hospital_name}</p>
          </div>
        )}

        <div>
          <p className="text-sm text-muted-foreground mb-2">문서 유형 선택</p>
          <div className="flex gap-2">
            {ALL_DOC_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setSelected(type)}
                className={`flex-1 rounded-lg border-2 py-2 text-sm font-medium transition-colors ${
                  currentSelected === type
                    ? "border-primary bg-primary/5 text-primary"
                    : "border-muted-foreground/20 hover:border-primary/40"
                }`}
              >
                {DOC_TYPE_LABEL[type]}
              </button>
            ))}
          </div>
        </div>
      </CardContent>
      <CardFooter className="gap-2">
        <Button variant="outline" onClick={() => navigate("/home")} className="flex-1">
          취소
        </Button>
        <Button onClick={handleConfirm} disabled={reclassifyMutation.isPending} className="flex-1">
          {reclassifyMutation.isPending ? "처리 중..." : "결과 확인"}
        </Button>
      </CardFooter>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>문서 유형 변경</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            자동 분류 결과(<strong>{doc.doc_type ? DOC_TYPE_LABEL[doc.doc_type] : "분류 불가"}</strong>)와 다릅니다.{" "}
            <strong>{selected ? DOC_TYPE_LABEL[selected] : ""}</strong>으로 재분류하면 OCR이 다시 실행됩니다. 계속하시겠습니까?
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              취소
            </Button>
            <Button
              onClick={() => { setConfirmOpen(false); reclassifyMutation.mutate(selected!); }}
              disabled={reclassifyMutation.isPending}
            >
              재분류
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
