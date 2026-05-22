import { useState } from "react";

import {
  generateGuide,
  getGuide,
  getGuideStatus,
  submitGuideFeedback,
  type GuideResponse,
} from "@/api/guides";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HealthGuide() {
  const [loading, setLoading] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [status, setStatus] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [guide, setGuide] = useState<GuideResponse | null>(null);
  const [guideId, setGuideId] = useState("");

  const [ratingComprehension, setRatingComprehension] = useState(5);
  const [ratingUsefulness, setRatingUsefulness] = useState(5);
  const [ratingSafety, setRatingSafety] = useState(5);
  const [comment, setComment] = useState("");

  async function handleGenerate() {
    try {
      setLoading(true);
      setStatus("가이드 생성 요청 중...");
      setFeedbackStatus("");
      setFeedbackSubmitted(false);
      setGuide(null);
      setGuideId("");

      const generateResult = await generateGuide({
        patient_id: "demo-patient-001",
        guide_types: ["MEDICATION"],
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