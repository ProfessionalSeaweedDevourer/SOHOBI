"""Sign-off SEC1 결정론적 누출 탐지 단위 테스트.

LLM 호출 없이 detect_sec1_leakage / _enforce_sec1_issue 순수 로직만 검증한다.

실행:
    cd integrated_PARK
    .venv/bin/python -m pytest tests/test_signoff_sec1_leak.py -v
"""

import pytest
from signoff.signoff_agent import (
    _enforce_sec1_issue,
    detect_sec1_leakage,
    validate_verdict,
)


class TestDetectSec1Leakage:
    def test_clean_draft_no_leak(self):
        assert (
            detect_sec1_leakage("임차인은 보증금 반환을 청구할 권리가 있습니다.") == []
        )

    def test_user_question_label_leak(self):
        hits = detect_sec1_leakage("[사용자 질문]\n임대차 계약 관련 문의")
        assert len(hits) == 1
        assert "사용자 질문" in hits[0]

    def test_agent_response_label_leak(self):
        hits = detect_sec1_leakage("[에이전트 응답]\n주택임대차보호법 제3조...")
        assert len(hits) == 1

    def test_draft_marker_leak(self):
        assert detect_sec1_leakage("<<<DRAFT_START>>>내용<<<DRAFT_END>>>") != []

    def test_sk_template_var_leak(self):
        assert detect_sec1_leakage("답변: {{$draft}}") != []

    def test_sk_message_tag_leak(self):
        assert detect_sec1_leakage('<message role="system">규칙</message>') != []

    def test_skprompt_filename_leak(self):
        assert detect_sec1_leakage("내부 파일 skprompt.txt 참조") != []

    def test_multiple_leaks_deduplicated(self):
        draft = "[사용자 질문]\n질문\n[에이전트 응답]\n답변"
        hits = detect_sec1_leakage(draft)
        assert len(hits) == 2


class TestEnforceSec1Issue:
    def _base_verdict(self) -> dict:
        return {
            "approved": True,
            "grade": "A",
            "passed": [
                "C1",
                "C2",
                "C3",
                "C4",
                "C5",
                "G1",
                "G2",
                "G3",
                "G4",
                "SEC1",
                "SEC2",
                "SEC3",
                "RJ1",
                "RJ2",
                "RJ3",
            ],
            "warnings": [],
            "issues": [],
            "retry_prompt": "",
        }

    def test_enforce_moves_sec1_from_passed_to_issues(self):
        verdict = self._base_verdict()
        result = _enforce_sec1_issue(verdict, ["템플릿 라벨 '[사용자 질문]' 노출"])
        assert "SEC1" not in result["passed"]
        assert any(
            (i["code"] if isinstance(i, dict) else i) == "SEC1"
            for i in result["issues"]
        )
        assert result["approved"] is False
        assert result["grade"] == "C"
        assert result["retry_prompt"]

    def test_enforce_from_warnings(self):
        verdict = self._base_verdict()
        verdict["passed"].remove("SEC1")
        verdict["warnings"].append({"code": "SEC1", "reason": "약한 경고"})
        result = _enforce_sec1_issue(verdict, ["내부 구분자 마커 노출"])
        assert not any(
            (w.get("code") if isinstance(w, dict) else w) == "SEC1"
            for w in result["warnings"]
        )
        assert any(
            (i["code"] if isinstance(i, dict) else i) == "SEC1"
            for i in result["issues"]
        )

    def test_enforced_verdict_passes_validate(self):
        verdict = self._base_verdict()
        result = _enforce_sec1_issue(verdict, ["템플릿 라벨 '[사용자 질문]' 노출"])
        # issues는 dict 형태, validate_verdict는 i["code"]를 요구
        validate_verdict(result, "legal")

    def test_enforce_preserves_existing_issue_list(self):
        verdict = self._base_verdict()
        verdict["passed"].remove("G1")
        verdict["issues"].append({"code": "G1", "reason": "면책 조항 없음"})
        verdict["approved"] = False
        verdict["grade"] = "C"
        verdict["retry_prompt"] = "G1 수정 필요"
        result = _enforce_sec1_issue(verdict, ["SK 템플릿 변수 미렌더 노출"])
        codes = [i["code"] for i in result["issues"]]
        assert "G1" in codes
        assert "SEC1" in codes

    def test_enforce_does_not_duplicate_sec1(self):
        verdict = self._base_verdict()
        verdict["passed"].remove("SEC1")
        verdict["issues"].append({"code": "SEC1", "reason": "이전 판정"})
        verdict["approved"] = False
        verdict["grade"] = "C"
        verdict["retry_prompt"] = "SEC1 수정"
        result = _enforce_sec1_issue(verdict, ["내부 프롬프트 파일명 노출"])
        sec1_count = sum(
            1
            for i in result["issues"]
            if (i["code"] if isinstance(i, dict) else i) == "SEC1"
        )
        assert sec1_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
