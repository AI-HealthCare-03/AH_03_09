from ai_worker.schemas.guide import GuideJobPayload


async def process_guide_task(payload: GuideJobPayload) -> None:
    """
    TODO: 실제 Worker 구현 시 아래 순서로 처리
    1. OpenAI API 호출 (guide_types별 프롬프트 분기)
    2. 응답 파싱 → GuideResponse 구조로 변환
    3. DB 저장 (Guide 모델)
    4. job 상태 DONE 업데이트
    """
    raise NotImplementedError("Worker 구현 전입니다. mock 서비스 참조: app/services/guides.py")
