import { useEffect, useRef, useState } from "react";

import { useLocation } from "react-router-dom";

import {
  generateGuide,
  getGuide,
  getGuideContext,
  getGuideStatus,
  submitGuideFeedback,
  type GuideContextResponse,
  type GuideResponse,
} from "@/api/guides";
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

export default function HealthGuide() {
  const [loading, setLoading] = useState(false);
  const [contextLoading, setContextLoading] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const [status, setStatus] = useState("");
  const [contextStatus, setContextStatus] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");

  const [guide, setGuide] = useState<GuideResponse | null>(null);
  const [guideContext, setGuideContext] =
    useState<GuideContextResponse | null>(null);
  const [guideId, setGuideId] = useState("");

  const [ratingComprehension, setRatingComprehension] = useState(5);
  const [ratingUsefulness, setRatingUsefulness] = useState(5);
  const [ratingSafety, setRatingSafety] = useState(5);
  const [comment, setComment] = useState("");
  const location = useLocation();
  const initialJobIdRef = useRef(
    (location.state as { guide_job_id?: string } | null)?.guide_job_id ?? null,
  );

  useEffect(() => {
    const jobId = initialJobIdRef.current;
    if (!jobId) return;

    let cancelled = false;

    async function pollFromOcr(id: string) {
      setLoading(true);
      setStatus("OCR 결과를 바탕으로 가이드 생성 중...");

      while (!cancelled) {
        await new Promise((r) => setTimeout(r, 2000));
        try {
          const statusResult = await getGuideStatus(id);
          if (cancelled) break;
          setStatus(`현재 상태: ${statusResult.status}`);
          if (statusResult.status === "DONE" && statusResult.guide_id) {
            const guideResult = await getGuide(statusResult.guide_id);
            if (!cancelled) {
              setGuide(guideResult);
              setGuideId(statusResult.guide_id);
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
      if (!cancelled) setLoading(false);
    }

    pollFromOcr(jobId);
    return () => {
      cancelled = true;
    };
  }, []); // initialJobIdRef는 마운트 시 한 번만 읽음

  async function handleGenerate() {
    try {
      setLoading(true);
      setStatus("가이드 생성 요청 중...");
      setContextStatus("");
      setFeedbackStatus("");
      setFeedbackSubmitted(false);
      setGuide(null);
      setGuideContext(null);
      setGuideId("");

      const generateResult = await generateGuide({
        patient_id: "demo-patient-001",
        guide_types: ["MEDICATION", "LIFESTYLE", "DIET", "EXERCISE"],
        medication_names: ["타이레놀", "아모잘탄"],
      });

      const jobId = generateResult.job_id;
      let done = false;

      while (!done) {
        await new Promise((resolve) => setTimeout(resolve, 2000));

        const statusResult = await getGuideStatus(jobId);
        setStatus(`현재 상태: ${statusResult.status}`);

        if (statusResult.status === "DONE" && statusResult.guide_id) {
          const guideResult = await getGuide(statusResult.guide_id);

          setGuide(guideResult);
          setGuideId(statusResult.guide_id);
          setStatus("가이드 생성 완료");
          done = true;
        }

        if (statusResult.status === "FAILED") {
          setStatus("가이드 생성 실패");
          done = true;
        }
      }
    } catch (error) {
      console.error(error);
      setStatus("에러 발생");
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadContext() {
    if (!guideId) {
      setContextStatus("가이드 생성 후 컨텍스트를 조회할 수 있습니다.");
      return;
    }

    try {
      setContextLoading(true);
      setContextStatus("가이드 컨텍스트 조회 중...");

      const contextResult = await getGuideContext(guideId);

      setGuideContext(contextResult);
      setContextStatus("가이드 컨텍스트 조회 완료");
    } catch (error) {
      console.error(error);
      setContextStatus("가이드 컨텍스트 조회 중 에러가 발생했습니다.");
    } finally {
      setContextLoading(false);
    }
  }

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

      setFeedbackStatus("피드백이 제출되었습니다.");
      setFeedbackSubmitted(true);
    } catch (error) {
      console.error(error);
      setFeedbackStatus("피드백 제출 중 에러가 발생했습니다.");
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">건강 가이드</h1>

      <Card>
        <CardHeader>
          <CardTitle>맞춤 건강 가이드</CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            복약 정보를 바탕으로 맞춤 건강 가이드를 생성합니다.
          </p>

          <Button type="button" onClick={handleGenerate} disabled={loading}>
            {loading ? "생성 중..." : "가이드 생성"}
          </Button>

          {status && <p className="text-sm text-muted-foreground">{status}</p>}

          {guide?.medication_guide && (
            <div className="space-y-4">
              {guide.medication_guide.medications.map((medication) => (
                <Card key={medication.name}>
                  <CardHeader>
                    <CardTitle className="text-lg">{medication.name}</CardTitle>
                  </CardHeader>

                  <CardContent className="space-y-2 text-sm">
                    {medication.action_icons?.length > 0 && (
  <>
    <p className="text-sm font-medium text-blue-700 mb-1">
      핵심 주의사항
    </p>

    <div className="flex flex-wrap gap-2 mb-2">
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

    <div className="flex flex-wrap gap-2 mb-2">
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
{medication.easy_summary?.length > 0 && (
  <div className="rounded-lg bg-slate-50 p-3 mb-2">
    <p className="font-medium mb-2">쉬운 설명</p>

    <ul className="list-disc pl-5 text-sm space-y-1">
      {medication.easy_summary.map((summary) => (
        <li key={summary}>{summary}</li>
      ))}
    </ul>
  </div>
)}
  {medication.match_status === "EXACT_DB_MATCH" && (
  <details className="mt-4 rounded-lg border p-3">
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

                    {medication.disclaimer && (
                      <div className="rounded-md bg-amber-50 p-3 text-amber-800">
                        {medication.disclaimer}
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
          {guideId && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">챗봇 연동용 가이드 컨텍스트</CardTitle>
              </CardHeader>

              <CardContent className="space-y-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleLoadContext}
                  disabled={contextLoading}
                >
                  {contextLoading ? "조회 중..." : "컨텍스트 조회"}
                </Button>

                {contextStatus && (
                  <p className="text-sm text-muted-foreground">{contextStatus}</p>
                )}

                {guideContext && (
                  <div className="space-y-3 rounded-md border p-4 text-sm">
                    

                    <div>
                      <p className="font-medium">약물</p>
                      {guideContext.medications.length > 0 ? (
                        <ul className="list-disc pl-5">
                          {guideContext.medications.map((medication) => (
                            <li key={medication}>{medication}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-muted-foreground">약물 정보가 없습니다.</p>
                      )}
                    </div>

                    <div>
                      <p className="font-medium">질병 코드</p>
                      {guideContext.disease_codes.length > 0 ? (
                        <ul className="list-disc pl-5">
                          {guideContext.disease_codes.map((code) => (
                            <li key={code}>{code}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-muted-foreground">
                          질병 코드 정보가 없습니다.
                        </p>
                      )}
                    </div>

                    <div>
                      <p className="font-medium">핵심 지침</p>
                      {guideContext.key_instructions.length > 0 ? (
                        <ul className="list-disc pl-5">
                          {guideContext.key_instructions.map((instruction) => (
                            <li key={instruction}>{instruction}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-muted-foreground">
                          핵심 지침 정보가 없습니다.
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
{(guide?.lifestyle_guide?.tips?.length ?? 0) > 0 && (
  <Card>
    <CardHeader>
      <CardTitle className="text-lg">
        생활 관리 안내
      </CardTitle>
    </CardHeader>

    <CardContent>
      <ul className="list-disc space-y-2 pl-5 text-sm">
        {guide?.lifestyle_guide?.tips?.map((tip: string) => (
          <li key={tip}>{tip}</li>
        ))}
      </ul>
      {guide?.diet_guide && (
  <div className="mt-6">
    <h3 className="mb-2 font-medium">식사 안내</h3>

    <div className="space-y-2 text-sm">
      <div>
        <p className="font-medium">권장 음식</p>
        <ul className="list-disc pl-5">
          {guide.diet_guide.recommended.map((item: string) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div>
        <p className="font-medium">주의 음식</p>
        <ul className="list-disc pl-5">
          {guide.diet_guide.forbidden.map((item: string) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div>
        <p className="font-medium">수분 섭취</p>
        <p>{guide.diet_guide.hydration}</p>
      </div>
    </div>
  </div>
)}

{guide?.exercise_guide && (
  <div className="mt-6">
    <h3 className="mb-2 font-medium">운동 안내</h3>

    <div className="space-y-2 text-sm">
      <p>
        <span className="font-medium">운동 강도:</span>{" "}
        {guide.exercise_guide.intensity}
      </p>

      <p>
        <span className="font-medium">운동 빈도:</span>{" "}
        {guide.exercise_guide.frequency}
      </p>

      <p>
        <span className="font-medium">운동 시간:</span>{" "}
        {guide.exercise_guide.duration}
      </p>

      <div>
        <p className="font-medium">주의사항</p>
        <ul className="list-disc pl-5">
          {guide.exercise_guide.cautions.map((item: string) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </div>
  </div>
)}
    </CardContent>
  </Card>
)}

          {guideId && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">가이드 피드백</CardTitle>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-3">
                  <label className="space-y-1 text-sm">
                    <span className="font-medium">이해도</span>
                    <input
                      type="number"
                      min={1}
                      max={5}
                      value={ratingComprehension}
                      onChange={(event) =>
                        setRatingComprehension(Number(event.target.value))
                      }
                      className="w-full rounded-md border px-3 py-2"
                      disabled={feedbackSubmitted}
                    />
                  </label>

                  <label className="space-y-1 text-sm">
                    <span className="font-medium">유용성</span>
                    <input
                      type="number"
                      min={1}
                      max={5}
                      value={ratingUsefulness}
                      onChange={(event) =>
                        setRatingUsefulness(Number(event.target.value))
                      }
                      className="w-full rounded-md border px-3 py-2"
                      disabled={feedbackSubmitted}
                    />
                  </label>

                  <label className="space-y-1 text-sm">
                    <span className="font-medium">안전성</span>
                    <input
                      type="number"
                      min={1}
                      max={5}
                      value={ratingSafety}
                      onChange={(event) =>
                        setRatingSafety(Number(event.target.value))
                      }
                      className="w-full rounded-md border px-3 py-2"
                      disabled={feedbackSubmitted}
                    />
                  </label>
                </div>

                <label className="space-y-1 text-sm">
                  <span className="font-medium">의견</span>
                  <textarea
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="가이드에 대한 의견을 입력해주세요."
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
                      : "피드백 제출"}
                </Button>

                {feedbackStatus && (
                  <p className="text-sm text-muted-foreground">
                    {feedbackStatus}
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>
    </div>
  );
}