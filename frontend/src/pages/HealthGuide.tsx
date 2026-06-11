import { useEffect, useRef, useState } from "react";

import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useChatStore } from "@/store/chatStore";

import {
  getGuide,
  getGuideContext,
  getGuideFeedbackStatus,
  getGuideStatus,
  submitGuideFeedback,
  type GuideContextResponse,
  type GuideResponse,
} from "@/api/guides";
import {
  AlertTriangle,
  Dumbbell,
  Droplets,
  MessageCircle,
  Utensils,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const iconMap: Record<string, string> = {
  alcohol: "🍺",
  pregnancy: "🤰",
  grapefruit: "🍊",
  drowsiness: "😴",
  driving: "🚗",
  headache: "🤕",
  liver: "🩺",
  kidney: "💧",
  child_storage: "🧒",
  interval: "⏰",
  max_dose: "🚫",
  no_water: "👅",
  weight: "⚖️",
};

function StarRating({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (v: number) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={disabled}
          onClick={() => onChange(star)}
          className={`text-2xl leading-none disabled:cursor-not-allowed ${
            star <= value ? "text-amber-400" : "text-gray-300"
          }`}
        >
          {star <= value ? "★" : "☆"}
        </button>
      ))}
    </div>
  );
}

export default function HealthGuide() {
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const [status, setStatus] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");

  const [guide, setGuide] = useState<GuideResponse | null>(null);
  const [guideContext, setGuideContext] = useState<GuideContextResponse | null>(null);
  const [guideId, setGuideId] = useState("");
  const navigate = useNavigate();
  const setStoreGuideId = useChatStore((s) => s.setGuideId);
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);

  const [ratingComprehension, setRatingComprehension] = useState(5);
  const [ratingUsefulness, setRatingUsefulness] = useState(5);
  const [ratingSafety] = useState(5);
  const [comment, setComment] = useState("");
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const initialJobIdRef = useRef(
    searchParams.get("job_id") ??
    (location.state as { guide_job_id?: string } | null)?.guide_job_id ??
    null,
  );

  useEffect(() => {
    const jobId = initialJobIdRef.current;
    if (!jobId) return;

    let cancelled = false;

    async function pollFromOcr(id: string) {
      setStatus("loading");

      while (!cancelled) {
        await new Promise((r) => setTimeout(r, 2000));
        try {
          const statusResult = await getGuideStatus(id);
          if (cancelled) break;
          setStatus("loading"); // PENDING/PROCESSING 모두 로딩 상태로 통일
          if (statusResult.status === "DONE" && statusResult.guide_id) {
            const guideResult = await getGuide(statusResult.guide_id);
            if (!cancelled) {
              setGuide(guideResult);
              setGuideId(statusResult.guide_id);
              setStoreGuideId(statusResult.guide_id);
              setStatus("가이드 생성 완료");
            }
            break;
          }
          if (statusResult.status === "FAILED") {
            if (!cancelled) setStatus("가이드 생성 실패");
            break;
          }
        } catch {
          if (!cancelled) setStatus("에러 발생");
          break;
        }
      }
    }

    pollFromOcr(jobId);
    return () => {
      cancelled = true;
    };
  }, []); // initialJobIdRef는 마운트 시 한 번만 읽음

  // guideId 설정 후 서버의 피드백 제출 여부를 동기화한다.
  useEffect(() => {
    if (!guideId) return;
    (async () => {
      try {
        const result = await getGuideFeedbackStatus(guideId);
        setFeedbackSubmitted(result.is_submitted);
      } catch {
        // 조회 실패 시 feedbackSubmitted = false 유지 (기존 동작)
      }
    })();
  }, [guideId]);

  // guideId 설정 후 생성 근거 데이터를 조회한다. 에러 시 조용히 무시.
  useEffect(() => {
    if (!guideId) return;
    getGuideContext(guideId)
      .then(setGuideContext)
      .catch(() => {});
  }, [guideId]);

  async function handleSubmitFeedback() {
    if (!guideId) {
      setFeedbackStatus("가이드 생성 후 피드백을 제출할 수 있습니다.");
      return;
    }

    try {
      setFeedbackSubmitting(true);
      setFeedbackStatus("피드백 제출 중...");

      await submitGuideFeedback(guideId, {
        rating_comprehension: ratingComprehension,
        rating_usefulness: ratingUsefulness,
        rating_safety: ratingSafety,
        comment,
      });

      setFeedbackStatus("소중한 의견 감사합니다.\n더 나은 건강 가이드 제공에 반영하겠습니다.");
      setFeedbackSubmitted(true);
    } catch (error) {
      console.error(error);
      setFeedbackStatus("피드백 제출 중 에러가 발생했습니다.");
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  return (
    <div className="space-y-3">
      {/* 페이지 타이틀 + 생성 완료 뱃지 */}
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold">건강 가이드</h1>
        {guide && (
          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
            생성 완료
          </span>
        )}
      </div>

      <Card>
        <CardContent className="space-y-3 px-4 pb-4 pt-4">
          {/* 가이드 미로드 시에만 설명·상태 표시 */}
          {!guide && !status && (
            <p className="text-sm text-muted-foreground">
              복약 정보를 바탕으로 맞춤 건강 가이드를 생성합니다.
            </p>
          )}
          {!guide && status === "loading" && (
            <div className="space-y-1 py-1 text-sm">
              <p className="font-medium text-gray-800">건강 가이드 생성 중</p>
              <p className="text-muted-foreground">
                올려주신 처방전/약정보를 읽고 복약·식사·운동 가이드를 생성하고 있습니다.
              </p>
              <p className="text-muted-foreground">잠시만 기다려 주세요.</p>
            </div>
          )}
          {!guide && status && status !== "loading" && (
            <p className="text-sm text-muted-foreground">{status}</p>
          )}

          {/* 생성 근거 및 필독 안내 — 기본 접힘, 발표 시 펼쳐서 설명 */}
          {guide && (
            <details className="rounded-md border border-gray-200 bg-gray-50 text-xs">
              <summary className="cursor-pointer px-3 py-2 font-medium text-gray-600">
                가이드 생성 근거 및 필독 안내
              </summary>
              <div className="space-y-3 border-t border-gray-200 px-3 pb-3 pt-2 text-gray-600">
                {(guide.medication_guide?.medications?.length ?? 0) > 0 && (
                  <div>
                    <p className="mb-1 font-medium text-gray-700">OCR 인식 약물</p>
                    <ul className="list-disc space-y-0.5 pl-4">
                      {guide.medication_guide!.medications.map((m) => (
                        <li key={m.name}>{m.name}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {(guideContext?.disease_codes?.length ?? 0) > 0 && (
                  <div>
                    <p className="mb-1 font-medium text-gray-700">OCR 질병코드</p>
                    <ul className="list-disc space-y-0.5 pl-4">
                      {guideContext!.disease_codes.map((code, idx) => {
                        const name = guideContext!.disease_names?.[idx];
                        return (
                          <li key={code}>
                            {name ? `${code} (${name})` : code}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
                <div>
                  <p className="mb-1 font-medium text-gray-700">필독 안내</p>
                  <p className="leading-relaxed text-gray-500">
                    본 가이드는 업로드한 문서(처방전, 약봉투 등)를 바탕으로 AI가 생성한 참고용 안내입니다.
                    정확한 진단·치료 및 복약 방법은 담당 의료진의 안내를 우선적으로 따라주시기 바랍니다.
                  </p>
                </div>
              </div>
            </details>
          )}

          {guide?.medication_guide && (
            <div className="space-y-2">
              {guide.medication_guide.medications.map((medication) => (
                <Card key={medication.name} className="py-4 gap-4">
                  <CardHeader className="px-4 py-2">
                    <CardTitle className="text-base">{medication.name}</CardTitle>
                  </CardHeader>

                  <CardContent className="px-4 space-y-1 pt-0 text-sm">
                    {medication.action_icons?.length > 0 && (
  <>
    <p className="text-sm font-medium text-blue-700 mb-1">
      핵심 주의사항
    </p>

    <div className="flex flex-wrap gap-2 mb-1">
      {medication.action_icons.map((icon) => (
        <div
          key={icon.type}
          className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs"
        >
          <span className="mr-1">{iconMap[icon.type] ?? "💊"}</span>
          {icon.label}
        </div>
      ))}
    </div>
  </>
)}

  {medication.usage_icons?.length > 0 && (
  <>
    <p className="text-sm font-medium text-green-700 mb-1">
      핵심 복용법
    </p>

    <div className="flex flex-wrap gap-2 mb-1">
      {medication.usage_icons.map((icon) => (
        <div
          key={icon.type}
          className="rounded-full border border-green-200 bg-green-50 px-3 py-1 text-xs"
        >
          <span className="mr-1">{iconMap[icon.type] ?? "💊"}</span>
          {icon.label}
        </div>
      ))}
    </div>
  </>
)}
{medication.easy_summary?.length > 0 && medication.match_status !== "NOT_FOUND" && (
  <div className="rounded-lg bg-slate-50 p-2 mb-1">
    <p className="font-medium mb-1">쉬운 설명</p>

    <ul className="list-disc pl-5 text-sm space-y-1">
      {medication.easy_summary.map((summary) => (
        <li key={summary}>{summary}</li>
      ))}
    </ul>
  </div>
)}
  {medication.match_status === "EXACT_DB_MATCH" && (
  <details className="mt-2 rounded-lg border p-3">
    <summary className="cursor-pointer font-medium text-blue-700">
      전체 복약정보 보기
    </summary>

    <div className="mt-3 space-y-3">
      <p>용법: {medication.dosage}</p>

      <p>복용 시간: {medication.timing}</p>

      <p>식사 관계: {medication.before_after_meal}</p>

      <div>
        <p className="font-medium">주의사항</p>

        <ul className="list-disc pl-5">
          {medication.cautions.map((caution) => (
            <li key={caution}>{caution}</li>
          ))}
        </ul>
      </div>
    </div>
  </details>
)}

{medication.match_status === "WEB_REFERENCE" && (
  <details className="mt-2 rounded-lg border p-3">
    <summary className="cursor-pointer font-medium text-blue-700">
      제품허가정보 원문 일부 보기
    </summary>

    <div className="mt-3 space-y-3">
      <div className="rounded-md bg-amber-50 p-3 text-amber-800 text-xs">
        아래 내용은 제품허가정보 원문 일부입니다.
        전문 용어가 포함되어 있어 이해가 어려울 수 있습니다.
        복용 관련 판단이 필요한 경우 의료진 또는 약사와 상담하세요.
      </div>

      {medication.dosage && <p>용법: {medication.dosage}</p>}

      {medication.cautions.length > 0 && (
        <div>
          <p className="font-medium">주의사항</p>

          <ul className="list-disc pl-5">
            {medication.cautions.map((caution) => (
              <li key={caution}>{caution}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  </details>
)}

{medication.match_status === "NOT_FOUND" && (
  <div className="rounded-md bg-amber-50 p-3 text-amber-800 text-sm space-y-1">
    <p className="font-medium">약물 정보를 찾을 수 없습니다.</p>
    <p>OCR 인식 오류 또는 등록되지 않은 의약품일 수 있습니다.</p>
    <p>약봉투 또는 처방전을 다시 확인해주세요.</p>
    {medication.disclaimer && <p>{medication.disclaimer}</p>}
  </div>
)}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
{guide?.schedule_table && guide.schedule_table.length > 0 && (
  <Card>
    <CardHeader>
      <CardTitle className="text-lg">복약 스케줄 요약</CardTitle>
    </CardHeader>

    <CardContent>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b">
            <tr>
              <th className="pb-2 text-left font-medium">복용 시간</th>
              <th className="pb-2 text-left font-medium">복용 약물</th>
            </tr>
          </thead>

          <tbody>
            {guide.schedule_table.map((schedule) => (
              <tr key={schedule.time} className="border-b last:border-0">
                <td className="py-3 font-medium">{schedule.time}</td>
                <td className="py-3">
                  {schedule.medications.length > 0 ? (
                    <ul className="list-disc pl-5">
                      {schedule.medications.map((medication) => (
                        <li key={medication}>{medication}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-muted-foreground">
                      해당 시간 복용 약물이 없습니다.
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </CardContent>
  </Card>
)}
{(guide?.lifestyle_guide?.tips?.length ?? 0) > 0 && (
  <Card>
    <CardHeader className="pb-2">
      <CardTitle className="flex items-center gap-2 text-lg">
        생활 관리 안내
      </CardTitle>
    </CardHeader>

    <CardContent className="space-y-5">
      {/* 생활 관리 팁 */}
      <ul className="space-y-2 text-sm">
        {guide?.lifestyle_guide?.tips?.map((tip: string) => (
          <li key={tip} className="rounded-md bg-gray-50 px-3 py-2 text-gray-700">
            {tip}
          </li>
        ))}
      </ul>

      {/* 식사 안내 */}
      {guide?.diet_guide && (
        <div className="border-t border-gray-200 pt-4">
          <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-gray-800">
            <Utensils className="h-4 w-4 text-emerald-600" />
            식사 안내
          </h3>

          {/* 권장/주의 음식 — 모바일 1열, md 이상 2열 */}
          <div className="mb-3 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            <div className="rounded-md border border-green-200 bg-green-50 p-3">
              <p className="mb-2 font-semibold text-green-800">권장 음식</p>
              <ul className="space-y-1 text-green-700">
                {guide.diet_guide.recommended.map((item: string) => (
                  <li key={item} className="flex items-start gap-1">
                    <span className="mt-0.5 shrink-0 text-green-500">✓</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
              <p className="mb-2 font-semibold text-amber-800">주의 음식</p>
              <ul className="space-y-1 text-amber-700">
                {guide.diet_guide.forbidden.map((item: string) => (
                  <li key={item} className="flex items-start gap-1">
                    <span className="mt-0.5 shrink-0 text-amber-500">✕</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* 수분 섭취 */}
          <div className="flex items-center gap-2 rounded-md border border-blue-100 bg-blue-50 px-3 py-2 text-sm text-blue-700">
            <Droplets className="h-4 w-4 shrink-0 text-blue-400" />
            <span>{guide.diet_guide.hydration}</span>
          </div>
        </div>
      )}

      {/* 운동 안내 */}
      {guide?.exercise_guide && (
        <div className="border-t border-gray-200 pt-4">
          <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-gray-800">
            <Dumbbell className="h-4 w-4 text-violet-600" />
            운동 안내
          </h3>

          <div className="mb-3 space-y-2 text-sm">
            <div className="flex items-center gap-3 rounded-md bg-gray-50 px-3 py-2">
              <span className="w-16 shrink-0 font-medium text-gray-600">운동 강도</span>
              <span className="text-gray-800">{guide.exercise_guide.intensity}</span>
            </div>
            <div className="flex items-center gap-3 rounded-md bg-gray-50 px-3 py-2">
              <span className="w-16 shrink-0 font-medium text-gray-600">운동 빈도</span>
              <span className="text-gray-800">{guide.exercise_guide.frequency}</span>
            </div>
            <div className="flex items-center gap-3 rounded-md bg-gray-50 px-3 py-2">
              <span className="w-16 shrink-0 font-medium text-gray-600">운동 시간</span>
              <span className="text-gray-800">{guide.exercise_guide.duration}</span>
            </div>
          </div>

          {/* 주의사항 */}
          {guide.exercise_guide.cautions.length > 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
              <p className="mb-2 flex items-center gap-1 font-semibold text-amber-800">
                <AlertTriangle className="h-4 w-4" />
                주의사항
              </p>
              <ul className="space-y-1 text-amber-700">
                {guide.exercise_guide.cautions.map((item: string) => (
                  <li key={item} className="flex items-start gap-1">
                    <span className="mt-0.5 shrink-0">·</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </CardContent>
  </Card>
)}

          {guideId && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">읽어보신 가이드는 어땠나요?</CardTitle>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-1 text-sm">
                    <p className="font-medium">이해하기 쉬웠나요?</p>
                    <StarRating
                      value={ratingComprehension}
                      onChange={setRatingComprehension}
                      disabled={feedbackSubmitted}
                    />
                  </div>

                  <div className="space-y-1 text-sm">
                    <p className="font-medium">도움이 되었나요?</p>
                    <StarRating
                      value={ratingUsefulness}
                      onChange={setRatingUsefulness}
                      disabled={feedbackSubmitted}
                    />
                  </div>
                </div>

                <label className="space-y-1 text-sm">
                  <span className="font-medium">추가 의견 (선택)</span>
                  <textarea
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="더 나은 가이드 제공을 위해 의견을 남겨주세요."
                    className="min-h-24 w-full rounded-md border px-3 py-2"
                    disabled={feedbackSubmitted}
                  />
                </label>

                <Button
                  type="button"
                  onClick={handleSubmitFeedback}
                  disabled={feedbackSubmitting || feedbackSubmitted}
                >
                  {feedbackSubmitting
                    ? "제출 중..."
                    : feedbackSubmitted
                      ? "피드백 제출 완료"
                      : "의견 보내기"}
                </Button>

                {feedbackStatus && (
                  <p className="text-sm text-muted-foreground">
                    {feedbackStatus}
                  </p>
                )}
              </CardContent>
            </Card>
          )}
          {guideId && (
            <div className="rounded-lg border border-blue-100 bg-blue-50 p-5">
              <p className="mb-1 text-sm font-medium text-blue-800">
                가이드를 읽으신 후 더 궁금하신 점이 있으신가요?
              </p>
              <p className="mb-4 text-xs text-blue-700">
                복약 방법, 질병코드, 생활관리 안내 등 추가 질문은 챗봇에서 상담하실 수 있습니다.
              </p>
              <Button
                type="button"
                className="w-full sm:w-auto"
                onClick={() => {
                  setStoreGuideId(guideId);
                  setCurrentSessionId(null);
                  navigate("/chat");
                }}
              >
                <MessageCircle className="mr-2 h-4 w-4" />
                챗봇에서 상담하기
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
