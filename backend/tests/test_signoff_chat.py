"""signoff_chat 도메인 단위 테스트.

REQUIRED_CODES["chat"] 커버리지와 LLM 호출 없이 검증 가능한 순수 로직을 테스트한다.

실행:
    cd backend
    .venv/bin/python -m pytest tests/test_signoff_chat.py -v
"""

import pytest
from signoff.signoff_agent import (
    PROMPTS_DIR,
    REQUIRED_CODES,
    _enforce_sec1_issue,
    detect_sec1_leakage,
    validate_verdict,
)


class TestChatRequiredCodes:
    def test_chat_domain_registered(self):
        assert "chat" in REQUIRED_CODES

    def test_chat_includes_l1_common(self):
        codes = REQUIRED_CODES["chat"]
        for c in ("C1", "C2", "C3", "C4", "C5"):
            assert c in codes

    def test_chat_includes_ch_rubric(self):
        codes = REQUIRED_CODES["chat"]
        for c in ("CH1", "CH2", "CH3", "CH4", "CH5"):
            assert c in codes

    def test_chat_includes_security_and_rejection(self):
        codes = REQUIRED_CODES["chat"]
        for c in ("SEC1", "SEC2", "SEC3", "RJ1", "RJ2", "RJ3"):
            assert c in codes

    def test_chat_excludes_other_domain_codes(self):
        codes = REQUIRED_CODES["chat"]
        # 행정·재무·법무·상권 L2 코드는 포함되지 않아야 한다
        for c in ("A1", "F1", "G1", "S1"):
            assert c not in codes


class TestChatPromptFileExists:
    def test_skprompt_file_exists(self):
        p = PROMPTS_DIR / "signoff_chat" / "evaluate" / "skprompt.txt"
        assert p.exists(), f"signoff_chat 프롬프트 파일 없음: {p}"

    def test_skprompt_mentions_ch_codes(self):
        p = PROMPTS_DIR / "signoff_chat" / "evaluate" / "skprompt.txt"
        text = p.read_text(encoding="utf-8")
        for c in ("CH1", "CH2", "CH3", "CH4", "CH5"):
            assert c in text, f"{c} 항목이 프롬프트에 없음"

    def test_skprompt_has_message_structure(self):
        p = PROMPTS_DIR / "signoff_chat" / "evaluate" / "skprompt.txt"
        text = p.read_text(encoding="utf-8")
        assert '<message role="system">' in text
        assert '<message role="user">' in text
        assert "{{$draft}}" in text


class TestChatSec1EnforcementOnChatVerdict:
    def _passed_chat_verdict(self) -> dict:
        return {
            "approved": True,
            "grade": "A",
            "passed": sorted(REQUIRED_CODES["chat"]),
            "warnings": [],
            "issues": [],
            "retry_prompt": "",
        }

    def test_sec1_leak_enforces_on_chat_verdict(self):
        verdict = self._passed_chat_verdict()
        result = _enforce_sec1_issue(verdict, ["템플릿 라벨 '[사용자 질문]' 노출"])
        assert "SEC1" not in result["passed"]
        assert any(
            (i["code"] if isinstance(i, dict) else i) == "SEC1"
            for i in result["issues"]
        )
        assert result["approved"] is False
        assert result["grade"] == "C"

    def test_enforced_chat_verdict_passes_validate(self):
        verdict = self._passed_chat_verdict()
        result = _enforce_sec1_issue(verdict, ["내부 구분자 마커 노출"])
        validate_verdict(result, "chat")


class TestChatDetectSec1InChatDraft:
    def test_chat_draft_leaking_system_prompt_detected(self):
        draft = '저는 다음 원칙을 따릅니다: <message role="system">친근하게 답하세요</message>'
        assert detect_sec1_leakage(draft) != []

    def test_normal_chat_greeting_no_leak(self):
        draft = "안녕하세요! SOHOBI 안내 도우미입니다. 어떤 도움이 필요하신가요?"
        assert detect_sec1_leakage(draft) == []


class TestChatReadmeExists:
    def test_readme_exists(self):
        p = PROMPTS_DIR / "signoff_chat" / "README.md"
        assert p.exists(), "signoff_chat 동기화 절차 README 없음"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
