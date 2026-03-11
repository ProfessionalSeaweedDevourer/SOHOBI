import asyncio
import yaml
import os
import re
from user_functions import FinanceSimulationSkill
from openai import OpenAI

# 0311_4 api키를 비롯한 .env파일 설정
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.getenv("BASE_DIR")
YAML_PATH = os.path.join(BASE_DIR, "skills", "investment-simulation.yaml")

client = OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")
)

async def call_llm(prompt: str) -> str:
    resp = client.chat.completions.create(
        model="test_model_fin",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

async def main():
    user_input = input(">>user   : ")

    # YAML 로드
    with open(YAML_PATH, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    finance_skill = FinanceSimulationSkill()

    # 1단계: 입력을 JSON으로 변환
    json_prompt = workflow["stages"][0]["prompt"].replace("{{user_input}}", user_input)
    json_variables = await call_llm(json_prompt)

    # 0311_1 코드 블록 제거
    clean_json = re.sub(r"^```json\s*|\s*```$", "", json_variables.strip(), flags=re.MULTILINE)

    # JSON → dict 변환
    variables = yaml.safe_load(clean_json)

    # 0311_2 monte_carlo_simulation에 필요한 키만 추출
    sim_keys = ["revenue", "cost", "salary", "hours", "rent", "admin", "fee", "tax_rate"]
    sim_input = {k: variables[k] for k in sim_keys if k in variables}

    # 2단계: MC simulation
    sim_result = finance_skill.monte_carlo_simulation(**sim_input)

    # 2-1: 초기 투자비용의 존재 여부에 따라 
    recovery_result = None
    if "initial_investment" in variables:
        recovery_result = finance_skill.investment_recovery(
            initial_investment=variables["initial_investment"],
            avg_profit=sim_result["average_net_profit"]
        )

    # 3단계: explain_result
    explain_prompt = workflow["stages"][2]["prompt"] \
        .replace("{{simulation_result.average_net_profit}}", str(sim_result["average_net_profit"])) \
        .replace("{{simulation_result.loss_probability}}", str(sim_result["loss_probability"]))
    final_explanation = await call_llm(explain_prompt)

    recovery_prompt = workflow["stages"][3]["prompt"] \
        .replace("{{recovery_result.recoverable}}", str(recovery_result["recoverable"])) \
        .replace("{{recovery_result.months}}", str(recovery_result["months"]))
    recovery_explanation = await call_llm(recovery_prompt)

    print("\n>>agent  : ")
    print(final_explanation)

    # 0311_0 초기 투자비용이 있을 때만 출력
    if recovery_result and recovery_result.get("recoverable") and recovery_result.get("months") is not None:
        print(recovery_explanation)

if __name__ == "__main__":
    asyncio.run(main())