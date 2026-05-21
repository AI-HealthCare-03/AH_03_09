import { useQuery } from "@tanstack/react-query";
import { CloudUploadIcon, FileTextIcon, Loader2Icon } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDocuments, uploadDocuments } from "@/api/ocr";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import type { DocType, OcrStatus } from "@/types/api";

const ACCEPT = ["image/jpeg", "image/png", "application/pdf"];
const MAX_SIZE_MB = 10;
const MAX_FILES = 5;

const DOC_TYPE_LABEL: Partial<Record<DocType, string>> = {
  PRESCRIPTION: "처방전",
  DRUG_BAG: "약봉투",
  OTHER: "기타",
};

const STATUS_LABEL: Record<OcrStatus, string> = {
  PENDING: "대기",
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

function validateFiles(files: File[]): string | null {
  if (files.length > MAX_FILES) return `최대 ${MAX_FILES}개까지 업로드 가능합니다.`;
  for (const f of files) {
    if (!ACCEPT.includes(f.type)) return `${f.name}: JPEG·PNG·PDF만 허용됩니다.`;
    if (f.size > MAX_SIZE_MB * 1024 * 1024)
      return `${f.name}: 파일 크기는 ${MAX_SIZE_MB}MB 이하여야 합니다.`;
  }
  return null;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Upload() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [duplicateRecordId, setDuplicateRecordId] = useState<number | null>(null);

  const { data: recentDocs, isLoading: docsLoading } = useQuery({
    queryKey: ["ocr-documents", { size: 5 }],
    queryFn: () => fetchDocuments({ size: 5 }),
  });

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const merged = [...files, ...Array.from(incoming)].slice(0, MAX_FILES);
    const err = validateFiles(merged);
    setError(err);
    setDuplicateRecordId(null);
    if (!err) setFiles(merged);
  };

  const removeFile = (idx: number) => {
    setFiles(files.filter((_, i) => i !== idx));
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    setDuplicateRecordId(null);
    try {
      const res = await uploadDocuments(files);
      const first = res.uploaded_files[0];
      navigate(`/upload/processing/${first.job_id}`, {
        state: { uploadedFiles: res.uploaded_files },
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        try {
          const parsed = JSON.parse(e.body) as { detail: { existing_record_id: number } };
          setDuplicateRecordId(parsed.detail.existing_record_id);
        } catch {
          setError("이미 업로드된 파일입니다.");
        }
      } else {
        setError(
          e instanceof ApiError ? `업로드 실패: ${e.message}` : "알 수 없는 오류가 발생했습니다.",
        );
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">문서 업로드</h1>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Upload area — 2/3 on desktop */}
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>처방전 · 약봉투 업로드</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <label
                htmlFor="file-input"
                className={`flex cursor-pointer select-none flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 transition-colors ${
                  dragOver
                    ? "border-primary bg-primary/5"
                    : "border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/20"
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
              >
                <div className="flex size-14 items-center justify-center rounded-full bg-primary/10">
                  <CloudUploadIcon className="size-7 text-primary" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium">
                    파일을 드래그하거나 <span className="font-semibold text-primary">클릭</span>하여
                    선택
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    JPEG · PNG · PDF / 최대 {MAX_FILES}개 / 각 {MAX_SIZE_MB}MB 이하
                  </p>
                </div>
              </label>
              <input
                id="file-input"
                ref={inputRef}
                type="file"
                multiple
                accept=".jpg,.jpeg,.png,.pdf"
                className="hidden"
                onChange={(e) => addFiles(e.target.files)}
              />

              {files.length > 0 && (
                <div className="divide-y overflow-hidden rounded-lg border">
                  {files.map((f, i) => (
                    <div
                      key={`${f.name}-${f.size}-${f.lastModified}`}
                      className="flex items-center gap-3 px-4 py-3"
                    >
                      <FileTextIcon className="size-4 shrink-0 text-muted-foreground" />
                      <span className="flex-1 truncate text-sm font-medium">{f.name}</span>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {formatSize(f.size)}
                      </span>
                      <button
                        type="button"
                        className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:text-destructive"
                        onClick={() => removeFile(i)}
                        aria-label={`${f.name} 제거`}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {duplicateRecordId !== null && (
                <Alert>
                  <AlertDescription className="flex items-center justify-between gap-3">
                    <span>이미 업로드된 파일입니다.</span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="shrink-0"
                      onClick={() => navigate(`/upload/result/${duplicateRecordId}`)}
                    >
                      기존 문서 보기
                    </Button>
                  </AlertDescription>
                </Alert>
              )}

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button
                className="w-full"
                size="lg"
                disabled={files.length === 0 || !!error || duplicateRecordId !== null || uploading}
                onClick={handleUpload}
              >
                {uploading ? (
                  <>
                    <Loader2Icon className="mr-2 size-4 animate-spin" />
                    업로드 중...
                  </>
                ) : (
                  `OCR 추출 시작 (${files.length}개 파일)`
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Recent documents sidebar */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">내 문서 목록</CardTitle>
          </CardHeader>
          <CardContent>
            {docsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : !recentDocs || recentDocs.documents.length === 0 ? (
              <p className="py-4 text-center text-xs text-muted-foreground">
                업로드된 문서가 없습니다.
              </p>
            ) : (
              <>
                <ul className="divide-y">
                  {recentDocs.documents.map((doc) => (
                    <li key={doc.record_id}>
                      <button
                        type="button"
                        className="flex w-full items-center gap-2 rounded px-1 py-2.5 text-left transition-colors hover:bg-muted/40"
                        onClick={() =>
                          doc.ocr_status === "DONE"
                            ? navigate(`/upload/result/${doc.record_id}`)
                            : navigate(`/upload/processing/${doc.job_id}`)
                        }
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-medium">{doc.original_filename}</p>
                          {doc.doc_type && (
                            <p className="text-xs text-muted-foreground">
                              {DOC_TYPE_LABEL[doc.doc_type] ?? doc.doc_type}
                            </p>
                          )}
                        </div>
                        <Badge
                          variant={STATUS_VARIANT[doc.ocr_status]}
                          className="shrink-0 text-xs"
                        >
                          {STATUS_LABEL[doc.ocr_status]}
                        </Badge>
                      </button>
                    </li>
                  ))}
                </ul>
                {recentDocs.total > 5 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2 w-full text-xs"
                    onClick={() => navigate("/documents")}
                  >
                    전체 보기 ({recentDocs.total}개)
                  </Button>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
