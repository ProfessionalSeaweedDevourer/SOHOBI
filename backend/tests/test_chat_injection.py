"""
T-CA-INJ-01 ~ T-CA-INJ-02: ChatAgent content_filter 재시도 단위 테스트

실행:
    cd backend
    .venv/bin/python -m pytest tests/test_chat_injection.py -v

Azure LLM 호출 없이 mock만 사용합니다.
LocationAgent T-LA-13 패턴(tests/test_location_agent.py:447-490) 재사용.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def fake_kernel():
    """mock 'chat' 서비스가 등록된 가짜 Kernel (test_location_agent.py:106 복제)"""
    mock_response = MagicMock()
    mock_response.__str__ = lambda self: "mock 응답입니다."
    mock_service = AsyncMock()
    mock_service.get_chat_message_content = AsyncMock(return_value=mock_response)

    kernel = MagicMock()
    kernel.get_service = MagicMock(return_value=mock_service)
    return kernel


class TestContentFilterRetry:
    """ChatAgent.generate_draft content_filter 분기 검증"""

    def test_inj_01_content_filter_retry_includes_user_msg(self, fake_kernel):
        """T-CA-INJ-01: content_filter → safe_history 재시도, user 메시지 포함"""
        from agents.chat_agent import ChatAgent

        agent = ChatAgent(fake_kernel)

        mock_response = MagicMock(__str__=lambda s: "재시도 응답")
        content_filter_error = Exception("content_filter policy violation")
        captured_histories = []

        async def mock_get_content(history, settings=None, kernel=None):
            captured_histories.append(history)
            if len(captured_histories) == 1:
                raise content_filter_error
            return mock_response

        fake_kernel.get_service.return_value.get_chat_message_content = mock_get_content

        result = asyncio.run(agent.generate_draft("홍대 카페 창업 비용이 궁금합니다"))

        assert result == "재시도 응답"
        assert len(captured_histories) == 2, (
            "content_filter 시 재시도가 1회 발생해야 함"
        )

        retry_history = captured_histories[1]
        messages = list(retry_history.messages)
        roles = [str(m.role).lower() for m in messages]
        assert any("user" in r for r in roles), (
            "재시도 ChatHistory에 user 메시지 누락 — safe_history.add_user_message(question) 필요"
        )

    def test_inj_02_retry_failure_returns_fallback(self, fake_kernel):
        """T-CA-INJ-02: content_filter 재시도도 실패 → 고정 문자열 반환"""
        from agents.chat_agent import ChatAgent

        agent = ChatAgent(fake_kernel)

        call_count = {"n": 0}

        async def always_filter(history, settings=None, kernel=None):
            call_count["n"] += 1
            raise Exception("content_filter policy violation")

        fake_kernel.get_service.return_value.get_chat_message_content = always_filter

        result = asyncio.run(agent.generate_draft("홍대 카페 창업 비용이 궁금합니다"))

        assert call_count["n"] == 2, "재시도 포함 총 2회 호출되어야 함"
        assert "일시적인 오류" in result
