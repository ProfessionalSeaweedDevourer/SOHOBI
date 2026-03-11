"""
재무 시뮬레이션 에이전트 (독립 실행용)
CHANG/skills/investment-simulation.yaml 워크플로우를 Semantic Kernel로 구현.

Python 3.12 / semantic-kernel 1.40.0 기준
수정 사항:
  - 날것의 OpenAI 클라이언트 → SK AzureChatCompletion
  - BASE_DIR None 안전 처리
  - yaml.safe_load(JSON) → json.loads
  - import os 중복 제거
"""

import asyncio
import json
import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.contents import ChatHistory

from user_functions import FinanceSimulationSkill

load_dotenv()

# ── 커널 초기화 ───────────────────────────────────────────────
_kernel = Kernel()
_kernel.add_service(
    AzureChatCompletion(
        service_id="finance",
        deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
    )
)

# ── YAML 워크플로우 로드 ──────────────────────────────────────
_BASE_DIR = Path(os.getenv("BASE_DIR", str(Path(__file__).parent)))
_YAML_PATH = _BASE_DIR / "skills" / "investment-simulation.yaml"

with _YAML_PATH.open(encoding="utf-8") as f:
    _WORKFLOW = yaml.safe_load(f)


async def _call_llm(prompt: str) -> str:
    """SK AzureChatCompletion으로 단일 프롬프트 호출."""
    service: AzureChatCompletion = _kernel.get_service("finance")
    history = ChatHistory()
    history.add_user_message(prompt)
    settings = OpenAIChatPromptExecutionSettings(temperature=0.3)
    result = await service.get_chat_message_content(history, settings=settings)
    return str(result)


async def main() -> None:
    user_input = input(">>user   : ")
    skill = FinanceSimulationSkill()
    stages = _WORKFLOW["stages"]

    # ── 1단계: 자연어 → JSON 파라미터 추출 ───────────────────
    json_prompt = stages[0]["prompt"].replace("{{user_input}}", user_input)
    raw_json = await _call_llm(json_prompt)

    # 코드 블록 마커 제거
    clean_json = re.sub(r"^```json\s*|\s*```$", "", raw_json.strip(), flags=re.MULTILINE)
    variables: dict = json.loads(clean_json)

    # ── 2단계: 몬테카를로 시뮬레이션 ─────────────────────────
    sim_keys = ["revenue", "cost", "salary", "hours", "rent", "admin", "fee", "tax_rate"]
    sim_input = {k: variables[k] for k in sim_keys if k in variables}
    sim_result = skill.monte_carlo_simulation(**sim_input)

    recovery_result: dict | None = None
    if "initial_investment" in variables:
        recovery_result = skill.investment_recovery(
            initial_investment=variables["initial_investment"],
            avg_profit=sim_result["average_net_profit"],
        )

    # ── 3단계: 시뮬레이션 결과 설명 ──────────────────────────
    explain_prompt = (
        stages[2]["prompt"]
        .replace("{{simulation_result.average_net_profit}}", str(sim_result["average_net_profit"]))
        .replace("{{simulation_result.loss_probability}}", str(sim_result["loss_probability"]))
    )
    final_explanation = await _call_llm(explain_prompt)

    print("\n>>agent  :")
    print(final_explanation)

    # ── 4단계: 투자 회수 설명 (초기 투자금 있을 때만) ─────────
    if recovery_result and recovery_result.get("recoverable") and recovery_result.get("months"):
        recovery_prompt = (
            stages[3]["prompt"]
            .replace("{{recovery_result.recoverable}}", str(recovery_result["recoverable"]))
            .replace("{{recovery_result.months}}", str(recovery_result["months"]))
        )
        recovery_explanation = await _call_llm(recovery_prompt)
        print(recovery_explanation)


if __name__ == "__main__":
    asyncio.run(main())
