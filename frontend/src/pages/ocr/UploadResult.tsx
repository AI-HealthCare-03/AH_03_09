import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Maximize2Icon, PencilIcon, Trash2Icon, XIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  type MedicationUpdateBody,
  confirmOcr,
  deleteMedication,
  fetchDocument,
  fetchDocumentFile,
  fetchOcrResult,
  updateMedication,
} from "@/api/ocr";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent } from "@/components/ui/dialog";
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
  const queryClient = useQueryClient();

  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<MedicationUpdateBody>({});

  const updateMedMutation = useMutation({
    mutationFn: ({ medId, body }: { medId: number; body: MedicationUpdateBody }) =>
      updateMedication(recordId, medId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ocr-document", recordId] });
      setEditingId(null);
      toast.success("약물 정보가 수정되었습니다.");
    },
    onError: () => toast.error("수정에 실패했습니다. 다시 시도해주세요."),
  });

  const deleteMedMutation = useMutation({
    mutationFn: (medId: number) => deleteMedication(recordId, medId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ocr-document", recordId] });
      toast.success("약물이 삭제되었습니다.");
    },
    onError: () => toast.error("삭제에 실패했습니다. 다시 시도해주세요."),
  });

  const confirmMutation = useMutation({
    mutationFn: (jobId: string) =>
      confirmOcr(jobId, { trigger_guide: true, trigger_chatbot_context: false }),
    onSuccess: () => navigate("/health-guide"),
  });

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
          {doc?.job_id && (
            <Button
              size="sm"
              onClick={() => confirmMutation.mutate(doc.job_id)}
              disabled={confirmMutation.isPending}
            >
              {confirmMutation.isPending ? "요청 중..." : "복약 가이드 생성"}
            </Button>
          )}
        </div>
      </div>

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
                    {["약물명", "EDI 코드", "성분명", "용량", "복약 횟수", "기간", ""].map((h) => (
                      <th
                        key={h}
                        scope="col"
                        className="pb-2 text-left text-xs font-medium text-muted-foreground"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {medications.map((m) => {
                    const isEditing = editingId === m.id;
                    const isBusy =
                      (updateMedMutation.isPending && updateMedMutation.variables?.medId === m.id) ||
                      (deleteMedMutation.isPending && deleteMedMutation.variables === m.id);

                    if (isEditing) {
                      return (
                        <tr key={m.id} className="bg-muted/20">
                          <td className="py-1.5 pr-2">
                            <input
                              className="w-full rounded border px-2 py-1 text-sm"
                              value={editForm.medication_name ?? ""}
                              onChange={(e) =>
                                setEditForm((f) => ({ ...f, medication_name: e.target.value }))
                              }
                            />
                          </td>
                          <td className="py-1.5 pr-2">
                            <input
                              className="w-24 rounded border px-2 py-1 font-mono text-sm"
                              value={editForm.edi_code ?? ""}
                              onChange={(e) =>
                                setEditForm((f) => ({
                                  ...f,
                                  edi_code: e.target.value || null,
                                }))
                              }
                            />
                          </td>
                          <td className="py-1.5 pr-2">
                            <input
                              className="w-28 rounded border px-2 py-1 text-sm"
                              value={editForm.generic_name ?? ""}
                              onChange={(e) =>
                                setEditForm((f) => ({
                                  ...f,
                                  generic_name: e.target.value || null,
                                }))
                              }
                            />
                          </td>
                          <td className="py-1.5 pr-2">
                            <input
                              className="w-20 rounded border px-2 py-1 text-sm"
                              value={editForm.dosage ?? ""}
                              onChange={(e) =>
                                setEditForm((f) => ({ ...f, dosage: e.target.value || null }))
                              }
                            />
                          </td>
                          <td className="py-1.5 pr-2">
                            <input
                              className="w-24 rounded border px-2 py-1 text-sm"
                              value={editForm.frequency ?? ""}
                              onChange={(e) =>
                                setEditForm((f) => ({
                                  ...f,
                                  frequency: e.target.value || null,
                                }))
                              }
                            />
                          </td>
                          <td className="py-1.5 pr-2">
                            <input
                              type="number"
                              className="w-16 rounded border px-2 py-1 text-sm"
                              value={editForm.duration_days ?? ""}
                              onChange={(e) =>
                                setEditForm((f) => ({
                                  ...f,
                                  duration_days: e.target.value ? Number(e.target.value) : null,
                                }))
                              }
                            />
                          </td>
                          <td className="py-1.5">
                            <div className="flex gap-1">
                              <Button
                                size="sm"
                                disabled={isBusy || !editForm.medication_name?.trim()}
                                onClick={() =>
                                  updateMedMutation.mutate({ medId: m.id, body: editForm })
                                }
                              >
                                저장
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={isBusy}
                                onClick={() => setEditingId(null)}
                              >
                                <XIcon className="size-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    }

                    return (
                      <tr key={m.id} className="transition-colors hover:bg-muted/20">
                        <td className="py-2.5 font-medium">{m.medication_name}</td>
                        <td className="py-2.5 font-mono text-muted-foreground">
                          {m.edi_code ?? "-"}
                        </td>
                        <td className="py-2.5 text-muted-foreground">{m.generic_name ?? "-"}</td>
                        <td className="py-2.5 text-muted-foreground">{m.dosage ?? "-"}</td>
                        <td className="py-2.5 text-muted-foreground">{m.frequency ?? "-"}</td>
                        <td className="py-2.5 text-muted-foreground">
                          {m.duration_days != null ? `${m.duration_days}일` : "-"}
                        </td>
                        <td className="py-2.5">
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2"
                              disabled={isBusy || editingId !== null}
                              onClick={() => {
                                setEditForm({
                                  medication_name: m.medication_name,
                                  edi_code: m.edi_code,
                                  generic_name: m.generic_name,
                                  dosage: m.dosage,
                                  frequency: m.frequency,
                                  duration_days: m.duration_days,
                                });
                                setEditingId(m.id);
                              }}
                            >
                              <PencilIcon className="size-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-destructive hover:text-destructive"
                              disabled={isBusy || editingId !== null}
                              onClick={() => deleteMedMutation.mutate(m.id)}
                            >
                              <Trash2Icon className="size-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
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

      {/* File preview */}
      {fileUrl && (
        <>
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">원본 문서</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setModalOpen(true)}>
                  <Maximize2Icon className="mr-1.5 size-4" />
                  전체 화면
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex justify-center">
              {doc.original_filename.toLowerCase().endsWith(".pdf") ? (
                <embed src={fileUrl} type="application/pdf" className="h-64 w-full rounded" />
              ) : (
                <img
                  src={fileUrl}
                  alt={doc.original_filename}
                  className="max-h-64 cursor-zoom-in rounded object-contain"
                  onClick={() => setModalOpen(true)}
                />
              )}
            </CardContent>
          </Card>

          <Dialog open={modalOpen} onOpenChange={setModalOpen}>
            <DialogContent className="top-0 left-0 w-screen h-screen max-w-none sm:max-w-none translate-x-0 translate-y-0 rounded-none flex flex-col p-4">
              {doc.original_filename.toLowerCase().endsWith(".pdf") ? (
                <embed src={fileUrl} type="application/pdf" className="flex-1 rounded" />
              ) : (
                <div className="flex flex-1 items-center justify-center overflow-auto">
                  <img
                    src={fileUrl}
                    alt={doc.original_filename}
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
              )}
            </DialogContent>
          </Dialog>
        </>
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
