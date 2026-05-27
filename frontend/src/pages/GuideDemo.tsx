import { useState } from "react";

import {
  generateGuide,
  getGuide,
  getGuideStatus,
  type GuideResponse,
} from "@/api/guides";

export default function GuideDemo() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [guide, setGuide] = useState<GuideResponse | null>(null);

  async function handleGenerate() {
    try {
      setLoading(true);
      setStatus("가이드 생성 요청 중...");
      setGuide(null);

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

  return (
    <main className="min-h-dvh bg-slate-50 p-8 text-slate-900">
      <div className="mx-auto max-w-3xl rounded-2xl bg-white p-6 shadow">
        <h1 className="mb-4 text-2xl font-bold">복약 가이드 데모</h1>

        <button
          type="button"
          onClick={handleGenerate}
          disabled={loading}
          className="rounded-lg bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? "생성 중..." : "가이드 생성"}
        </button>

        <p className="mt-4 text-sm text-slate-600">{status}</p>

        {guide?.medication_guide && (
          <div className="mt-8 space-y-4">
            {guide.medication_guide.medications.map((medication) => (
              <div
                key={medication.name}
                className="rounded-xl border border-slate-200 p-4"
              >
                <h2 className="text-lg font-semibold">
                  {medication.name}
                </h2>

                <div className="mt-2 space-y-1 text-sm">
                  <p>용법: {medication.dosage}</p>
                  <p>복용 시간: {medication.timing}</p>
                  <p>식사 관계: {medication.before_after_meal}</p>

                  <p className="mt-2 font-medium">주의사항</p>
                  <ul className="list-disc pl-5">
                    {medication.cautions.map((caution) => (
                      <li key={caution}>{caution}</li>
                    ))}
                  </ul>

                  {medication.disclaimer && (
                    <div className="mt-3 rounded bg-amber-50 p-3 text-amber-800">
                      {medication.disclaimer}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
