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
★ 손실 발생 확률: {loss_prob}  ← 핵심 지표
- 평균 월 순이익: {avg_profit:,}원
- 수익 분포 (하위 5% ~ 상위 95%): {p5:,}원 ~ {p95:,}원

위 결과를 바탕으로 아래 질문에 대한 창업 재무 분석 응답을 작성하십시오.

질문: {question}

작성 기준:
- 손실 발생 확률을 수치(%)로 응답의 첫 단락 또는 주요 강조 위치에 명시하십시오.
  손실 케이스가 관측되지 않은 경우에도 '관측되지 않았습니다'로 명확히 서술하십시오.
- 첫 단락에 위의 가정 조건(월매출, 원가, 급여 등)을 명시하십시오.
- 평균 순이익은 참고 수치로 제시하되, 손실 확률이 핵심 메시지임을 유지하십시오.
- 수익 분포(하위 5%·상위 95% 구간)를 보조 정보로 제공하십시오.
- 위험 요인과 기회 요인을 함께 언급하십시오.
- 낙관·기본·비관 시나리오와 리스크 경고를 포함하십시오.
- 시뮬레이션 범위 밖의 리스크(예: 경기 침체, 예상 외 비용 급증)가 존재함을 언급하십시오.
- 투자 권유가 아닌 정보 제공임을 명시하십시오.
- 경영자가 이해하기 쉬운 자연어로 작성하십시오."""

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
    def __init__(self, kernel: Kernel):
        self._kernel = kernel
        self._sim = FinanceSimulationPlugin()

    async def _call_llm(self, prompt: str, _retry: bool = False) -> str:
        service: AzureChatCompletion = self._kernel.get_service("sign_off")
        history = ChatHistory()
        history.add_user_message(prompt)
        settings = OpenAIChatPromptExecutionSettings(max_completion_tokens=3000)
        try:
            result = await service.get_chat_message_content(history, settings=settings)
            return str(result)
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

    async def _extract_params(self, question: str, profile: str = "", session_vars: dict | None = None) -> dict:
        """자연어 질문 → 시뮬레이션 파라미터 JSON 추출.

        session_vars(이전 대화에서 추출된 재무 변수)를 베이스로 사용하고,
        현재 질문에서 추출한 값으로 덮어쓴다 (질문 우선).
        """
        context = (_PROFILE_CONTEXT.format(profile=profile) if profile else "")
        raw = await self._call_llm(context + _PARAM_EXTRACT_PROMPT.format(user_input=question))
        clean = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            from_question = json.loads(clean)
        except json.JSONDecodeError:
            from_question = {}

        # 베이스: session_vars → 현재 질문 추출값으로 덮어쓰기
        base: dict = {}
        if session_vars:
            # revenue가 session_vars에 int로 저장되어 있으면 리스트로 변환
            for k, v in session_vars.items():
                base[k] = [v] if k == "revenue" and isinstance(v, int) else v
        base.update(from_question)

        if base:
            return base
        # 베이스도 추출값도 없을 때 최소 기본값
        return {"revenue": [5_000_000], "cost": 2_000_000, "salary": 2_000_000, "tax_rate": 0.2}

    @kernel_function(name="generate_draft", description="재무 시뮬레이션 기반 draft 생성")
    async def generate_draft(self, question: str, retry_prompt: str = "", profile: str = "", session_vars: dict | None = None) -> str:
        # ── 1단계: 파라미터 추출 ─────────────────────────────
        variables = await self._extract_params(question, profile=profile, session_vars=session_vars)

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
        # 가정 조건 문자열 구성 — 단일 입력 vs. 복수 데이터(실제 분포) 분기
        rev = variables.get("revenue", [])
        is_multi = len(rev) > 1
        if is_multi:
            rev_line = f"- 월매출: 실제 매장 {len(rev)}개 데이터 기반 (범위: {min(rev):,}~{max(rev):,}원)"
        else:
            rev_str = f"{rev[0]:,}원" if rev else "0원"
            rev_line = f"- 월매출: {rev_str}"
        cost_line = f"- 원가: {variables.get('cost', 0):,}원"
        assumption_lines = [
            rev_line,
            cost_line,
            f"- 급여: {variables.get('salary', 0):,}원",
        ]
        if variables.get("rent"): assumption_lines.append(f"- 임대료: {variables['rent']:,}원")
        if variables.get("admin"): assumption_lines.append(f"- 관리비: {variables['admin']:,}원")
        if variables.get("fee"):   assumption_lines.append(f"- 수수료: {variables['fee']:,}원")
        assumption_lines.append(f"- 세율: {variables.get('tax_rate', 0.2):.0%}")
        assumptions = "\n".join(assumption_lines)

        # 손실확률: 핵심 지표로 명시.
        # 0%이면 서술형으로 표현 (수치 "0%"가 리스크 부정으로 오해되는 것을 방지)
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
            p5=sim_result["p5_net_profit"],
            p95=sim_result["p95_net_profit"],
            loss_prob=loss_prob_str,
            question=question,
        )
        if profile:
            explain_prompt = _PROFILE_CONTEXT.format(profile=profile) + explain_prompt
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
