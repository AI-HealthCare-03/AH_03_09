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
  action_icons: {
  type: string;
  label: string;
}[];
  usage_icons: {
  type: string;
  label: string;
}[];
  easy_summary: string[];
  match_status: string | null;
  disclaimer: string | null;
  source_name: string | null;
};

export type MedicationGuide = {
  medications: MedicationItem[];
};

export type ScheduleEntry = {
  time: string;
  medications: string[];
};

export type LifestyleGuide = {
  tips: string[];
};

export type DietGuide = {
  forbidden: string[];
  recommended: string[];
  hydration: string;
};

export type ExerciseGuide = {
  intensity: string;
  frequency: string;
  duration: string;
  cautions: string[];
};

export type GenerationResult = {
  guide_type: GuideType;
  status: string;
  skip_reason?: string | null;
};

export type GuideResponse = {
  guide_id: string;
  guide_types: GuideType[];
  created_at: string;
  medication_guide: MedicationGuide | null;
  schedule_table: ScheduleEntry[] | null;
  lifestyle_guide: LifestyleGuide | null;
  diet_guide: DietGuide | null;
  exercise_guide: ExerciseGuide | null;
  generation_results?: GenerationResult[];
};

export type GuideListItem = {
  guide_id: string;
  created_at: string;
  guide_types: GuideType[];
  medication_names: string[];
};

export type GuideListResponse = {
  items: GuideListItem[];
  total: number;
};

export function getGuideList() {
  return request<GuideListResponse>("/guides");
}

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

export type FeedbackStatusResponse = {
  is_submitted: boolean;
  rating_comprehension: number | null;
  rating_usefulness: number | null;
  comment: string | null;
};

export function getGuideFeedbackStatus(guideId: string) {
  return request<FeedbackStatusResponse>(`/guides/${guideId}/feedback/status`);
}

export type GuideContextResponse = {
  guide_id: string;
  medications: string[];
  disease_codes: string[];
  disease_names?: string[];
  key_instructions: string[];
};

export function getGuideContext(guideId: string) {
  return request<GuideContextResponse>(`/guides/${guideId}/context`);
}
