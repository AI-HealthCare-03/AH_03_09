"""OCR 파싱 로직 단위 테스트.

대상:
  ai_worker.tasks.ocr_parser  — _clean_ocr_text, parse_medications_and_diseases
  ai_worker.tasks.ocr_task    — _strip_dosage, _normalize_medication_names
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_worker.tasks.ocr_parser import _clean_ocr_text, parse_medications_and_diseases
from ai_worker.tasks.ocr_task import _normalize_medication_names, _strip_dosage

# ── _clean_ocr_text ────────────────────────────────────────────────────────────


class TestCleanOcrText:
    def test_removes_receipt_noise(self):
        raw = "영수증\n타이레놀정 500mg\n약제비 3000원"
        result = _clean_ocr_text(raw)
        assert "타이레놀정" in result
        assert "영수증" not in result
        assert "약제비" not in result

    def test_removes_pharmacy_admin_lines(self):
        raw = "사업자번호 123-45-67890\n대표약사 홍길동\n타이레놀정 1정"
        result = _clean_ocr_text(raw)
        assert "타이레놀정" in result
        assert "사업자번호" not in result
        assert "대표약사" not in result

    def test_removes_drug_appearance_lines(self):
        raw = "분홍색 원형정제\n타이레놀정\n흰색 타원형"
        result = _clean_ocr_text(raw)
        assert "타이레놀정" in result
        assert "분홍색" not in result
        assert "흰색" not in result

    def test_removes_amount_only_lines(self):
        """금액만 있는 줄(숫자+쉼표)은 제거."""
        raw = "타이레놀정 1정\n12,500\n세티리진정 1정\n3,000"
        result = _clean_ocr_text(raw)
        assert "타이레놀정" in result
        assert "세티리진정" in result
        assert "12,500" not in result
        assert "3,000" not in result

    def test_removes_special_char_only_lines(self):
        raw = "타이레놀정\n■■■\n---\n암로디핀정"
        result = _clean_ocr_text(raw)
        assert "타이레놀정" in result
        assert "암로디핀정" in result
        assert "■■■" not in result

    def test_removes_test_tags(self):
        raw = "RECEIPT\nPATIENT-001\n타이레놀정\nRX-9999"
        result = _clean_ocr_text(raw)
        assert "타이레놀정" in result
        assert "RECEIPT" not in result
        assert "PATIENT-001" not in result

    def test_empty_input(self):
        assert _clean_ocr_text("") == ""

    def test_all_noise_returns_empty_lines(self):
        raw = "영수증\n약제비\n본인부담"
        result = _clean_ocr_text(raw)
        assert result.strip() == ""

    def test_preserves_medication_content(self):
        raw = "처방전\n암로디핀정5mg 1정 1일 1회 식후 30분 30일\n넥시움정 1정 1일 1회"
        result = _clean_ocr_text(raw)
        assert "암로디핀정5mg" in result
        assert "넥시움정" in result


# ── _strip_dosage ──────────────────────────────────────────────────────────────


class TestStripDosage:
    def test_strips_mg_unit(self):
        assert _strip_dosage("타이레놀정 500mg") == "타이레놀정"

    def test_strips_parenthetical_generic(self):
        assert _strip_dosage("타이레놀정 (아세트아미노펜)") == "타이레놀정"

    def test_strips_both_mg_and_generic(self):
        assert _strip_dosage("타이레놀정 500mg (아세트아미노펜)") == "타이레놀정"

    def test_strips_ml_unit(self):
        assert _strip_dosage("아목시실린시럽 250mL") == "아목시실린시럽"

    def test_strips_mcg_unit(self):
        assert _strip_dosage("레보티록신정 50mcg") == "레보티록신정"

    def test_strips_iu_unit(self):
        assert _strip_dosage("비타민D정 1000IU") == "비타민D정"

    def test_no_dosage_unchanged(self):
        assert _strip_dosage("타이레놀정") == "타이레놀정"

    def test_empty_string(self):
        assert _strip_dosage("") == ""

    def test_strips_decimal_dosage(self):
        assert _strip_dosage("암로디핀정 2.5mg") == "암로디핀정"


# ── _normalize_medication_names ────────────────────────────────────────────────


class TestNormalizeMedicationNames:
    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self):
        conn = AsyncMock()
        result = await _normalize_medication_names(conn, [])
        assert result == []
        conn.fetchrow.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_name_appended_unchanged(self):
        conn = AsyncMock()
        med = {"medication_name": "", "dosage": "1정"}
        result = await _normalize_medication_names(conn, [med])
        assert result == [med]
        conn.fetchrow.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_name_appended_unchanged(self):
        conn = AsyncMock()
        med = {"medication_name": None, "dosage": "1정"}
        result = await _normalize_medication_names(conn, [med])
        assert result == [med]

    @pytest.mark.asyncio
    async def test_match_replaces_name(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {"item_name": "타이레놀정500밀리그람(아세트아미노펜)"}
        med = {"medication_name": "타이레놀정 500mg", "dosage": "1정"}
        result = await _normalize_medication_names(conn, [med])
        assert result[0]["medication_name"] == "타이레놀정500밀리그람(아세트아미노펜)"

    @pytest.mark.asyncio
    async def test_no_match_keeps_original_name(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        med = {"medication_name": "알수없는약품명", "dosage": "1정"}
        result = await _normalize_medication_names(conn, [med])
        assert result[0]["medication_name"] == "알수없는약품명"

    @pytest.mark.asyncio
    async def test_other_fields_preserved_on_match(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = {"item_name": "암로디핀정5밀리그람"}
        med = {
            "medication_name": "암로디핀정 5mg",
            "dosage": "1정",
            "frequency": "1일 1회",
            "duration_days": 30,
        }
        result = await _normalize_medication_names(conn, [med])
        assert result[0]["dosage"] == "1정"
        assert result[0]["frequency"] == "1일 1회"
        assert result[0]["duration_days"] == 30

    @pytest.mark.asyncio
    async def test_multiple_meds_each_queried(self):
        conn = AsyncMock()
        conn.fetchrow.side_effect = [
            {"item_name": "타이레놀정500밀리그람(아세트아미노펜)"},
            None,
        ]
        meds = [
            {"medication_name": "타이레놀정 500mg"},
            {"medication_name": "알수없는약"},
        ]
        result = await _normalize_medication_names(conn, meds)
        assert result[0]["medication_name"] == "타이레놀정500밀리그람(아세트아미노펜)"
        assert result[1]["medication_name"] == "알수없는약"
        assert conn.fetchrow.call_count == 2


# ── parse_medications_and_diseases ────────────────────────────────────────────


class TestParseMedicationsAndDiseases:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_empty(self):
        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = None
            result = await parse_medications_and_diseases("some text", "DRUG_BAG")
        assert result == {"medications": [], "disease_codes": []}

    @pytest.mark.asyncio
    async def test_normal_prescription_response(self):
        payload = {
            "medications": [
                {
                    "medication_name": "암로디핀정5밀리그람",
                    "edi_code": "123456789",
                    "dosage": "1정",
                    "frequency": "1일 1회",
                    "timing": "식후 30분",
                    "duration_days": 30,
                    "time_of_day": ["아침"],
                    "warnings": [],
                    "confidence_score": 0.92,
                }
            ],
            "disease_codes": [{"icd10_code": "I10", "disease_name": "본태성고혈압", "confidence_score": 0.95}],
        }
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(payload)

        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
                result = await parse_medications_and_diseases("처방전 텍스트", "PRESCRIPTION")

        assert len(result["medications"]) == 1
        assert result["medications"][0]["medication_name"] == "암로디핀정5밀리그람"
        assert len(result["disease_codes"]) == 1
        assert result["disease_codes"][0]["icd10_code"] == "I10"

    @pytest.mark.asyncio
    async def test_drug_bag_no_disease_codes(self):
        """약봉투 파싱 결과에 disease_codes 없어도 정상 처리."""
        payload = {
            "medications": [{"medication_name": "타이레놀정", "confidence_score": 0.85}],
            "disease_codes": [],
        }
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(payload)

        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
                result = await parse_medications_and_diseases("약봉투 텍스트", "DRUG_BAG")

        assert len(result["medications"]) == 1
        assert result["disease_codes"] == []

    @pytest.mark.asyncio
    async def test_null_fields_in_response(self):
        """GPT가 일부 필드를 null로 반환해도 정상 처리."""
        payload = {
            "medications": [
                {
                    "medication_name": "넥시움정",
                    "edi_code": None,
                    "generic_name": None,
                    "dosage": None,
                    "frequency": None,
                    "timing": None,
                    "usage_time": None,
                    "duration_days": None,
                    "time_of_day": None,
                    "warnings": [],
                    "confidence_score": 0.65,
                }
            ],
            "disease_codes": [],
        }
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(payload)

        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
                result = await parse_medications_and_diseases("약봉투", "DRUG_BAG")

        med = result["medications"][0]
        assert med["medication_name"] == "넥시움정"
        assert med["dosage"] is None
        assert med["duration_days"] is None

    @pytest.mark.asyncio
    async def test_missing_keys_in_response_use_defaults(self):
        """GPT 응답에 medications/disease_codes 키 없으면 빈 배열 반환."""
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps({})

        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
                result = await parse_medications_and_diseases("텍스트", "DRUG_BAG")

        assert result == {"medications": [], "disease_codes": []}

    @pytest.mark.asyncio
    async def test_openai_exception_returns_empty(self):
        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API 오류"))
                result = await parse_medications_and_diseases("텍스트", "PRESCRIPTION")

        assert result == {"medications": [], "disease_codes": []}

    @pytest.mark.asyncio
    async def test_empty_medications_array(self):
        """GPT가 medications를 빈 배열로 반환해도 정상 처리."""
        payload = {"medications": [], "disease_codes": []}
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(payload)

        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
                result = await parse_medications_and_diseases("읽을 수 없는 텍스트", "DRUG_BAG")

        assert result == {"medications": [], "disease_codes": []}

    @pytest.mark.asyncio
    async def test_multiple_disease_codes(self):
        """처방전에 상병코드가 여러 개인 경우 모두 반환."""
        payload = {
            "medications": [],
            "disease_codes": [
                {"icd10_code": "J45.0", "disease_name": "기관지천식", "confidence_score": 0.93},
                {"icd10_code": "J30.1", "disease_name": "알레르기비염", "confidence_score": 0.88},
            ],
        }
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(payload)

        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
                result = await parse_medications_and_diseases("처방전", "PRESCRIPTION")

        assert len(result["disease_codes"]) == 2
        codes = [d["icd10_code"] for d in result["disease_codes"]]
        assert "J45.0" in codes
        assert "J30.1" in codes

    @pytest.mark.asyncio
    async def test_text_truncated_to_3000_chars(self):
        """3000자 초과 텍스트는 잘려서 GPT에 전달된다."""
        long_text = "약물정보 " * 1000  # ~5000자

        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps({"medications": [], "disease_codes": []})

        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
                await parse_medications_and_diseases(long_text, "DRUG_BAG")

        call_kwargs = mock_client.chat.completions.create.call_args
        user_content = call_kwargs.kwargs["messages"][1]["content"]
        # 3000자 제한 + 문서유형 헤더가 포함된 user message
        # OCR 텍스트 부분만 3000자 이하인지 확인
        assert len(user_content) <= 3100  # 헤더 포함 약간의 여유

    @pytest.mark.asyncio
    async def test_warnings_present_in_document(self):
        """문서에 약물별 주의 문구가 있으면 warnings에 담긴다."""
        payload = {
            "medications": [
                {
                    "medication_name": "졸피뎀정",
                    "dosage": "1정",
                    "frequency": "1일 1회",
                    "timing": "취침 전",
                    "duration_days": 14,
                    "time_of_day": None,
                    "warnings": ["졸음 유발 - 운전 주의", "음주 금지"],
                    "confidence_score": 0.91,
                }
            ],
            "disease_codes": [],
        }
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(payload)

        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
                result = await parse_medications_and_diseases("약봉투", "DRUG_BAG")

        med = result["medications"][0]
        assert med["warnings"] == ["졸음 유발 - 운전 주의", "음주 금지"]

    @pytest.mark.asyncio
    async def test_warnings_empty_when_not_in_document(self):
        """문서에 약물 전용 주의 문구가 없으면 warnings는 빈 배열."""
        payload = {
            "medications": [
                {
                    "medication_name": "타이레놀정",
                    "dosage": "1정",
                    "frequency": "1일 3회",
                    "warnings": [],
                    "confidence_score": 0.88,
                }
            ],
            "disease_codes": [],
        }
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(payload)

        with patch("ai_worker.tasks.ocr_parser.config") as mock_cfg:
            mock_cfg.OPENAI_API_KEY = "test-key"
            with patch("ai_worker.tasks.ocr_parser.AsyncOpenAI") as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
                result = await parse_medications_and_diseases("약봉투", "DRUG_BAG")

        assert result["medications"][0]["warnings"] == []
