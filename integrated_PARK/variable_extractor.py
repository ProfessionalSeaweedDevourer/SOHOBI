"""
이전 에이전트 응답에서 재무 변수를 추출한다 (Path B: 세션 변수 추출).

규칙:
- 명시적으로 언급된 값만 추출한다. 추론·가정으로 채우지 않는다.
- 숫자가 포함되지 않은 텍스트는 LLM 호출 없이 빈 딕트를 반환한다.
- 실패 시 항상 {} 반환 — 메인 플로우를 중단시키지 않는다.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """다음 텍스트에서 창업 재무 시뮬레이션에 사용할 수 있는 수치를 추출하십시오.

[텍스트]
{text}

[추출 규칙]
- 텍스트에 명시적으로 언급된 값만 추출하십시오. 추론하거나 가정하지 마십시오.
- 모든 금액은 원(KRW) 단위 정수로 변환하십시오. 예: 700만원 → 7000000
- revenue는 단일 월매출 수치를 정수로 출력하십시오 (리스트 아님).
- 해당 항목이 텍스트에 없으면 출력에 포함하지 마십시오.

[추출 가능한 항목]
- revenue: 월매출 (원 단위 정수)
- cost: 월 원가 (원 단위 정수)
- salary: 급여 (원 단위 정수)
- hours: 월 근무시간 (숫자, 시급인 경우)
- rent: 임대료 (원 단위 정수)
- admin: 관리비 (원 단위 정수)
- fee: 수수료 (원 단위 정수)
- tax_rate: 세율 (0.0~1.0 소수)
- initial_investment: 초기 투자비용 (원 단위 정수)

JSON만 출력하십시오. 다른 텍스트는 절대 포함하지 마십시오."""

_NUMERIC_KEYS = {"revenue", "cost", "salary", "hours", "rent", "admin", "fee", "initial_investment"}


async def extract_financial_vars(text: str) -> dict:
    """에이전트 응답 텍스트에서 재무 변수를 추출한다. 실패 시 {} 반환."""
    if not text or not re.search(r'\d', text):
        return {}

    try:
        from kernel_setup import get_kernel
        from semantic_kernel.connectors.ai.open_ai import (
            AzureChatCompletion,
            OpenAIChatPromptExecutionSettings,
        )
        from semantic_kernel.contents import ChatHistory

        kernel = get_kernel()
        service: AzureChatCompletion = kernel.get_service("sign_off")
        history = ChatHistory()
        history.add_user_message(_EXTRACT_PROMPT.format(text=text))
        settings = OpenAIChatPromptExecutionSettings(max_completion_tokens=300)
        result = await service.get_chat_message_content(history, settings=settings)
        raw = str(result).strip()
        clean = re.sub(r'^```json\s*|\s*```$', '', raw, flags=re.MULTILINE)
        parsed = json.loads(clean)
        if not isinstance(parsed, dict):
            return {}

        # 타입 보정
        for k in list(parsed.keys()):
            if k in _NUMERIC_KEYS:
                try:
                    parsed[k] = int(parsed[k])
                except (ValueError, TypeError):
                    del parsed[k]
        if "tax_rate" in parsed:
            try:
                parsed["tax_rate"] = float(parsed["tax_rate"])
            except (ValueError, TypeError):
                del parsed["tax_rate"]

        return parsed
    except Exception as e:
        logger.warning("재무 변수 추출 실패 (무시): %s", e)
        return {}
