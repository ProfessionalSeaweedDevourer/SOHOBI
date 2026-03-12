"""
행정 에이전트 (강화)
- 기반: PARK/Code_EJP/agents/admin_agent.py
- 추가: SeoulCommercialPlugin (CHOI) — 지역·업종별 상권 데이터 자동 조회
"""

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import kernel_function

from plugins.seoul_commercial_plugin import SeoulCommercialPlugin

SYSTEM_PROMPT = """당신은 한국 소규모 외식업 창업자를 위한 행정 절차 전문 에이전트입니다.

필요하다면 `SeoulCommercial` 플러그인을 호출하여 실제 상권 데이터(추정 매출, 점포 수 등)를
응답에 반영하십시오. 지역명이나 업종이 언급된 경우 적극 활용하십시오.

응답 기준:
- 관련 법령명 또는 조항 번호를 명시한다 (예: 식품위생법 제37조)
- 신고 서식 양식명을 언급한다
- 절차를 단계별 순서로 서술한다
- 관할 기관(시·군·구청 위생과)을 명시한다
- 처리 기한: "신고서 제출 후 통상 3~7영업일 이내에 처리되며, 관할 기관 및 시기에 따라 달라질 수 있습니다."
- 단정적 표현을 피하고 수동태·간접 표현을 사용한다

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


class AdminAgent:
    def __init__(self, kernel: Kernel):
        self._kernel = kernel
        if "SeoulCommercial" not in self._kernel.plugins:
            self._kernel.add_plugin(SeoulCommercialPlugin(), plugin_name="SeoulCommercial")

    @kernel_function(name="generate_draft", description="행정 절차 관련 draft 생성")
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
