export interface HealthProfileResponse {
  id: number;
  gender: "M" | "F" | "OTHER" | null;
  age_range: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  blood_pressure_systolic: number | null;
  blood_pressure_diastolic: number | null;
  primary_conditions: string[];
  allergies: string[];
  current_medications: string[];
  lifestyle_exercise: "REGULAR" | "IRREGULAR" | "NONE";
  lifestyle_smoking: boolean;
  lifestyle_alcohol: "NONE" | "MODERATE" | "HEAVY";
  updated_at: string;
}

export interface HealthProfileUpdateRequest {
  gender?: "M" | "F" | "OTHER";
  age_range?: string;
  height_cm?: number;
  weight_kg?: number;
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  primary_conditions?: string[];
  allergies?: string[];
  current_medications?: string[];
  lifestyle_exercise?: "REGULAR" | "IRREGULAR" | "NONE";
  lifestyle_smoking?: boolean;
  lifestyle_alcohol?: "NONE" | "MODERATE" | "HEAVY";
}

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
  feedback?: "good" | "bad" | null;
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
  reanalyze_count: number;
  retake_recommended: boolean;
}

export interface OcrConfirmResponse {
  record_id: number;
  job_id: string;
  guide_job_id: string | null;
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
  is_db_matched: boolean | null;
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
  low_confidence: boolean;
}

export interface OcrDocumentDetailResponse extends OcrDocumentResponse {
  medications: MedicationResponse[];
  disease_codes: DiseaseCodeResponse[];
  result: OcrResultResponse | null;
  guide_job_id: string | null;
}

export interface OcrDocumentListResponse {
  documents: OcrDocumentResponse[];
  total: number;
}
