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
import re

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
예: "매출 700" → 700만원 = 7,000,000원

- revenue: 예상 월매출 데이터 리스트 (숫자 배열, 원 단위)
- cost: 예상 월 원가 (숫자, 원 단위)
- salary: 직원 급여 (숫자, 원 단위, 고정급 또는 시급)
- hours: 월 근무시간 (시급일 경우만, 없으면 생략)
- rent: 임대료 (원 단위, 없으면 0)
- admin: 관리비 (원 단위, 없으면 0)
- fee: 수수료 (원 단위, 없으면 0)
- tax_rate: 세율 (기본값 0.2)
- initial_investment: 초기 투자비용 (원 단위, 언급 없으면 생략)

출력은 JSON 형식으로만 하세요."""

_EXPLAIN_PROMPT = """다음은 창업 재무 시뮬레이션 결과입니다.

[시뮬레이션 가정 조건]
{assumptions}

[시뮬레이션 결과 — 10,000회 몬테카를로]
- 평균 월 순이익: {avg_profit:,}원
- 표준편차: {std_profit:,}원
- 90% 신뢰구간: {p5:,}원 ~ {p95:,}원  (하위 5% ~ 상위 95%)
- 손실 발생 관측 여부: {loss_prob}

위 결과를 바탕으로 사업 가능성을 설명하세요.
- 응답 첫 단락에 위의 가정 조건(월매출, 원가, 급여 등)을 명시하세요.
- 신뢰구간과 표준편차를 언급하여 예측의 불확실성을 구체적으로 설명하세요.
- 위험 요인과 기회 요인을 함께 언급하세요.
- 낙관·기본·비관 시나리오와 리스크 경고를 포함하세요.
- 손실 발생 확률이 낮더라도 실제 사업에서는 시뮬레이션 범위 밖의 리스크(예: 경기 침체, 예상 외 비용 급증)가 존재함을 반드시 언급하세요.
- **주의**: "손실 발생 확률 0%" 또는 이와 동일한 의미의 표현을 그대로 쓰지 마세요. 대신 "시뮬레이션 가정 범위 내에서는 손실이 관측되지 않았으나, 외부 충격에는 취약할 수 있습니다" 형식으로 서술하세요.
- 투자 권유가 아닌 정보 제공임을 명시하세요.
- 경영자가 이해하기 쉬운 자연어로 작성하세요.

응답 형식:
[사용자 질문]
{question}

[에이전트 응답]
(위 기준을 충족하는 응답 내용)"""

_RECOVERY_PROMPT = """초기 투자비용 회수 시뮬레이션 결과:
- 회수 가능 여부: {recoverable}
- 예상 소요 기간: {months}개월

위 결과를 바탕으로 투자 회수 가능성을 짧게 설명하세요.
예: "투자 회수까지 약 n개월(n년 n개월)이 소요됩니다." """

_RETRY_PREFIX = """이전 응답에서 다음 문제가 지적되었습니다. 반드시 반영하여 전체 응답을 다시 작성하십시오.

[지적 사항]
{retry_prompt}

"""


class FinanceAgent:
    def __init__(self, kernel: Kernel):
        self._kernel = kernel
        self._sim = FinanceSimulationPlugin()

    async def _call_llm(self, prompt: str) -> str:
        service: AzureChatCompletion = self._kernel.get_service("sign_off")
        history = ChatHistory()
        history.add_user_message(prompt)
        settings = OpenAIChatPromptExecutionSettings(temperature=0.3, max_tokens=2000)
        result = await service.get_chat_message_content(history, settings=settings)
        return str(result)

    async def _extract_params(self, question: str) -> dict:
        """자연어 질문 → 시뮬레이션 파라미터 JSON 추출."""
        raw = await self._call_llm(_PARAM_EXTRACT_PROMPT.format(user_input=question))
        clean = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # 파싱 실패 시 최소한의 기본값 반환
            return {"revenue": [5_000_000], "cost": 2_000_000, "salary": 2_000_000, "tax_rate": 0.2}

    @kernel_function(name="generate_draft", description="재무 시뮬레이션 기반 draft 생성")
    async def generate_draft(self, question: str, retry_prompt: str = "") -> str:
        # ── 1단계: 파라미터 추출 ─────────────────────────────
        variables = await self._extract_params(question)

        # ── 2단계: 시뮬레이션 실행 ──────────────────────────
        sim_keys = ["revenue", "cost", "salary", "hours", "rent", "admin", "fee", "tax_rate"]
        sim_input = {k: variables[k] for k in sim_keys if k in variables}
        sim_result = self._sim.monte_carlo_simulation(**sim_input)

        recovery_result: dict | None = None
        if "initial_investment" in variables:
            recovery_result = self._sim.investment_recovery(
                initial_investment=variables["initial_investment"],
                avg_profit=sim_result["average_net_profit"],
            )

        # ── 3단계: 설명 draft 생성 ──────────────────────────
        # 가정 조건 문자열 구성
        rev = variables.get("revenue", [])
        rev_str = f"{rev[0]:,}원" if len(rev) == 1 else f"{min(rev):,}~{max(rev):,}원 (복수 시나리오)"
        assumption_lines = [
            f"- 월매출: {rev_str} (±10% 정규분포 가정)",
            f"- 원가: {variables.get('cost', 0):,}원 (±10% 정규분포 가정)",
            f"- 급여: {variables.get('salary', 0):,}원",
        ]
        if variables.get("rent"): assumption_lines.append(f"- 임대료: {variables['rent']:,}원")
        if variables.get("admin"): assumption_lines.append(f"- 관리비: {variables['admin']:,}원")
        if variables.get("fee"):   assumption_lines.append(f"- 수수료: {variables['fee']:,}원")
        assumption_lines.append(f"- 세율: {variables.get('tax_rate', 0.2):.0%}")
        assumptions = "\n".join(assumption_lines)

        # 손실확률: 0%이면 수치 자체를 제거하고 서술형으로만 전달
        # (sign-off C5·F5는 "0%" 수치 자체를 리스크 부정 표현으로 판정함)
        raw_loss = sim_result["loss_probability"]
        if raw_loss == 0.0:
            loss_prob_str = (
                "이번 시뮬레이션 가정 범위(매출·원가 ±10%) 내에서는 손실 케이스가 관측되지 않았음. "
                "단, 경기 침체·임대료 급등·수요 급감 등 시뮬레이션 가정 밖의 충격이 발생하면 "
                "실제 손실로 이어질 수 있으며, 이 결과는 미래 수익을 보장하지 않음."
            )
        else:
            loss_prob_str = f"10,000회 중 {raw_loss:.1%}에서 손실 발생"

        explain_prompt = _EXPLAIN_PROMPT.format(
            assumptions=assumptions,
            avg_profit=sim_result["average_net_profit"],
            std_profit=sim_result["std_profit"],
            p5=sim_result["p5_net_profit"],
            p95=sim_result["p95_net_profit"],
            loss_prob=loss_prob_str,
            question=question,
        )
        if retry_prompt:
            explain_prompt = _RETRY_PREFIX.format(retry_prompt=retry_prompt) + explain_prompt

        draft = await self._call_llm(explain_prompt)

        # ── 4단계: 투자 회수 설명 병합 (있을 때만) ───────────
        if recovery_result and recovery_result.get("recoverable") and recovery_result.get("months"):
            recovery_text = await self._call_llm(
                _RECOVERY_PROMPT.format(
                    recoverable=recovery_result["recoverable"],
                    months=recovery_result["months"],
                )
            )
            draft = f"{draft}\n\n[투자 회수 전망]\n{recovery_text}"

        return draft
