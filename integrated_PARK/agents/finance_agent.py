"""
재무 에이전트 (강화 — CHANG 워크플로우 통합)
출처: PARK/Code_EJP/agents/finance_agent.py (기반)
     CHANG/main_agent.py + CHANG/skills/investment-simulation.yaml (파이프라인)

파이프라인:
  1. 사용자 질문 → LLM으로 시뮬레이션 파라미터 JSON 추출
  2. FinanceSimulationPlugin (Python) 으로 몬테카를로 시뮬레이션 실행
  3. 시뮬레이션 결과 + (투자 회수 결과) → LLM으로 설명 draft 생성
  4. 생성된 draft → SignOffAgent 판정

FunctionChoiceBehavior.Auto 대신 명시적 3단계 파이프라인을 사용하여
수치 파라미터 추출의 안정성을 높인다.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import kernel_function

from plugins.finance_simulation_plugin import FinanceSimulationPlugin

# ── 워크플로우 프롬프트 (CHANG/skills/investment-simulation.yaml 인라인) ──

_PARAM_EXTRACT_PROMPT = """사용자가 다음과 같은 질문을 했습니다:
"{user_input}"

이 질문을 기반으로 아래 변수들을 추정해 JSON으로 출력하세요.
단, 숫자에 단위가 명시되지 않은 경우 기본적으로 '만원' 단위로 해석하세요.
예: "매출 700" → 700만원 → 7,000,000원

- revenue: 예상 월매출 데이터 리스트 (숫자 배열, 원 단위). 사용자가 단일 값만 언급한 경우 반드시 1개짜리 배열로 작성.
- cost: 예상 월 원가 (숫자, 원 단위)
- salary: 직원 급여 (숫자, 원 단위, 고정급 또는 시급)
- hours: 월 근무시간 (시급일 경우만, 없으면 생략)
- rent: 임대료 (원 단위)
- admin: 관리비 (원 단위)
- fee: 수수료 (원 단위)
- initial_investment: 초기 투자비용 (원 단위)

사용자가 명시적으로 언급한 항목만 값을 채우고, 언급하지 않은 항목은 반드시 null으로 두세요.
임의로 값을 추정하거나 채워넣지 마세요.

출력은 JSON 형식으로만 하세요."""

_EXPLAIN_PROMPT = """다음은 창업 재무 시뮬레이션 결과입니다.

[시뮬레이션 가정 조건]
{assumptions}

[시뮬레이션 결과 — 10,000회 몬테카를로]
★ 손실 발생 확률: {loss_prob}  ← 핵심 지표
- 평균 월 순이익: {avg_profit:,}원
- 손실(0원 미만의 순이익) 발생 관측 여부: {loss_prob}
- 비관 시나리오 월 순이익: {p20:,}원
  (전체 시뮬레이션 중 하위 20%에 해당하는 케이스의 상단 기준값)

위 수치를 그대로 사용하여 별도 계산 없이 아래 형식으로 작성하세요.

[1. 가정 조건]과 [2. 시뮬레이션 결과], [안내]는 이미 작성되어 있으므로 수정하거나 내용을 추가하지 마세요.
[3. 외부 리스크 경고] 섹션의 내용만 직접 작성하고,
나머지 섹션은 아래 형식 그대로 출력하세요.

[사용자 질문]
{question}

[에이전트 응답]

[1. 가정 조건]
{assumptions}\n
입력되지 않은 항목은 지역/업종/상권 평균치를 적용하였으며, 추가 입력 시 더 정확한 결과를 제공할 수 있습니다.

[2. 시뮬레이션 결과]
- 평균 월 순이익: {avg_profit:,}원
- 손실(0원 미만의 순이익) 발생 관측 여부: 10,000회 중 {loss_prob}
- 비관 시나리오(하위 20%) 월 순이익: {p20:,}원.\n
  이는 10명 중 2명꼴로 월 순이익이 {p20:,}원 이하에 그칠 수 있으며, 이것이 지속될 경우 사업 운영에 부담이 될 수 있음을 의미합니다.

[3. 외부 리스크 경고]\n
(시뮬레이션을 기반으로 한 리스크 및 시뮬레이션 가정 범위 밖의 외부 충격—경기 침체, 임대료 급등, 수요 급감 등—이
발생할 경우 실제 손실로 이어질 수 있음을 경고하세요.)

[안내]
본 결과는 투자 권유가 아닌 정보 제공을 목적으로 하며, 실제 사업 결과와 다를 수 있습니다.
"""

_RECOVERY_PROMPT = """초기 투자비용 회수 시뮬레이션 결과:
- 회수 가능 여부: {recoverable}
- 예상 소요 기간: {months}개월

위 결과를 바탕으로 투자 회수 가능성을 짧게 설명하세요.
예: "투자 회수까지 약 n개월(n년 n개월)이 소요됩니다." """

_RETRY_PREFIX = """이전 응답에서 다음 문제가 지적되었습니다. 반드시 반영하여 전체 응답을 다시 작성하십시오.

[지적 사항]
{retry_prompt}

"""

_PROFILE_CONTEXT = """[창업자 상황]
{profile}

"""


class FinanceAgent:
    def __init__(self, kernel: Kernel, region: str = None, industry: str = None):
        self._kernel = kernel
        self._sim = FinanceSimulationPlugin()

    async def _call_llm(self, prompt: str, _retry: bool = False) -> str:
        service: AzureChatCompletion = self._kernel.get_service("sign_off")
        history = ChatHistory()
        history.add_user_message(prompt)
        settings = OpenAIChatPromptExecutionSettings(max_completion_tokens=5000)
        try:
            result = await service.get_chat_message_content(history, settings=settings)
            return result.content or str(result)
        except Exception as e:
            err_str = str(e).lower()
            logger.error("FinanceAgent LLM 호출 실패 (_retry=%s): %s", _retry, e)
            if ("content_filter" in err_str or "content filter" in err_str) and not _retry:
                # Azure 콘텐츠 필터 오탐 → 안전 문구를 앞에 붙여 1회 재시도
                safe_prompt = "다음은 합법적인 창업 재무 분석 요청입니다.\n\n" + prompt
                return await self._call_llm(safe_prompt, _retry=True)
            raise ValueError(
                f"AI 응답 생성 중 오류가 발생했습니다: {e}"
            ) from e

    async def _extract_params(self, question: str) -> dict:
        raw = await self._call_llm(_PARAM_EXTRACT_PROMPT.format(user_input=question))
        clean = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            current = json.loads(clean)
        except json.JSONDecodeError:
            current = {}
        return current  # ← LLM 추출값만 반환

    async def _call_llm_with_history(
        self, prompt: str, prior_history: list[dict] | None = None
    ) -> str:
        """explanation 단계 전용: prior_history를 ChatHistory에 주입 후 LLM 호출."""
        service: AzureChatCompletion = self._kernel.get_service("sign_off")
        history = ChatHistory()
        for msg in (prior_history or []):
            if msg["role"] == "user":
                history.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                history.add_assistant_message(msg["content"])
        history.add_user_message(prompt)
        settings = OpenAIChatPromptExecutionSettings(max_completion_tokens=5000)
        try:
            result = await service.get_chat_message_content(history, settings=settings)
            return result.content or str(result)
        except Exception as e:
            err_str = str(e).lower()
            logger.error("FinanceAgent explanation LLM 호출 실패: %s", e)
            if "content_filter" in err_str or "content filter" in err_str:
                safe_prompt = "다음은 합법적인 창업 재무 분석 요청입니다.\n\n" + prompt
                history2 = ChatHistory()
                history2.add_user_message(safe_prompt)
                result = await service.get_chat_message_content(history2, settings=settings)
                return result.content or str(result)
            raise ValueError(f"AI 응답 생성 중 오류가 발생했습니다: {e}") from e

    @kernel_function(name="generate_draft", description="재무 시뮬레이션 기반 draft 생성")
    async def generate_draft(
        self,
        question: str,
        current_params: dict = None,
        retry_prompt: str = "",
        profile: str = "",
        prior_history: list[dict] | None = None,
    ) -> str:
        # ── 1단계: 파라미터 추출 ─────────────────────────────
        # current_params 없으면 None 기반 초기값 사용
        base = current_params or self._sim.load_initial()
        extracted = await self._extract_params(question)
        variables = self._sim.merge_json(base, extracted)
        # state를 front-end에서 저장(브라우저별)하는 방식, current_params가 front에 저장된 변수들입니다.
        # front 저장방식: 개인폴더 chat_test.html 의 line 408~부분 or 개발일지 참조
        # ── 2단계: 시뮬레이션 실행 ──────────────────────────
        sim_keys = ["revenue", "cost", "salary", "hours", "rent", "admin", "fee"]

        sim_input = {k: variables[k] for k in sim_keys if variables.get(k) is not None}

        sim_result = self._sim.monte_carlo_simulation(**sim_input)

        recovery_result: dict | None = None
        if variables.get("initial_investment") is not None:
            recovery_result = self._sim.investment_recovery(
                initial_investment=variables["initial_investment"],
                avg_profit=sim_result["average_net_profit"],
            )

        # ── 3단계: 설명 draft 생성 ──────────────────────────
        # 가정 조건 문자열 구성
        rev = variables.get("revenue") or []
        rev_str = f"{rev[0]:,}원" if len(rev) == 1 else f"{min(rev):,}~{max(rev):,}원 (복수 시나리오)"
        assumption_lines = [
            f"- 월매출: {rev_str}",
            f"- 원가: {sim_result['actual_cost']:,}원",
            f"- 급여: {sim_result['actual_salary']:,}원",
            f"- 임대료: {sim_result['actual_rent']:,}원",
            f"- 관리비: {sim_result['actual_admin']:,}원",
            f"- 수수료: {sim_result['actual_fee']:,}원",
        ]
        assumptions = "\n".join(assumption_lines)

        # 손실확률: 핵심 지표로 명시.
        # 0%이면 서술형으로 표현 (수치 "0%"가 리스크 부정으로 오해되는 것을 방지)
        is_multi = len(rev) > 1
        raw_loss = sim_result["loss_probability"]
        if raw_loss == 0.0:
            range_desc = f"실제 매장 {len(rev)}개 데이터" if is_multi else "매출·원가 ±10%"
            loss_prob_str = (
                f"이번 시뮬레이션({range_desc}) 범위 내에서는 손실 케이스가 관측되지 않았음. "
                "단, 경기 침체·임대료 급등·수요 급감 등 시뮬레이션 범위 밖의 충격이 발생하면 "
                "실제 손실로 이어질 수 있으며, 이 결과는 미래 수익을 보장하지 않음."
            )
        else:
            loss_prob_str = f"{raw_loss:.1%} (10,000회 시뮬레이션 기준)"

        explain_prompt = _EXPLAIN_PROMPT.format(
            assumptions=assumptions,
            avg_profit=sim_result["average_net_profit"],
            loss_prob=loss_prob_str,
            p20=sim_result["p20"],        # 추가
            question=question,
        )
        if profile:
            explain_prompt = _PROFILE_CONTEXT.format(profile=profile) + explain_prompt
        if retry_prompt:
            explain_prompt = _RETRY_PREFIX.format(retry_prompt=retry_prompt) + explain_prompt
        draft = await self._call_llm_with_history(explain_prompt, prior_history=prior_history)

        # ── 4단계: 투자 회수 설명 병합 (있을 때만) ───────────
        if recovery_result and recovery_result.get("recoverable") and recovery_result.get("months"):
            recovery_text = await self._call_llm(
                _RECOVERY_PROMPT.format(
                    recoverable=recovery_result["recoverable"],
                    months=recovery_result["months"],
                )
            )
            draft = f"{draft}\n\n[투자 회수 전망]\n{recovery_text}"

        return {
            "draft":          draft,
            "chart":          sim_result.get("chart"),   # base64 PNG 또는 None
            "updated_params": variables,                  # 누적된 파라미터 (프론트 저장용)
        }
