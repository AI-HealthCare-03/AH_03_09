import { request } from "@/lib/api";
import { postMultipart } from "@/lib/apiMultipart";
import type {
  DiseaseCodeResponse,
  DocType,
  MedicationResponse,
  OcrDocumentDetailResponse,
  OcrDocumentListResponse,
  OcrDocumentResponse,
  OcrJobStatusResponse,
  OcrResultResponse,
  OcrStatus,
  OcrUploadResponse,
} from "@/types/api";

export function uploadDocuments(files: File[]): Promise<OcrUploadResponse> {
  const formData = new FormData();
  for (const f of files) {
    formData.append("files", f);
  }
  return postMultipart<OcrUploadResponse>("/ocr/upload", formData);
}

export function fetchJobStatus(jobId: string): Promise<OcrJobStatusResponse> {
  return request<OcrJobStatusResponse>(`/ocr/jobs/${jobId}/status`);
}

export function fetchDocument(recordId: number): Promise<OcrDocumentDetailResponse> {
  return request<OcrDocumentDetailResponse>(`/ocr/records/${recordId}`);
}

export function fetchDocuments(params?: {
  page?: number;
  size?: number;
  doc_type?: DocType | null;
  ocr_status?: OcrStatus | null;
  sort?: string;
}): Promise<OcrDocumentListResponse> {
  const q = new URLSearchParams();
  if (params?.page != null) q.set("page", String(params.page));
  if (params?.size != null) q.set("size", String(params.size));
  if (params?.doc_type) q.set("doc_type", params.doc_type);
  if (params?.ocr_status) q.set("ocr_status", params.ocr_status);
  if (params?.sort) q.set("sort", params.sort);
  const qs = q.toString();
  return request<OcrDocumentListResponse>(qs ? `/ocr/records?${qs}` : "/ocr/records");
}

export function patchDocument(
  recordId: number,
  body: { doc_type?: DocType },
): Promise<OcrDocumentResponse> {
  return request<OcrDocumentResponse>(`/ocr/records/${recordId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchOcrResult(recordId: number): Promise<OcrResultResponse> {
  return request<OcrResultResponse>(`/ocr/records/${recordId}/result`);
}

export function fetchMedications(recordId: number): Promise<MedicationResponse[]> {
  return request<MedicationResponse[]>(`/ocr/records/${recordId}/medications`);
}

export function fetchDiseaseCodes(recordId: number): Promise<DiseaseCodeResponse[]> {
  return request<DiseaseCodeResponse[]>(`/ocr/records/${recordId}/disease-codes`);
}

export function deleteDocument(recordId: number): Promise<void> {
  return request<void>(`/ocr/records/${recordId}`, { method: "DELETE" });
}
