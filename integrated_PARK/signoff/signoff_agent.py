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
    "admin":    {"C1", "C2", "C3", "C4", "C5", "A1", "A2", "A3", "A4", "A5"},
    "finance":  {"C1", "C2", "C3", "C4", "C5", "F1", "F2", "F3", "F4", "F5"},
    "legal":    {"C1", "C2", "C3", "C4", "C5", "G1", "G2", "G3", "G4"},
    "location": {"C1", "C2", "C3", "C4", "C5", "S1", "S2", "S3", "S4", "S5"},
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


def _derive_grade(verdict: dict) -> str:
    """issues/warnings 배열에서 grade를 결정한다.
    C: issues 1개 이상 (blocking)
    B: issues 없음, warnings 1개 이상 (non-blocking)
    A: 둘 다 없음
    """
    if verdict.get("issues"):
        return "C"
    if verdict.get("warnings"):
        return "B"
    return "A"


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

        passed_set   = set(verdict.get("passed", []))
        issues_set   = {i["code"] for i in verdict.get("issues", [])}
        warnings_set = {w["code"] for w in verdict.get("warnings", [])}
        missing = required_codes - (passed_set | issues_set | warnings_set)

        if not missing:
            # grade와 approved를 확정적으로 설정한다 (LLM 출력 신뢰도 보정)
            verdict["approved"] = len(issues_set) == 0
            if "grade" not in verdict:
                verdict["grade"] = _derive_grade(verdict)
            return verdict

        if attempt < max_retries:
            missing_list = ", ".join(sorted(missing))
            history.add_assistant_message(str(result))
            history.add_user_message(
                f"다음 항목이 passed, warnings, issues 중 어디에도 누락되어 있습니다: {missing_list}\n"
                f"이 항목들을 포함하여 전체 평가를 다시 JSON 형식으로 출력하십시오."
            )

    # 최대 재시도 후에도 커버리지 미달 시 가용 verdict 반환
    verdict["approved"] = len({i["code"] for i in verdict.get("issues", [])}) == 0
    if "grade" not in verdict:
        verdict["grade"] = _derive_grade(verdict)
    return verdict


def validate_verdict(verdict: dict, domain: str) -> None:
    required_codes = REQUIRED_CODES[domain]
    passed_set   = set(verdict.get("passed", []))
    issues_set   = {i["code"] for i in verdict.get("issues", [])}
    warnings_set = {w["code"] for w in verdict.get("warnings", [])}

    # 모든 항목이 passed | issues | warnings 중 하나에 포함되어야 한다
    missing = required_codes - (passed_set | issues_set | warnings_set)
    assert not missing, f"누락된 평가 항목: {missing}"

    # 배열 간 중복 금지
    overlap_pi = passed_set & issues_set
    assert not overlap_pi, f"passed와 issues에 동시에 분류된 항목: {overlap_pi}"
    overlap_pw = passed_set & warnings_set
    assert not overlap_pw, f"passed와 warnings에 동시에 분류된 항목: {overlap_pw}"
    overlap_iw = issues_set & warnings_set
    assert not overlap_iw, f"issues와 warnings에 동시에 분류된 항목: {overlap_iw}"

    # issues 존재 ↔ approved=false (불변 조건)
    if issues_set:
        assert not verdict["approved"], "issues가 존재하는데 approved=true로 설정됨"
    if not issues_set:
        assert verdict["approved"], "issues가 없는데 approved=false로 설정됨"

    # approved=false인 경우 retry_prompt 필수
    if not verdict["approved"]:
        assert verdict.get("retry_prompt"), "approved=false인데 retry_prompt가 비어 있음"

    # grade 일관성 검사
    grade = verdict.get("grade")
    if grade:
        if issues_set:
            assert grade == "C", f"issues가 있는데 grade={grade}"
        elif warnings_set:
            assert grade == "B", f"warnings만 있는데 grade={grade}"
        else:
            assert grade == "A", f"issues/warnings 없는데 grade={grade}"
