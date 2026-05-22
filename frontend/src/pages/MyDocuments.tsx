import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2Icon } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { deleteDocument, fetchDocuments } from "@/api/ocr";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { DocType, OcrStatus } from "@/types/api";

const DOC_TYPE_FILTERS: { value: DocType | null; label: string }[] = [
  { value: null, label: "전체" },
  { value: "PRESCRIPTION", label: "처방전" },
  { value: "DRUG_BAG", label: "약봉투" },
  { value: "OTHER", label: "기타" },
];

const STATUS_FILTERS: { value: OcrStatus | null; label: string }[] = [
  { value: null, label: "전체" },
  { value: "DONE", label: "완료" },
  { value: "PROCESSING", label: "처리 중" },
  { value: "PENDING", label: "대기 중" },
  { value: "FAILED", label: "실패" },
];

const DOC_TYPE_LABEL: Partial<Record<DocType, string>> = {
  PRESCRIPTION: "처방전",
  DRUG_BAG: "약봉투",
  OTHER: "기타",
};

const STATUS_LABEL: Record<OcrStatus, string> = {
  PENDING: "대기 중",
  PROCESSING: "처리 중",
  DONE: "완료",
  FAILED: "실패",
};

const STATUS_VARIANT: Record<OcrStatus, "default" | "secondary" | "outline" | "destructive"> = {
  PENDING: "outline",
  PROCESSING: "secondary",
  DONE: "default",
  FAILED: "destructive",
};

const PAGE_SIZE = 10;

export default function MyDocuments() {
  const navigate = useNavigate();
  const [docType, setDocType] = useState<DocType | null>(null);
  const [ocrStatus, setOcrStatus] = useState<OcrStatus | null>(null);
  const [sort, setSort] = useState("created_at_desc");
  const [page, setPage] = useState(1);
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["ocr-documents", { docType, ocrStatus, sort, page }],
    queryFn: () =>
      fetchDocuments({
        page,
        size: PAGE_SIZE,
        doc_type: docType,
        ocr_status: ocrStatus,
        sort,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">내 문서</h1>
          <Button size="sm" onClick={() => navigate("/upload")}>
            새 업로드
          </Button>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle>업로드한 문서 목록</CardTitle>
              {data && <span className="text-sm text-muted-foreground">총 {data.total}개</span>}
            </div>

            <div className="space-y-2 pt-2">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="w-14 shrink-0 text-xs text-muted-foreground">문서 유형</span>
                {DOC_TYPE_FILTERS.map((f) => (
                  <button
                    key={f.label}
                    type="button"
                    onClick={() => {
                      setDocType(f.value);
                      setPage(1);
                    }}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      docType === f.value
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground hover:bg-muted/70"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                <span className="w-14 shrink-0 text-xs text-muted-foreground">OCR 상태</span>
                {STATUS_FILTERS.map((f) => (
                  <button
                    key={f.label}
                    type="button"
                    onClick={() => {
                      setOcrStatus(f.value);
                      setPage(1);
                    }}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      ocrStatus === f.value
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground hover:bg-muted/70"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2">
                <span className="w-14 shrink-0 text-xs text-muted-foreground">정렬</span>
                <select
                  aria-label="정렬 순서"
                  className="rounded-md border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
                  value={sort}
                  onChange={(e) => {
                    setSort(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="created_at_desc">최신순</option>
                  <option value="created_at_asc">오래된순</option>
                </select>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            {isLoading ? (
              <div className="space-y-2 p-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : !data || data.documents.length === 0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                {docType !== null || ocrStatus !== null
                  ? "조건에 맞는 문서가 없습니다."
                  : "업로드된 문서가 없습니다."}
              </p>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b bg-muted/40">
                      <tr>
                        <th
                          scope="col"
                          className="px-4 py-3 text-left text-xs font-medium text-muted-foreground"
                        >
                          파일명
                        </th>
                        <th
                          scope="col"
                          className="px-4 py-3 text-left text-xs font-medium text-muted-foreground"
                        >
                          문서 유형
                        </th>
                        <th
                          scope="col"
                          className="px-4 py-3 text-left text-xs font-medium text-muted-foreground"
                        >
                          업로드일시
                        </th>
                        <th
                          scope="col"
                          className="px-4 py-3 text-left text-xs font-medium text-muted-foreground"
                        >
                          OCR 상태
                        </th>
                        <th
                          scope="col"
                          className="px-4 py-3 text-left text-xs font-medium text-muted-foreground"
                        >
                          관리
                        </th>
                        <th
                          scope="col"
                          className="px-4 py-3 text-left text-xs font-medium text-muted-foreground"
                        >
                          삭제
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data.documents.map((doc) => (
                        <tr key={doc.record_id} className="transition-colors hover:bg-muted/30">
                          <td className="px-4 py-3">
                            <p className="max-w-[200px] truncate font-medium">
                              {doc.original_filename}
                            </p>
                            {doc.hospital_name && (
                              <p className="text-xs text-muted-foreground">{doc.hospital_name}</p>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {doc.doc_type ? (
                              <Badge variant="outline">
                                {DOC_TYPE_LABEL[doc.doc_type] ?? doc.doc_type}
                              </Badge>
                            ) : (
                              <span className="text-xs text-muted-foreground">-</span>
                            )}
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 text-xs text-muted-foreground">
                            {new Date(doc.created_at).toLocaleString("ko-KR", {
                              year: "numeric",
                              month: "2-digit",
                              day: "2-digit",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={STATUS_VARIANT[doc.ocr_status]}>
                              {STATUS_LABEL[doc.ocr_status]}
                            </Badge>
                          </td>
                          <td className="px-4 py-3">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="-ml-3"
                              onClick={() =>
                                doc.ocr_status === "DONE"
                                  ? navigate(`/upload/result/${doc.record_id}`)
                                  : navigate(`/upload/processing/${doc.job_id}`)
                              }
                            >
                              {doc.ocr_status === "DONE"
                                ? "결과 보기"
                                : doc.ocr_status === "FAILED"
                                  ? "실패 내역"
                                  : "처리 현황"}
                            </Button>
                          </td>
                          <td className="px-4 py-3">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="-ml-3 text-destructive hover:text-destructive"
                              onClick={() =>
                                setDeleteTarget({
                                  id: doc.record_id,
                                  name: doc.original_filename,
                                })
                              }
                            >
                              <Trash2Icon className="size-4" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {totalPages > 1 && (
                  <div className="flex items-center justify-between border-t px-4 py-3">
                    <p className="text-xs text-muted-foreground">
                      {page} / {totalPages} 페이지
                    </p>
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={page <= 1}
                        onClick={() => setPage(page - 1)}
                      >
                        이전
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={page >= totalPages}
                        onClick={() => setPage(page + 1)}
                      >
                        다음
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={deleteTarget !== null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>문서 삭제</DialogTitle>
            <DialogDescription>
              <span className="font-medium text-foreground">{deleteTarget?.name}</span> 문서를
              삭제하시겠습니까?
              <br />
              삭제 후 30일간 복구 가능하며, 이후 완전히 삭제됩니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleting}>
              취소
            </Button>
            <Button
              variant="destructive"
              disabled={deleting}
              onClick={async () => {
                if (!deleteTarget) return;
                setDeleting(true);
                try {
                  await deleteDocument(deleteTarget.id);
                  toast.success("문서가 삭제되었습니다.");
                  setDeleteTarget(null);
                  queryClient.invalidateQueries({ queryKey: ["ocr-documents"] });
                } catch {
                  toast.error("삭제에 실패했습니다. 다시 시도해주세요.");
                } finally {
                  setDeleting(false);
                }
              }}
            >
              {deleting ? "삭제 중..." : "삭제"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
