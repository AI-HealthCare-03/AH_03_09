import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchDocument, fetchDocumentFile, fetchOcrResult } from "@/api/ocr";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

function ConfidenceBadge({ score }: { score: number | null }) {
  if (score === null) return null;
  const pct = Math.round(score * 100);
  const variant: "default" | "secondary" | "destructive" =
    pct >= 80 ? "default" : pct >= 60 ? "secondary" : "destructive";
  return <Badge variant={variant}>{pct}%</Badge>;
}

export default function UploadResult() {
  const { recordId: recordIdStr } = useParams<{ recordId: string }>();
  const recordId = Number(recordIdStr);
  const navigate = useNavigate();

  const [fileUrl, setFileUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!recordId) return;
    let url: string | null = null;
    fetchDocumentFile(recordId)
      .then((objectUrl) => {
        url = objectUrl;
        setFileUrl(objectUrl);
      })
      .catch(() => {});
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [recordId]);

  const { data: doc, isLoading: docLoading } = useQuery({
    queryKey: ["ocr-document", recordId],
    queryFn: () => fetchDocument(recordId),
    enabled: !!recordId,
  });

  const { data: result, isLoading: resultLoading } = useQuery({
    queryKey: ["ocr-result", recordId],
    queryFn: () => fetchOcrResult(recordId),
    enabled: !!recordId,
  });

  if (docLoading || resultLoading || !doc) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  const medications = doc.medications.filter((m) => m.is_active);
  const diseaseCodes = doc.disease_codes.filter((c) => c.is_active);
  const ocrText = result?.processed_text ?? result?.raw_text;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">분석 결과</h1>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => navigate("/upload")}>
            새 업로드
          </Button>
          <Button variant="outline" size="sm" onClick={() => navigate("/documents")}>
            목록으로
          </Button>
        </div>
      </div>

      {/* File preview */}
      {fileUrl && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">원본 문서</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            {doc.original_filename.toLowerCase().endsWith(".pdf") ? (
              <embed src={fileUrl} type="application/pdf" className="h-96 w-full rounded" />
            ) : (
              <img
                src={fileUrl}
                alt={doc.original_filename}
                className="max-h-96 rounded object-contain"
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Document info */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">문서 정보</CardTitle>
            {doc.doc_type && (
              <Badge variant={DOC_TYPE_VARIANT[doc.doc_type]}>{DOC_TYPE_LABEL[doc.doc_type]}</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="mb-0.5 text-xs text-muted-foreground">파일명</dt>
              <dd className="truncate font-medium">{doc.original_filename}</dd>
            </div>
            {doc.hospital_name && (
              <div>
                <dt className="mb-0.5 text-xs text-muted-foreground">의료기관</dt>
                <dd className="font-medium">{doc.hospital_name}</dd>
              </div>
            )}
            {doc.issued_date && (
              <div>
                <dt className="mb-0.5 text-xs text-muted-foreground">발행일</dt>
                <dd className="font-medium">
                  {new Date(doc.issued_date).toLocaleDateString("ko-KR")}
                </dd>
              </div>
            )}
            {result?.confidence_score != null && (
              <div>
                <dt className="mb-0.5 text-xs text-muted-foreground">OCR 신뢰도</dt>
                <dd>
                  <ConfidenceBadge score={result.confidence_score} />
                </dd>
              </div>
            )}
            {result?.processing_time_ms != null && (
              <div>
                <dt className="mb-0.5 text-xs text-muted-foreground">처리 시간</dt>
                <dd className="text-muted-foreground">{result.processing_time_ms}ms</dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* Medications */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            약물 목록
            {medications.length > 0 && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {medications.length}개
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {medications.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              추출된 약물 정보가 없습니다.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th
                      scope="col"
                      className="pb-2 text-left text-xs font-medium text-muted-foreground"
                    >
                      약물명
                    </th>
                    <th
                      scope="col"
                      className="pb-2 text-left text-xs font-medium text-muted-foreground"
                    >
                      성분명
                    </th>
                    <th
                      scope="col"
                      className="pb-2 text-left text-xs font-medium text-muted-foreground"
                    >
                      용량
                    </th>
                    <th
                      scope="col"
                      className="pb-2 text-left text-xs font-medium text-muted-foreground"
                    >
                      복약 횟수
                    </th>
                    <th
                      scope="col"
                      className="pb-2 text-left text-xs font-medium text-muted-foreground"
                    >
                      기간
                    </th>
                    <th
                      scope="col"
                      className="pb-2 text-left text-xs font-medium text-muted-foreground"
                    >
                      신뢰도
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {medications.map((m) => (
                    <tr key={m.id}>
                      <td className="py-2.5 font-medium">{m.medication_name}</td>
                      <td className="py-2.5 text-muted-foreground">{m.generic_name ?? "-"}</td>
                      <td className="py-2.5 text-muted-foreground">{m.dosage ?? "-"}</td>
                      <td className="py-2.5 text-muted-foreground">{m.frequency ?? "-"}</td>
                      <td className="py-2.5 text-muted-foreground">
                        {m.duration_days != null ? `${m.duration_days}일` : "-"}
                      </td>
                      <td className="py-2.5">
                        <ConfidenceBadge score={m.confidence_score} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Disease codes — prescription only */}
      {(doc.doc_type === "PRESCRIPTION" || diseaseCodes.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              질병분류기호
              {diseaseCodes.length > 0 && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  {diseaseCodes.length}개
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {diseaseCodes.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                추출된 질병분류기호가 없습니다.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b">
                    <tr>
                      <th
                        scope="col"
                        className="pb-2 text-left text-xs font-medium text-muted-foreground"
                      >
                        ICD-10 코드
                      </th>
                      <th
                        scope="col"
                        className="pb-2 text-left text-xs font-medium text-muted-foreground"
                      >
                        질병명
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {diseaseCodes.map((c) => (
                      <tr key={c.id}>
                        <td className="py-2.5 font-mono font-medium">{c.icd10_code}</td>
                        <td className="py-2.5 text-muted-foreground">{c.disease_name ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* OCR text */}
      {ocrText && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">OCR 원문 텍스트</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-60 overflow-y-auto whitespace-pre-wrap rounded-lg bg-muted p-4 text-xs leading-relaxed">
              {ocrText}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
