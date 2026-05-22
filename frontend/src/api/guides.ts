import { request } from "@/lib/api";

export type GuideType = "MEDICATION" | "LIFESTYLE" | "DIET" | "EXERCISE";
export type JobStatus = "PENDING" | "PROCESSING" | "DONE" | "FAILED";

export type GenerateGuideRequest = {
  patient_id: string;
  guide_types: GuideType[];
  medication_names: string[];
};

export type GenerateGuideResponse = {
  job_id: string;
  estimated_seconds: number;
};

export type GuideStatusResponse = {
  job_id: string;
  status: JobStatus;
  guide_id: string | null;
};

export type MedicationItem = {
  name: string;
  dosage: string;
  timing: string;
  before_after_meal: string;
  side_effects: string[];
  cautions: string[];
  missed_dose: string;
  storage: string;
  match_status: string | null;
  disclaimer: string | null;
  source_name: string | null;
};

export type GuideResponse = {
  guide_id: string;
  guide_types: GuideType[];
  created_at: string;
  medication_guide: {
    medications: MedicationItem[];
  } | null;
  schedule_table:
    | {
        time: string;
        medications: string[];
      }[]
    | null;
};

export function generateGuide(body: GenerateGuideRequest) {
  return request<GenerateGuideResponse>("/guides/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getGuideStatus(jobId: string) {
  return request<GuideStatusResponse>(`/guides/status/${jobId}`);
}

export function getGuide(guideId: string) {
  return request<GuideResponse>(`/guides/${guideId}`);
}

export type GuideFeedbackRequest = {
  rating_comprehension: number;
  rating_usefulness: number;
  rating_safety: number;
  comment: string;
};

export function submitGuideFeedback(
  guideId: string,
  payload: GuideFeedbackRequest,
) {
  return request(`/guides/${guideId}/feedback`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface GuideContextResponse {
  guide_id: string;
  medications: string[];
  disease_codes: string[];
  key_instructions: string[];
}

export function getGuideContext(guideId: string) {
  return request<GuideContextResponse>(`/guides/${guideId}/context`);
}