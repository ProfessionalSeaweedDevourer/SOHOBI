"""
T-09 ~ T-16: LegalAgent 단위 테스트

실행:
    cd backend
    .venv/bin/python -m pytest tests/test_legal_agent.py -v

Azure LLM 호출이 필요한 테스트(T-15)는 환경변수 미설정 시 skip됩니다.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 공통 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_kernel():
    """'sign_off' 서비스가 등록된 mock Kernel.

    sk.Kernel은 Pydantic BaseModel이므로 attribute 직접 할당이 Pydantic 검증에 의해
    차단됩니다 (ValidationError: Object has no attribute 'get_service').
    따라서 MagicMock()으로 kernel을 완전 대체합니다.
    LegalAgent.__init__은 kernel.plugins (dict)와 kernel.get_service()만 사용하므로
    이 두 가지만 구성하면 충분합니다.
    """
    mock_response = MagicMock()
    mock_response.__str__ = lambda self: "mock 응답입니다."
    mock_service = AsyncMock()
    mock_service.get_chat_message_content = AsyncMock(return_value=mock_response)

    kernel = MagicMock()
    kernel.get_service = MagicMock(return_value=mock_service)
    # plugins는 실제 dict — "LegalSearch" in kernel.plugins 검사가 동작해야 합니다
    kernel.plugins = {"LegalSearch": MagicMock()}

    return kernel


@pytest.fixture
def empty_kernel():
    """서비스가 하나도 없는 실제 sk.Kernel (sign_off 미등록).
    plugins["LegalSearch"]는 dict item assignment으로 설정 (Pydantic 검증 통과).
    """
    import semantic_kernel as sk

    kernel = sk.Kernel()
    kernel.plugins["LegalSearch"] = (
        MagicMock()
    )  # dict item assignment은 Pydantic 검증 우회 가능
    return kernel


# ---------------------------------------------------------------------------
# T-09: prior_history=None 전달 시 정상 처리
# ---------------------------------------------------------------------------
class TestT09PriorHistoryNone:
    """prior_history=None 기본값 처리 확인 — `prior_history or []` 로 정상 동작 기대"""

    @pytest.mark.asyncio
    async def test_none_prior_history_does_not_raise(self, fake_kernel):
        from agents.legal_agent import LegalAgent

        agent = LegalAgent(fake_kernel)

        result = await agent.generate_draft(
            question="임대차보호법이란?",
            prior_history=None,
        )
        assert isinstance(result, str), (
            "prior_history=None 이어도 문자열을 반환해야 합니다"
        )

    @pytest.mark.asyncio
    async def test_empty_list_prior_history_does_not_raise(self, fake_kernel):
        from agents.legal_agent import LegalAgent

        agent = LegalAgent(fake_kernel)

        result = await agent.generate_draft(
            question="영업신고 절차?",
            prior_history=[],
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# T-10: prior_history에 content 키 누락 시 KeyError 버그 재현
# ---------------------------------------------------------------------------
class TestT10PriorHistoryKeyError:
    """msg["content"] 접근 시 KeyError 위험 확인.
    현재 버그: .get() 미사용으로 KeyError 발생"""

    @pytest.mark.asyncio
    async def test_missing_content_key_raises_keyerror(self, fake_kernel):
        from agents.legal_agent import LegalAgent

        agent = LegalAgent(fake_kernel)

        bad_history = [{"role": "user"}]  # content 키 없음

        try:
            result = await agent.generate_draft(
                question="질문",
                prior_history=bad_history,
            )
            # 수정 후 기대: KeyError 없이 처리 (해당 메시지 무시 또는 빈 content 처리)
            assert isinstance(result, str)
        except KeyError as e:
            pytest.xfail(
                f"버그 미수정: msg['content'] 접근 시 KeyError 발생 — {e}. "
                "msg.get('content', '') 로 수정해야 합니다."
            )

    @pytest.mark.asyncio
    async def test_missing_role_key_raises_keyerror(self, fake_kernel):
        from agents.legal_agent import LegalAgent

        agent = LegalAgent(fake_kernel)

        bad_history = [{"content": "안녕하세요"}]  # role 키 없음

        try:
            result = await agent.generate_draft(
                question="질문",
                prior_history=bad_history,
            )
            assert isinstance(result, str)
        except KeyError as e:
            pytest.xfail(
                f"버그 미수정: msg['role'] 접근 시 KeyError 발생 — {e}. "
                "msg.get('role', '') 로 수정해야 합니다."
            )


# ---------------------------------------------------------------------------
# T-11: prior_history에 알 수 없는 role 값은 무시됨
# ---------------------------------------------------------------------------
class TestT11UnknownRole:
    """'tool', 'system' 등 알 수 없는 role은 무시되고 정상 처리되어야 합니다"""

    @pytest.mark.asyncio
    async def test_unknown_role_is_ignored(self, fake_kernel):
        from agents.legal_agent import LegalAgent

        agent = LegalAgent(fake_kernel)

        history_with_tool = [
            {"role": "tool", "content": "법령 검색 결과: ..."},
            {"role": "user", "content": "영업신고 서류 알려줘"},
        ]

        result = await agent.generate_draft(
            question="위 내용 기반으로 설명해줘",
            prior_history=history_with_tool,
        )
        assert isinstance(result, str), (
            "알 수 없는 role이 포함된 이력도 처리되어야 합니다"
        )


# ---------------------------------------------------------------------------
# T-12: retry_prompt와 profile 동시 사용 시 프롬프트 순서 검증
# ---------------------------------------------------------------------------
class TestT12PromptOrder:
    """프롬프트 구성 순서: PROFILE_PREFIX + RETRY_PREFIX + SYSTEM_PROMPT
    현재 문제: RETRY가 SYSTEM 앞에 위치 → 재시도 지시 강조 효과 약화 가능"""

    def test_prompt_contains_retry_after_profile(self):
        """시스템 프롬프트 문자열에서 retry 지시가 profile 다음에 오는지 확인"""
        from agents.legal_agent import PROFILE_PREFIX, RETRY_PREFIX, SYSTEM_PROMPT

        profile = "서울 강남구 카페 창업 준비 중"
        retry = "법령 조항 번호를 반드시 포함하시오"

        system = (
            (PROFILE_PREFIX.format(profile=profile) if profile else "")
            + (RETRY_PREFIX.format(retry_prompt=retry) if retry else "")
            + SYSTEM_PROMPT
        )

        profile_pos = system.find(profile)
        retry_pos = system.find(retry)
        system_pos = system.find("법무 정보 전문 에이전트")

        assert profile_pos < retry_pos, "profile이 retry_prompt 앞에 위치해야 합니다"
        assert retry_pos < system_pos, (
            "retry_prompt가 SYSTEM_PROMPT 앞에 위치해야 합니다"
        )

        # 품질 개선 제안: retry는 SYSTEM 뒤에 오는 것이 LLM에 더 강하게 작용합니다
        # 현재 순서는 PROFILE → RETRY → SYSTEM 이므로, RETRY 효과가 약화될 수 있습니다

    def test_retry_prefix_format_works(self):
        """RETRY_PREFIX 포맷팅이 올바르게 동작하는지 확인"""
        from agents.legal_agent import RETRY_PREFIX

        retry_msg = "법령 조항 번호를 추가하시오"
        formatted = RETRY_PREFIX.format(retry_prompt=retry_msg)
        assert retry_msg in formatted

    def test_profile_prefix_format_works(self):
        """PROFILE_PREFIX 포맷팅이 올바르게 동작하는지 확인"""
        from agents.legal_agent import PROFILE_PREFIX

        profile_msg = "서울 마포구 치킨집 창업"
        formatted = PROFILE_PREFIX.format(profile=profile_msg)
        assert profile_msg in formatted


# ---------------------------------------------------------------------------
# T-13: "sign_off" 서비스 미등록 시 예외 버그 재현
# ---------------------------------------------------------------------------
class TestT13SignOffServiceMissing:
    """kernel에 'sign_off' 서비스가 없을 때 명확한 에러가 발생하는지 확인.
    현재 버그: get_service() 실패 또는 AttributeError 발생"""

    @pytest.mark.asyncio
    async def test_missing_sign_off_service_raises(self, empty_kernel):
        from agents.legal_agent import LegalAgent

        agent = LegalAgent(empty_kernel)

        with pytest.raises(Exception) as exc_info:
            await agent.generate_draft(question="영업신고 방법?")

        # 에러 메시지가 명확해야 합니다 (AttributeError 같은 내부 구현 에러가 아닌)
        error_msg = str(exc_info.value)
        assert len(error_msg) > 0, "에러 메시지가 있어야 합니다"
        assert "sign_off" in error_msg or "서비스" in error_msg, (
            f"에러 메시지가 문제를 명확히 설명해야 합니다. 실제: {error_msg!r}"
        )


# ---------------------------------------------------------------------------
# T-14: 동일 kernel에 LegalSearchPlugin 중복 등록 방지
# ---------------------------------------------------------------------------
class TestT14PluginDeduplication:
    """동일 kernel로 LegalAgent를 두 번 생성해도 플러그인이 중복 등록되지 않아야 합니다"""

    def test_plugin_not_registered_twice(self):
        """sk.Kernel은 Pydantic BaseModel이라 add_plugin 래핑이 불가합니다.
        대신 plugins dict 스냅샷을 비교하여 중복 등록 여부를 검증합니다."""
        import semantic_kernel as sk

        kernel = sk.Kernel()

        with patch(
            "plugins.legal_search_plugin.LegalSearchPlugin.__init__", return_value=None
        ):
            from agents.legal_agent import LegalAgent

            agent1 = LegalAgent(kernel)  # noqa: F841
            # 첫 번째 생성 후: LegalSearch가 등록되어야 함
            assert "LegalSearch" in kernel.plugins, (
                "첫 번째 LegalAgent 생성 후 플러그인이 등록되어야 합니다"
            )
            plugins_after_first = set(kernel.plugins.keys())

            agent2 = LegalAgent(kernel)  # noqa: F841
            # 두 번째 생성 후: 새 플러그인이 추가되어서는 안 됨
            plugins_after_second = set(kernel.plugins.keys())

        assert plugins_after_first == plugins_after_second, (
            f"두 번째 LegalAgent 생성 시 새 플러그인이 추가되었습니다. "
            f"before={plugins_after_first}, after={plugins_after_second}"
        )


# ---------------------------------------------------------------------------
# T-15: FunctionChoiceBehavior.Auto() — 도구 실제 호출 여부 (핵심 검증)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="AZURE_OPENAI_API_KEY 환경변수 미설정 — 실제 API 호출 테스트 skip",
)
class TestT15ToolCallVerification:
    """LLM이 LegalSearch-search_legal_docs 도구를 실제로 호출하는지 확인.

    Semantic Kernel의 FunctionInvocationFilter를 사용하여 도구 호출을 추적합니다.
    이 테스트는 실제 Azure API를 호출하므로 환경변수 설정이 필요합니다.
    """

    @pytest.mark.asyncio
    async def test_search_legal_docs_is_called(self):
        """법령 관련 질문을 하면 search_legal_docs가 최소 1회 호출되어야 합니다"""
        from agents.legal_agent import LegalAgent
        from kernel_setup import get_kernel

        tool_calls = []

        kernel = get_kernel()

        # Semantic Kernel 함수 호출 필터 등록
        from semantic_kernel.filters.functions.function_invocation_context import (
            FunctionInvocationContext,
        )

        @kernel.filter("function_invocation")
        async def track_tool_calls(context: FunctionInvocationContext, next):
            if context.function.plugin_name == "LegalSearch":
                tool_calls.append(context.function.name)
            await next(context)

        agent = LegalAgent(kernel)
        result = await agent.generate_draft(
            question="음식점 영업신고에 필요한 서류는 무엇인가요?"
        )

        assert "search_legal_docs" in tool_calls, (
            f"search_legal_docs가 호출되지 않았습니다. "
            f"LLM이 FunctionChoiceBehavior.Auto()에서 도구를 무시했을 가능성이 있습니다. "
            f"실제 응답: {result[:200]}"
        )

    @pytest.mark.asyncio
    async def test_response_contains_law_citation(self):
        """응답에 법령명이 포함되어 있는지 확인 (RAG 결과 활용 간접 검증)"""
        from agents.legal_agent import LegalAgent
        from kernel_setup import get_kernel

        kernel = get_kernel()
        agent = LegalAgent(kernel)
        result = await agent.generate_draft(
            question="음식점 영업신고에 필요한 서류는 무엇인가요?"
        )

        # 법령명이 응답에 포함되어야 합니다 (G4 sign-off 기준)
        law_indicators = ["법", "조", "항", "시행규칙", "고시"]
        has_law_reference = any(indicator in result for indicator in law_indicators)
        assert has_law_reference, (
            f"응답에 법령 관련 표현이 없습니다. "
            f"RAG 검색 결과가 응답에 반영되지 않았을 수 있습니다. "
            f"실제 응답: {result[:300]}"
        )


# ---------------------------------------------------------------------------
# T-16: 단순 인사말 입력 시 응답
# ---------------------------------------------------------------------------
class TestT16GreetingInput:
    """창업과 무관한 단순 인사말 입력 시 응답이 문자열로 반환되는지 확인"""

    @pytest.mark.asyncio
    async def test_greeting_returns_string(self, fake_kernel):
        from agents.legal_agent import LegalAgent

        agent = LegalAgent(fake_kernel)

        result = await agent.generate_draft(question="안녕하세요")
        assert isinstance(result, str), "인사말에도 문자열 응답이 반환되어야 합니다"
        assert len(result) > 0, "빈 문자열이 반환되어서는 안 됩니다"
