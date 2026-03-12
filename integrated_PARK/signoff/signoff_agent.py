"""
Sign-off Agent: 하위 에이전트 draft의 품질을 판정한다.
출처: PARK/Code_EJP/step3_domain_signoff.py
"""

import json
import re
from pathlib import Path

from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

REQUIRED_CODES = {
    "admin":   {"C1", "C2", "C3", "C4", "C5", "A1", "A2", "A3", "A4", "A5"},
    "finance": {"C1", "C2", "C3", "C4", "C5", "F1", "F2", "F3", "F4", "F5"},
    "legal":   {"C1", "C2", "C3", "C4", "C5", "G1", "G2", "G3", "G4"},
}


def _build_history(domain: str, draft: str) -> ChatHistory:
    prompt_file = PROMPTS_DIR / f"signoff_{domain}" / "evaluate" / "skprompt.txt"
    raw = prompt_file.read_text(encoding="utf-8").replace("{{$draft}}", draft)

    history = ChatHistory()
    for m in re.finditer(r'<message role="(\w+)">(.*?)</message>', raw, re.DOTALL):
        role, content = m.group(1), m.group(2).strip()
        if role == "system":
            history.add_system_message(content)
        elif role == "user":
            history.add_user_message(content)
    return history


async def run_signoff(kernel, domain: str, draft: str, max_retries: int = 2) -> dict:
    required_codes = REQUIRED_CODES[domain]
    chat_service = kernel.get_service("sign_off")
    settings = AzureChatPromptExecutionSettings(
        response_format={"type": "json_object"}
    )
    history = _build_history(domain, draft)

    for attempt in range(max_retries + 1):
        result = await chat_service.get_chat_message_content(
            chat_history=history,
            settings=settings,
        )
        verdict = json.loads(str(result))

        passed_set = set(verdict.get("passed", []))
        issues_set = {i["code"] for i in verdict.get("issues", [])}
        missing = required_codes - (passed_set | issues_set)

        if not missing:
            return verdict

        if attempt < max_retries:
            missing_list = ", ".join(sorted(missing))
            history.add_assistant_message(str(result))
            history.add_user_message(
                f"다음 항목이 passed 또는 issues에 누락되어 있습니다: {missing_list}\n"
                f"이 항목들을 포함하여 전체 평가를 다시 JSON 형식으로 출력하십시오."
            )

    return verdict


def validate_verdict(verdict: dict, domain: str) -> None:
    required_codes = REQUIRED_CODES[domain]
    passed_set = set(verdict.get("passed", []))
    issues_set = {i["code"] for i in verdict.get("issues", [])}

    missing = required_codes - (passed_set | issues_set)
    assert not missing, f"누락된 평가 항목: {missing}"

    overlap = passed_set & issues_set
    assert not overlap, f"passed와 issues에 동시에 분류된 항목: {overlap}"

    if not verdict["approved"]:
        assert verdict.get("retry_prompt"), "approved=false인데 retry_prompt가 비어 있음"

    if issues_set:
        assert not verdict["approved"], "issues가 존재하는데 approved=true로 설정됨"

    if not issues_set:
        assert verdict["approved"], "issues가 없는데 approved=false로 설정됨"
