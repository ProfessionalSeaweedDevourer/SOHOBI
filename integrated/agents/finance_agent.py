"""
재무 에이전트 (강화)
- 기반: PARK/Code_EJP/agents/finance_agent.py
- 추가: FinanceSimulationPlugin (CHANG) — 몬테카를로 시뮬레이션 자동 호출
  LLM이 사용자 질문에서 수치를 추출해 시뮬레이션을 직접 실행한 뒤 설명한다.
"""

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import kernel_function

from plugins.finance_simulation_plugin import FinanceSimulationPlugin

SYSTEM_PROMPT = """당신은 한국 소규모 외식업 창업자를 위한 재무 분석 전문 에이전트입니다.

사용자 질문에 투자금, 매출, 비용 등 수치가 포함되어 있으면
`FinanceSim-monte_carlo_simulation` 도구를 반드시 호출하여 실제 시뮬레이션 결과를 기반으로 답하십시오.
초기 투자금이 언급된 경우 `FinanceSim-investment_recovery`도 호출하십시오.

응답 기준:
- 시뮬레이션을 사용한 경우 가정(자기자본/대출 비율, 세율 등)을 명시한다
- 금액 단위를 원(KRW)으로 일관되게 표기한다
- 낙관·기본·비관 시나리오를 포함한다
- 리스크 경고를 명시한다 (실제 결과와 다를 수 있음)
- 투자 권유가 아닌 정보 제공임을 명시한다

응답 형식:
[사용자 질문]
{question}

[에이전트 응답]
(위 기준을 충족하는 응답 내용)
"""

RETRY_PREFIX = """이전 응답에서 다음 문제가 지적되었습니다. 반드시 반영하여 전체 응답을 다시 작성하십시오.

[지적 사항]
{retry_prompt}

"""


class FinanceAgent:
    def __init__(self, kernel: Kernel):
        self._kernel = kernel
        if "FinanceSim" not in self._kernel.plugins:
            self._kernel.add_plugin(FinanceSimulationPlugin(), plugin_name="FinanceSim")

    @kernel_function(name="generate_draft", description="재무 시뮬레이션 관련 draft 생성")
    async def generate_draft(self, question: str, retry_prompt: str = "") -> str:
        service: AzureChatCompletion = self._kernel.get_service("sign_off")
        system = (RETRY_PREFIX.format(retry_prompt=retry_prompt) if retry_prompt else "") + SYSTEM_PROMPT

        history = ChatHistory()
        history.add_system_message(system)
        history.add_user_message(question)

        settings = OpenAIChatPromptExecutionSettings(
            temperature=0.3,
            function_choice_behavior=FunctionChoiceBehavior.Auto(),
        )
        response = await service.get_chat_message_content(
            history, settings=settings, kernel=self._kernel
        )
        return str(response)
