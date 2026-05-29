"""REQ-OCR-030: 동일 입력 5회 반복 일관성 검증 스크립트.

같은 이미지를 1회 업로드 + 4회 reanalyze하여 총 5회 OCR을 수행하고,
신뢰도 점수(confidence_score)의 표준편차가 ±2% 이내인지 검증합니다.

사전 조건:
  - FastAPI 서버가 로컬에서 실행 중이어야 합니다 (기본: http://localhost:8000)
  - 유효한 JWT Bearer 토큰이 필요합니다 (Kakao 로그인 후 발급)

Usage:
    BEARER_TOKEN=<your_jwt_token> uv run python scripts/verify_ocr_consistency.py <image_path>

    # 서버 주소 변경 시
    BASE_URL=http://localhost:8000 BEARER_TOKEN=<token> uv run python scripts/verify_ocr_consistency.py <image_path>

    # 재시도 횟수 조정 (기본 5회, 최대 4회 reanalyze + 1회 업로드)
    RUNS=5 BEARER_TOKEN=<token> uv run python scripts/verify_ocr_consistency.py <image_path>
"""

import asyncio
import mimetypes
import os
import statistics
import sys
from pathlib import Path

import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
API_PREFIX = "/api/v1/ocr"
BEARER_TOKEN = os.getenv("BEARER_TOKEN", "")
RUNS = int(os.getenv("RUNS", "5"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))
POLL_TIMEOUT = float(os.getenv("POLL_TIMEOUT", "120"))


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {BEARER_TOKEN}"}


async def _poll_until_done(client: httpx.AsyncClient, job_id: str) -> dict:
    """DONE 또는 FAILED 상태가 될 때까지 폴링합니다."""
    elapsed = 0.0
    while elapsed < POLL_TIMEOUT:
        resp = client.get(f"{BASE_URL}{API_PREFIX}/jobs/{job_id}/status", headers=_headers())
        resp = await resp
        resp.raise_for_status()
        data = resp.json()
        st = data.get("status")
        print(f"  └ 상태: {st} ({elapsed:.0f}s)", flush=True)
        if st in ("DONE", "FAILED"):
            return data
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    raise TimeoutError(f"OCR 처리가 {POLL_TIMEOUT}초 내에 완료되지 않았습니다.")


async def _get_confidence(client: httpx.AsyncClient, record_id: int) -> float | None:
    """record 상세에서 confidence_score를 조회합니다."""
    resp = await client.get(f"{BASE_URL}{API_PREFIX}/records/{record_id}", headers=_headers())
    resp.raise_for_status()
    result = resp.json().get("result") or {}
    return result.get("confidence_score")


async def _upload_run(
    client: httpx.AsyncClient, image_path: Path, mime_type: str, run_no: int, padding: int
) -> tuple[int, float] | None:
    """파일을 업로드하고 confidence_score를 반환합니다. (record_id, confidence) / 실패 시 None.

    padding: 같은 파일을 여러 번 업로드하기 위해 null byte를 추가해 SHA-256 hash를 다르게 만듦.
    JPEG는 EOI(FF D9) 이후 바이트를 무시하므로 OCR 결과에 영향 없음.
    """
    print(f"[{run_no}/{RUNS}] 업로드 중...")
    with image_path.open("rb") as f:
        content = f.read() + b"\x00" * padding

    upload_resp = await client.post(
        f"{BASE_URL}{API_PREFIX}/upload",
        headers=_headers(),
        files=[("files", (image_path.name, content, mime_type))],
    )
    if upload_resp.status_code == 409:
        err = upload_resp.json()
        existing_id = (err.get("detail") or {}).get("existing_record_id")
        print(f"  └ [건너뜀] 중복 파일 (record_id={existing_id})")
        return None
    upload_resp.raise_for_status()

    uploaded = upload_resp.json().get("uploaded_files", [{}])[0]
    record_id: int = uploaded["record_id"]
    job_id: str = str(uploaded["job_id"])
    print(f"  └ record_id={record_id}, job_id={job_id}")

    status_data = await _poll_until_done(client, job_id)
    if status_data["status"] == "FAILED":
        print(f"  └ [실패] {run_no}회차 OCR 처리 실패.")
        return None

    score = await _get_confidence(client, record_id)
    confidence = score if score is not None else 0.0
    print(f"  └ confidence_score: {score}\n")
    return record_id, confidence


def _print_report(scores: list[float], record_id: int) -> None:
    sep = "=" * 60
    print(f"\n{sep}")
    print("결과 분석")
    print(sep)
    print(f"  실행 완료: {len(scores)}회")
    for i, s in enumerate(scores, 1):
        print(f"  {i}회차 confidence: {s:.4f} ({s * 100:.2f}%)")

    if len(scores) < 2:
        print("\n[경고] 비교할 데이터가 부족합니다 (최소 2회 이상 필요).")
        return

    mean_score = statistics.mean(scores)
    stdev_score = statistics.stdev(scores)
    min_score = min(scores)
    max_score = max(scores)
    range_score = max_score - min_score

    print(f"\n  평균 신뢰도: {mean_score:.4f} ({mean_score * 100:.2f}%)")
    print(f"  표준편차:   {stdev_score:.4f} ({stdev_score * 100:.4f}%p)")
    print(f"  최솟값:     {min_score:.4f}")
    print(f"  최댓값:     {max_score:.4f}")
    print(f"  범위(max-min): {range_score:.4f} ({range_score * 100:.2f}%p)")

    threshold = 0.02  # REQ-OCR-030 기준: ±2%
    passed = stdev_score <= threshold

    print(f"\n{sep}")
    if passed:
        print(f"합격: 표준편차 {stdev_score * 100:.4f}%p <= 기준 +-{threshold * 100:.0f}%p")
    else:
        print(f"불합격: 표준편차 {stdev_score * 100:.4f}%p > 기준 +-{threshold * 100:.0f}%p")
        print("   -> 동일 입력에 대한 OCR 결과 일관성이 낮습니다.")
    print(f"  record_id={record_id}")
    print(f"{sep}\n")


async def run_consistency_check(image_path: Path) -> None:
    if not image_path.exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {image_path}")
        sys.exit(1)
    if not BEARER_TOKEN:
        print("[오류] BEARER_TOKEN 환경변수를 설정해주세요.")
        sys.exit(1)
    if RUNS < 1 or RUNS > 5:
        print("[오류] RUNS는 1~5 사이여야 합니다.")
        sys.exit(1)

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    sep = "=" * 60
    print(f"\n{sep}")
    print("REQ-OCR-030 일관성 검증")
    print(f"  파일: {image_path.name}  ({mime_type})")
    print(f"  실행 횟수: {RUNS}회  (1회 업로드 + {RUNS - 1}회 reanalyze)")
    print(f"  서버: {BASE_URL}")
    print(f"{sep}\n")

    scores: list[float] = []
    record_ids: list[int] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for run_no in range(1, RUNS + 1):
            result = await _upload_run(client, image_path, mime_type, run_no, padding=run_no - 1)
            if result is None:
                continue
            rid, confidence = result
            record_ids.append(rid)
            scores.append(confidence)

    if not scores:
        print("[오류] 성공한 OCR 실행이 없습니다.")
        sys.exit(1)

    _print_report(scores, record_ids[0])


def _main() -> None:
    if len(sys.argv) < 2:
        # RECORD_ID 환경변수로 기존 문서 재사용 모드 안내
        record_id_env = os.getenv("RECORD_ID")
        if record_id_env:
            print("RECORD_ID 모드는 아직 지원되지 않습니다. 이미지 경로를 인자로 전달하세요.")
        else:
            print(__doc__)
        sys.exit(1)

    image_path = Path(sys.argv[1])
    asyncio.run(run_consistency_check(image_path))


if __name__ == "__main__":
    _main()
