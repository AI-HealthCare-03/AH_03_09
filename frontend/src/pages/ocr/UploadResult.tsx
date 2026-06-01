import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2Icon, Maximize2Icon, PencilIcon, PlusIcon, Trash2Icon, XIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  type MedicationCreateBody,
  type MedicationUpdateBody,
  addMedication,
  confirmDiseaseCodes,
  confirmMedications,
  confirmOcr,
  deleteMedication,
  fetchDocument,
  fetchDocumentFile,
  fetchOcrResult,
  reanalyzeDocument,
  searchDrugs,
  unconfirmDiseaseCodes,
  unconfirmMedications,
  updateDiseaseCode,
  updateMedication,
} from "@/api/ocr";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  const colorClass =
    pct >= 80
      ? "bg-green-100 text-green-800 border-green-200"
      : pct >= 60
        ? "bg-yellow-100 text-yellow-800 border-yellow-200"
        : "bg-red-100 text-red-800 border-red-200";
  return (
    <>
      <Badge className={colorClass}>{pct}%</Badge>
      {score < 0.7 && <p className="mt-1 text-xs text-amber-600">재촬영 권고</p>}
    </>
  );
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
  const [editingDiseaseId, setEditingDiseaseId] = useState<number | null>(null);
  const [editDiseaseCode, setEditDiseaseCode] = useState("");

  const [addModalOpen, setAddModalOpen] = useState(false);
  const [drugSearch, setDrugSearch] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [addForm, setAddForm] = useState<MedicationCreateBody>({
    medication_name: "",
    frequency: null,
    duration_days: null,
  });
  const [dupWarning, setDupWarning] = useState<string | null>(null);

  const resetAddForm = () => {
    setDrugSearch("");
    setAddForm({ medication_name: "", frequency: null, duration_days: null });
    setShowSuggestions(false);
    setDupWarning(null);
  };

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

  const updateDiseaseCodeMutation = useMutation({
    mutationFn: ({ codeId, icd10Code }: { codeId: number; icd10Code: string }) =>
      updateDiseaseCode(recordId, codeId, icd10Code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ocr-document", recordId] });
      setEditingDiseaseId(null);
      toast.success("질병분류기호가 수정되었습니다.");
    },
    onError: () => toast.error("수정에 실패했습니다. 다시 시도해주세요."),
  });

  const addMedMutation = useMutation({
    mutationFn: (body: MedicationCreateBody) => addMedication(recordId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ocr-document", recordId] });
      setAddModalOpen(false);
      resetAddForm();
      toast.success("약물이 추가되었습니다.");
    },
    onError: () => toast.error("추가에 실패했습니다. 다시 시도해주세요."),
  });

  const { data: drugSuggestions } = useQuery({
    queryKey: ["drug-search", drugSearch],
    queryFn: () => searchDrugs(drugSearch),
    enabled: drugSearch.length >= 2,
    staleTime: 30_000,
  });

  const findDuplicate = (name: string): string | null => {
    const n = name.toLowerCase().replace(/\s/g, "");
    for (const m of medications) {
      const e = m.medication_name.toLowerCase().replace(/\s/g, "");
      if (e.includes(n) || n.includes(e)) return m.medication_name;
    }
    return null;
  };

  const handleAddSubmit = (force = false) => {
    if (!force) {
      const dup = findDuplicate(addForm.medication_name);
      if (dup) {
        setDupWarning(dup);
        return;
      }
    }
    addMedMutation.mutate(addForm);
  };

  const confirmMutation = useMutation({
    mutationFn: (jobId: string) =>
      confirmOcr(jobId, { trigger_guide: true, trigger_chatbot_context: false }),
    onSuccess: () => navigate("/health-guide"),
  });

  const reanalyzeMutation = useMutation({
    mutationFn: () => reanalyzeDocument(recordId),
    onSuccess: (data) => navigate(`/upload/processing/${data.job_id}`, { state: { recordId } }),
    onError: () => toast.error("재추출에 실패했습니다. 다시 시도해주세요."),
  });

  const confirmMedMutation = useMutation({
    mutationFn: () => confirmMedications(recordId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ocr-document", recordId] }),
    onError: () => toast.error("확인 처리에 실패했습니다."),
  });

  const unconfirmMedMutation = useMutation({
    mutationFn: () => unconfirmMedications(recordId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ocr-document", recordId] }),
    onError: () => toast.error("확인 취소에 실패했습니다."),
  });

  const confirmDiseaseCodeMutation = useMutation({
    mutationFn: () => confirmDiseaseCodes(recordId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ocr-document", recordId] }),
    onError: () => toast.error("확인 처리에 실패했습니다."),
  });

  const unconfirmDiseaseCodeMutation = useMutation({
    mutationFn: () => unconfirmDiseaseCodes(recordId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ocr-document", recordId] }),
    onError: () => toast.error("확인 취소에 실패했습니다."),
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

  const medications = doc.medications.filter((m) => m.is_active).sort((a, b) => a.id - b.id);
  const diseaseCodes = doc.disease_codes.filter((c) => c.is_active);
  const ocrText = result?.processed_text ?? result?.raw_text;

  const allMedsConfirmed = medications.length > 0 && medications.every((m) => m.is_confirmed);
  const allDiseasesConfirmed = diseaseCodes.length === 0 || diseaseCodes.every((c) => c.is_confirmed);
  const isLocked = allMedsConfirmed; // 약물 전체 확인 완료 시 편집 잠금

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">분석 결과</h1>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => reanalyzeMutation.mutate()}
            disabled={reanalyzeMutation.isPending}
          >
            {reanalyzeMutation.isPending ? "요청 중..." : "재추출"}
          </Button>
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
              disabled={confirmMutation.isPending || !allMedsConfirmed}
              title={!allMedsConfirmed ? "약물 목록을 먼저 전체 확인해주세요" : undefined}
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
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">
              약물 목록
              {medications.length > 0 && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  {medications.length}개
                </span>
              )}
            </CardTitle>
            <div className="flex gap-2">
              {medications.length > 0 && (
                allMedsConfirmed ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => unconfirmMedMutation.mutate()}
                    disabled={unconfirmMedMutation.isPending}
                  >
                    {unconfirmMedMutation.isPending ? "처리 중..." : "확인 취소"}
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => confirmMedMutation.mutate()}
                    disabled={confirmMedMutation.isPending || editingId !== null}
                  >
                    <CheckCircle2Icon className="mr-1 size-3.5" />
                    {confirmMedMutation.isPending ? "처리 중..." : "전체 확인"}
                  </Button>
                )
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setAddModalOpen(true)}
                disabled={isLocked || editingId !== null}
              >
                <PlusIcon className="mr-1 size-3.5" />
                약물 추가
              </Button>
            </div>
          </div>
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
                    const isRowLocked = isLocked;

                    if (isEditing) {
                      return (
                        <tr key={m.id} className="bg-muted/20">
                          <td className="py-2.5 font-medium">{m.medication_name}</td>
                          <td className="py-2.5 font-mono text-muted-foreground">
                            {m.edi_code ?? "-"}
                          </td>
                          <td className="py-2.5 text-muted-foreground">{m.generic_name ?? "-"}</td>
                          <td className="py-2.5 text-muted-foreground">{m.dosage ?? "-"}</td>
                          <td className="py-1.5 pr-2">
                            <input
                              className="w-24 rounded border px-2 py-1 text-sm"
                              value={editForm.frequency ?? ""}
                              onChange={(e) =>
                                setEditForm((f) => ({ ...f, frequency: e.target.value || null }))
                              }
                            />
                          </td>
                          <td className="py-1.5 pr-2">
                            <input
                              type="number"
                              min={1}
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
                                disabled={isBusy}
                                onClick={() =>
                                  updateMedMutation.mutate({
                                    medId: m.id,
                                    body: {
                                      frequency: editForm.frequency,
                                      duration_days: editForm.duration_days,
                                    },
                                  })
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
                        <td className="py-2.5 font-medium">
                          <span className="flex items-center gap-1">
                            {m.is_confirmed && (
                              <CheckCircle2Icon className="size-3.5 shrink-0 text-green-500" aria-label="확인됨" />
                            )}
                            {m.medication_name}
                          </span>
                        </td>
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
                              disabled={isBusy || editingId !== null || isRowLocked}
                              onClick={() => {
                                setEditForm({
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
                              disabled={isBusy || editingId !== null || isRowLocked}
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
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">
                질병분류기호
                {diseaseCodes.length > 0 && (
                  <span className="ml-2 text-sm font-normal text-muted-foreground">
                    {diseaseCodes.length}개
                  </span>
                )}
              </CardTitle>
              {diseaseCodes.length > 0 && (
                allDiseasesConfirmed ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => unconfirmDiseaseCodeMutation.mutate()}
                    disabled={unconfirmDiseaseCodeMutation.isPending}
                  >
                    {unconfirmDiseaseCodeMutation.isPending ? "처리 중..." : "확인 취소"}
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => confirmDiseaseCodeMutation.mutate()}
                    disabled={confirmDiseaseCodeMutation.isPending || editingDiseaseId !== null}
                  >
                    <CheckCircle2Icon className="mr-1 size-3.5" />
                    {confirmDiseaseCodeMutation.isPending ? "처리 중..." : "전체 확인"}
                  </Button>
                )
              )}
            </div>
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
                      <th scope="col" className="pb-2 text-left text-xs font-medium text-muted-foreground">
                        ICD-10 코드
                      </th>
                      <th scope="col" className="pb-2 text-left text-xs font-medium text-muted-foreground">
                        질병명
                      </th>
                      <th scope="col" className="pb-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {diseaseCodes.map((c) => {
                      const isEditing = editingDiseaseId === c.id;
                      const isBusy = updateDiseaseCodeMutation.isPending && updateDiseaseCodeMutation.variables?.codeId === c.id;
                      if (isEditing) {
                        return (
                          <tr key={c.id} className="bg-muted/20">
                            <td className="py-1.5 pr-2">
                              <input
                                className="w-28 rounded border px-2 py-1 font-mono text-sm"
                                value={editDiseaseCode}
                                onChange={(e) => setEditDiseaseCode(e.target.value)}
                              />
                            </td>
                            <td className="py-1.5 text-muted-foreground text-sm italic">자동 갱신</td>
                            <td className="py-1.5">
                              <div className="flex gap-1">
                                <Button
                                  size="sm"
                                  disabled={isBusy || !editDiseaseCode.trim()}
                                  onClick={() => updateDiseaseCodeMutation.mutate({ codeId: c.id, icd10Code: editDiseaseCode.trim() })}
                                >
                                  저장
                                </Button>
                                <Button size="sm" variant="ghost" disabled={isBusy} onClick={() => setEditingDiseaseId(null)}>
                                  <XIcon className="size-4" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      }
                      return (
                        <tr key={c.id} className="transition-colors hover:bg-muted/20">
                          <td className="py-2.5 font-mono font-medium">
                            <span className="flex items-center gap-1">
                              {c.is_confirmed && (
                                <CheckCircle2Icon className="size-3.5 shrink-0 text-green-500" aria-label="확인됨" />
                              )}
                              {c.icd10_code}
                            </span>
                          </td>
                          <td className="py-2.5 text-muted-foreground">{c.disease_name ?? "-"}</td>
                          <td className="py-2.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2"
                              disabled={editingDiseaseId !== null || editingId !== null || allDiseasesConfirmed}
                              onClick={() => { setEditDiseaseCode(c.icd10_code); setEditingDiseaseId(c.id); }}
                            >
                              <PencilIcon className="size-3.5" />
                            </Button>
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
              <DialogTitle className="sr-only">원본 문서 보기</DialogTitle>
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

      {/* Add medication modal */}
      <Dialog
        open={addModalOpen}
        onOpenChange={(open) => {
          setAddModalOpen(open);
          if (!open) resetAddForm();
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>약물 추가</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Drug name autocomplete */}
            <div>
              <label className="mb-1 block text-sm font-medium">
                약물명 <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <input
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="약물명 검색 또는 직접 입력"
                  value={drugSearch}
                  onChange={(e) => {
                    setDrugSearch(e.target.value);
                    setAddForm((f) => ({ ...f, medication_name: e.target.value }));
                    setShowSuggestions(true);
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                />
                {showSuggestions && drugSuggestions && drugSuggestions.length > 0 && (
                  <ul className="absolute z-50 mt-1 max-h-48 w-full overflow-y-auto rounded-md border bg-background shadow-md">
                    {drugSuggestions.map((s) => (
                      <li
                        key={s.item_name}
                        className="cursor-pointer px-3 py-2 text-sm hover:bg-muted"
                        onMouseDown={() => {
                          setDrugSearch(s.item_name);
                          setAddForm((f) => ({ ...f, medication_name: s.item_name }));
                          setShowSuggestions(false);
                        }}
                      >
                        {s.item_name}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Frequency */}
            <div>
              <label className="mb-1 block text-sm font-medium">복약 횟수</label>
              <input
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="예: 1일 3회"
                value={addForm.frequency ?? ""}
                onChange={(e) =>
                  setAddForm((f) => ({ ...f, frequency: e.target.value || null }))
                }
              />
            </div>

            {/* Duration */}
            <div>
              <label className="mb-1 block text-sm font-medium">기간 (일)</label>
              <input
                type="number"
                min={1}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="예: 30"
                value={addForm.duration_days ?? ""}
                onChange={(e) =>
                  setAddForm((f) => ({
                    ...f,
                    duration_days: e.target.value ? Number(e.target.value) : null,
                  }))
                }
              />
            </div>
          </div>

          {dupWarning && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              <span className="font-medium">"{dupWarning}"</span>이(가) 이미 목록에 있습니다.
              그래도 추가하시겠습니까?
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setAddModalOpen(false)}>
              취소
            </Button>
            {dupWarning ? (
              <Button
                disabled={addMedMutation.isPending}
                onClick={() => handleAddSubmit(true)}
              >
                {addMedMutation.isPending ? "추가 중..." : "그래도 추가"}
              </Button>
            ) : (
              <Button
                disabled={!addForm.medication_name.trim() || addMedMutation.isPending}
                onClick={() => handleAddSubmit()}
              >
                {addMedMutation.isPending ? "추가 중..." : "추가"}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
