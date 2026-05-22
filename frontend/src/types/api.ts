export interface ChatSessionResponse {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageResponse {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatMessageListResponse {
  messages: ChatMessageResponse[];
}

export interface SendMessageResponse {
  user_message: ChatMessageResponse;
  assistant_message: ChatMessageResponse;
}

export interface UserInfoResponse {
  id: number;
  kakao_id: string;
  email: string | null;
  name: string | null;
  gender: string | null;
  age_range: string | null;
  birthday: string | null;
  birthyear: string | null;
  phone_number: string | null;
  created_at: string | null;
}

// ── OCR ───────────────────────────────────────────────────────────────────────

export type OcrStatus = "PENDING" | "PROCESSING" | "DONE" | "FAILED";
export type DocType = "PRESCRIPTION" | "DRUG_BAG" | "OTHER";

export interface UploadedFileItem {
  record_id: number;
  job_id: string;
  ocr_status: OcrStatus;
  original_filename: string;
}

export interface OcrUploadResponse {
  uploaded_files: UploadedFileItem[];
  message: string;
}

export interface OcrJobStatusResponse {
  job_id: string;
  record_id: number;
  status: OcrStatus;
  progress_pct: number;
  message: string | null;
  result_url: string | null;
  estimated_remaining_seconds: number | null;
}

export interface MedicationResponse {
  id: number;
  medication_name: string;
  edi_code: string | null;
  generic_name: string | null;
  dosage: string | null;
  frequency: string | null;
  timing: string | null;
  duration_days: number | null;
  time_of_day: string[] | null;
  instructions: string | null;
  warnings: string[] | null;
  confidence_score: number | null;
  is_confirmed: boolean;
  is_active: boolean;
}

export interface DiseaseCodeResponse {
  id: number;
  icd10_code: string;
  disease_name: string | null;
  confidence_score: number | null;
  is_confirmed: boolean;
  is_active: boolean;
}

export interface OcrResultResponse {
  id: number;
  raw_text: string | null;
  processed_text: string | null;
  confidence_score: number | null;
  processing_time_ms: number | null;
  is_user_edited: boolean;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface OcrDocumentResponse {
  record_id: number;
  job_id: string;
  original_filename: string;
  doc_type: DocType | null;
  ocr_status: OcrStatus;
  issued_date: string | null;
  valid_until: string | null;
  hospital_name: string | null;
  thumbnail_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OcrDocumentDetailResponse extends OcrDocumentResponse {
  medications: MedicationResponse[];
  disease_codes: DiseaseCodeResponse[];
  result: OcrResultResponse | null;
}

export interface OcrDocumentListResponse {
  documents: OcrDocumentResponse[];
  total: number;
}
