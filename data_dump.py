"""
식약처 의약품개요정보(DrbEasyDrugInfoService) 전체 누적 CSV 추출 스크립트

사용법:
    python data_dump.py

인증키 교체:
    공공데이터포털(data.go.kr) → 마이페이지 → 인증키 발급/관리에서
    '인코딩된 인증키'를 복사하여 SERVICE_KEY에 붙여넣기.
"""

import time

import pandas as pd
import requests

# ── 설정 ──────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────


def fetch_page(page_no: int) -> tuple[list[dict], int]:
    """단일 페이지 호출. (items, totalCount) 반환."""
    # 인증키는 URL에 직접 삽입 (requests 자동 인코딩 방지)
    request_url = f"{BASE_URL}?serviceKey={SERVICE_KEY}"
    params = {
        "type": "json",
        "numOfRows": PAGE_SIZE,
        "pageNo": page_no,
    }
    resp = requests.get(request_url, params=params, timeout=15)
    resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError as e:
        raise ValueError(f"JSON 파싱 실패 (page {page_no}): {e}\n응답 내용: {resp.text[:500]}") from e
    # 공공데이터포털 응답 구조: {response: {body: ...}} 또는 {body: ...}
    body = data.get("response", data).get("body", {})

    total_count: int = int(body.get("totalCount", 0))
    raw_items = body.get("items", {})

    # items가 비어있으면 빈 리스트
    if not raw_items:
        return [], total_count

    # 응답 구조 두 가지 처리:
    #   (A) items가 직접 list → 그대로 사용
    #   (B) items가 {"item": [...]} dict → item 키 추출
    if isinstance(raw_items, list):
        return raw_items, total_count

    item = raw_items.get("item", [])
    if isinstance(item, dict):
        item = [item]

    return item, total_count


def main() -> None:
    all_items: list[dict] = []
    page_no = 1
    total_count = 0

    print("=" * 50)
    print("식약처 의약품개요정보 전체 수집 시작")
    print("=" * 50)

    while True:
        print(f"  페이지 {page_no} 수집 중...", end=" ", flush=True)

        try:
            items, total_count = fetch_page(page_no)
        except requests.exceptions.HTTPError as e:
            print(f"\n[오류] HTTP {e.response.status_code}: {e}")
            if e.response.status_code == 401:
                print(
                    "\n⚠️  인증 실패 (401 Unauthorized)\n"
                    "  → data.go.kr 마이페이지에서 '인코딩된 인증키'를 복사하여\n"
                    "    data_dump.py 상단의 SERVICE_KEY에 붙여넣으세요.\n"
                    "  → '디코딩된 인증키'(일반 인증키)는 requests 자동 인코딩과\n"
                    "    충돌하여 401이 발생할 수 있습니다."
                )
            break
        except requests.exceptions.RequestException as e:
            print(f"\n[오류] 네트워크 오류: {e}")
            break
        except ValueError as e:
            print(f"\n[오류] {e}")
            break

        if not items:
            print("데이터 없음 → 수집 종료")
            break

        all_items.extend(items)
        print(f"{len(items)}건 수집 (누적: {len(all_items):,} / 전체: {total_count:,})")

        if len(all_items) >= total_count:
            print("  전체 데이터 수집 완료")
            break

        page_no += 1
        time.sleep(REQUEST_DELAY)

    if not all_items:
        print("\n수집된 데이터가 없습니다. 인증키를 확인하세요.")
        return

    print(f"\nCSV 저장 중: {OUTPUT_FILE}")
    df = pd.DataFrame(all_items)
    df.to_csv(OUTPUT_FILE, encoding="utf-8-sig", index=False)

    print("=" * 50)
    print(f"✅ 저장 완료: {OUTPUT_FILE}")
    print(f"   총 {len(df):,}행 × {len(df.columns)}열")
    print(f"   컬럼: {', '.join(df.columns.tolist())}")
    print("=" * 50)


if __name__ == "__main__":
    main()
