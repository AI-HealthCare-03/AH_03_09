import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangleIcon, CheckCircle2Icon, InfoIcon, Maximize2Icon, PencilIcon, PlusIcon, Trash2Icon, XIcon } from "lucide-react";
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
  patchDocument,
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
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { DocType } from "@/types/api";

const DOC_TYPE_LABEL: Record<DocType, string> = {
  PRESCRIPTION: "처방전",
  DRUG_BAG: "약봉투",
  OTHER: "기타",
};


const ALL_DOC_TYPES: DocType[] = ["PRESCRIPTION", "DRUG_BAG", "OTHER"];

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

  const [editNameModalOpen, setEditNameModalOpen] = useState(false);
  const [editNameSearch, setEditNameSearch] = useState("");
  const [showEditNameSuggestions, setShowEditNameSuggestions] = useState(false);
  const [editNameFocusField, setEditNameFocusField] = useState<"medication_name" | "generic_name">("medication_name");
  const [editNameModalForm, setEditNameModalForm] = useState({ medication_name: "", generic_name: "", selected_from_db: false });

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

  const { data: editNameSuggestions } = useQuery({
    queryKey: ["drug-search", editNameSearch],
    queryFn: () => searchDrugs(editNameSearch),
    enabled: editNameSearch.length >= 2,
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

  const patchDocTypeMutation = useMutation({
    mutationFn: (docType: DocType) => patchDocument(recordId, { doc_type: docType }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ocr-document", recordId] });
      toast.success("문서 유형이 변경되었습니다.");
    },
    onError: () => toast.error("문서 유형 변경에 실패했습니다."),
  });

  const confirmMutation = useMutation({
    mutationFn: (jobId: string) =>
      confirmOcr(jobId, { trigger_guide: true, trigger_chatbot_context: false }),
    onSuccess: (data) =>
      navigate(`/health-guide?job_id=${data.guide_job_id}`),
    onError: () => toast.error("가이드 생성에 실패했습니다. 다시 시도해주세요."),
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
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <Button variant="outline" size="sm" onClick={() => navigate("/upload")}>
                새 업로드
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              결과가 불만족스러우면 더 선명한 사진으로 새 파일을 업로드해 보세요.
            </TooltipContent>
          </Tooltip>
          <Button variant="outline" size="sm" onClick={() => navigate("/documents")}>
            목록으로
          </Button>
          {doc?.job_id && (
            <Button
              size="sm"
              onClick={() => confirmMutation.mutate(doc.job_id)}
              disabled={confirmMutation.isPending || !allMedsConfirmed}
            >
              {confirmMutation.isPending ? "요청 중..." : "복약 가이드 생성"}
            </Button>
          )}
        </div>
      </div>

      {/* 가이드 생성 안내 — 약물이 1개 이상 있는데 아직 미확인인 경우만 표시 */}
      {doc?.job_id && medications.length > 0 && !allMedsConfirmed && (
        <div className="flex items-center justify-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          <InfoIcon className="size-4 shrink-0 text-blue-500" />
          <span>
            약물 목록을 검토한 후 <strong>전체 확인</strong> 버튼을 누르고,{" "}
            <strong>복약 가이드 생성</strong> 버튼을 누르면 복약 및 생활 가이드를 받아볼 수 있어요.
          </span>
        </div>
      )}

      {/* Document info */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">문서 정보</CardTitle>
            <div className="flex gap-1">
              {ALL_DOC_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  disabled={patchDocTypeMutation.isPending}
                  onClick={() => { if (type !== doc.doc_type) patchDocTypeMutation.mutate(type); }}
                  className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                    doc.doc_type === type
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-muted-foreground/20 text-muted-foreground hover:border-primary/40"
                  }`}
                >
                  {DOC_TYPE_LABEL[type]}
                </button>
              ))}
            </div>
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
          {medications.some((m) => m.is_db_matched === false) && (
            <div className="mb-3 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              <AlertTriangleIcon className="mt-0.5 size-4 shrink-0" />
              <span>
                <span className="font-medium">DB에서 확인되지 않은 약물</span>이 있습니다.
                약물명 옆 ⚠ 표시된 항목은 OCR 원문 그대로 유지된 것이므로,
                수정 버튼으로 약물명·성분명을 직접 확인해 주세요.
              </span>
            </div>
          )}
          {medications.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              추출된 약물 정보가 없습니다.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    {[
                      { label: "약물명", className: "w-45 max-w-45" },
                      { label: "EDI 코드", className: "whitespace-nowrap" },
                      { label: "성분명", className: "" },
                      { label: "용량", className: "whitespace-nowrap" },
                      { label: "복약 횟수", className: "whitespace-nowrap" },
                      { label: "기간", className: "whitespace-nowrap" },
                      { label: "", className: "" },
                    ].map((h) => (
                      <th
                        key={h.label}
                        scope="col"
                        className={`pb-2 text-left text-xs font-medium text-muted-foreground ${h.className}`}
                      >
                        {h.label}
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
                      const openEditNameModal = (focusField: "medication_name" | "generic_name") => {
                        setEditNameModalForm({
                          medication_name: editForm.medication_name ?? "",
                          generic_name: editForm.generic_name ?? "",
                          selected_from_db: false,
                        });
                        setEditNameSearch(editForm.medication_name ?? "");
                        setShowEditNameSuggestions(false);
                        setEditNameFocusField(focusField);
                        setEditNameModalOpen(true);
                      };
                      return (
                        <tr key={m.id} className="bg-muted/20">
                          <td className="py-1.5 pr-2">
                            <button
                              type="button"
                              className="flex min-w-36 items-center gap-1 rounded border border-dashed px-2 py-1 text-sm hover:bg-muted"
                              onClick={() => openEditNameModal("medication_name")}
                            >
                              <PencilIcon className="size-3 shrink-0 text-muted-foreground" />
                              <span className="truncate">{editForm.medication_name}</span>
                            </button>
                          </td>
                          <td className="py-2.5 font-mono text-muted-foreground">
                            {m.edi_code ?? "-"}
                          </td>
                          <td className="py-1.5 pr-2">
                            <button
                              type="button"
                              className="flex min-w-28 items-center gap-1 rounded border border-dashed px-2 py-1 text-sm hover:bg-muted"
                              onClick={() => openEditNameModal("generic_name")}
                            >
                              <PencilIcon className="size-3 shrink-0 text-muted-foreground" />
                              <span className="truncate text-muted-foreground">
                                {editForm.generic_name || "성분명 입력"}
                              </span>
                            </button>
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
                                      medication_name: editForm.medication_name,
                                      generic_name: editForm.generic_name,
                                      dosage: editForm.dosage,
                                      frequency: editForm.frequency,
                                      duration_days: editForm.duration_days,
                                      is_db_matched: editForm.is_db_matched,
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
                        <td className="w-45 max-w-45 py-2.5 font-medium">
                          <Tooltip delayDuration={0}>
                            <TooltipTrigger asChild>
                              <span className="flex min-w-0 items-center gap-1">
                                {m.is_confirmed && (
                                  <CheckCircle2Icon className="size-3.5 shrink-0 text-green-500" aria-label="확인됨" />
                                )}
                                {m.is_db_matched === false && (
                                  <AlertTriangleIcon
                                    className="size-3.5 shrink-0 text-amber-500"
                                    aria-label="약물명 미확인 — 직접 확인 후 수정해 주세요"
                                  />
                                )}
                                <span className="truncate">{m.medication_name}</span>
                              </span>
                            </TooltipTrigger>
                            <TooltipContent>{m.medication_name}</TooltipContent>
                          </Tooltip>
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
                                  medication_name: m.medication_name,
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

      {/* Edit medication name / generic name modal */}
      <Dialog
        open={editNameModalOpen}
        onOpenChange={(open) => {
          setEditNameModalOpen(open);
          if (!open) {
            setEditNameSearch("");
            setShowEditNameSuggestions(false);
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>약물명 / 성분명 수정</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="mb-1 block text-sm font-medium">
                약물명 <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <input
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="약물명 검색 또는 직접 입력"
                  value={editNameSearch}
                  autoFocus={editNameFocusField === "medication_name"}
                  onChange={(e) => {
                    setEditNameSearch(e.target.value);
                    setEditNameModalForm((f) => ({ ...f, medication_name: e.target.value, selected_from_db: false }));
                    setShowEditNameSuggestions(true);
                  }}
                  onFocus={() => setShowEditNameSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowEditNameSuggestions(false), 150)}
                />
                {showEditNameSuggestions && editNameSuggestions && editNameSuggestions.length > 0 && (
                  <ul className="absolute z-50 mt-1 max-h-48 w-full overflow-y-auto rounded-md border bg-background shadow-md">
                    {editNameSuggestions.map((s) => (
                      <li
                        key={s.item_name}
                        className="cursor-pointer px-3 py-2 text-sm hover:bg-muted"
                        onMouseDown={() => {
                          setEditNameSearch(s.item_name);
                          setEditNameModalForm((f) => ({ ...f, medication_name: s.item_name, selected_from_db: true }));
                          setShowEditNameSuggestions(false);
                        }}
                      >
                        {s.item_name}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                성분명{" "}
                <span className="text-xs font-normal text-muted-foreground">(선택)</span>
              </label>
              <input
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="성분명 직접 입력"
                autoFocus={editNameFocusField === "generic_name"}
                value={editNameModalForm.generic_name}
                onChange={(e) =>
                  setEditNameModalForm((f) => ({ ...f, generic_name: e.target.value }))
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditNameModalOpen(false)}>
              취소
            </Button>
            <Button
              disabled={!editNameModalForm.medication_name.trim()}
              onClick={() => {
                setEditForm((f) => ({
                  ...f,
                  medication_name: editNameModalForm.medication_name,
                  generic_name: editNameModalForm.generic_name || null,
                  ...(editNameModalForm.selected_from_db && { is_db_matched: true }),
                }));
                setEditNameModalOpen(false);
                setEditNameSearch("");
                setShowEditNameSuggestions(false);
              }}
            >
              확인
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
