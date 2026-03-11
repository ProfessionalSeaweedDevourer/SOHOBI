import asyncio
import json
import re
import sys
from pathlib import Path

# OUTDATED/ 하위에서 실행 시 부모(Code_EJP/)를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from kernel_setup import get_kernel

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

REQUIRED_CODES = {
    "admin":   {"C1", "C2", "C3", "C4", "C5", "A1", "A2", "A3", "A4", "A5"},
    "finance": {"C1", "C2", "C3", "C4", "C5", "F1", "F2", "F3", "F4", "F5"},
    "legal":   {"C1", "C2", "C3", "C4", "C5", "G1", "G2", "G3", "G4"},
}

MOCK_DRAFTS = {
    "admin": """
[사용자 질문]
식품 가게를 창업하려고 하는데 영업신고는 어떻게 하나요?

[에이전트 응답]
식품영업신고는 영업 시작 전에 관할 구청 위생과에 신고해야 합니다.
필요 서류는 신분증, 영업장 도면, 위생교육 이수증입니다.
신고 후 약 3일 내에 신고증이 발급됩니다.
""",
    "finance": """
[사용자 질문]
주택담보대출 금리가 어느 정도인가요?

[에이전트 응답]
현재 주택담보대출 금리는 연 3.5%입니다.
대출 한도는 최대 5억 원이며 반드시 안정적인 수익을 얻을 수 있습니다.
""",
    "legal": """
[사용자 질문]
임대차 계약 만료 후 집주인이 보증금을 돌려주지 않으면 어떻게 하나요?

[에이전트 응답]
주택임대차보호법 제3조에 따라 임차인은 보증금 반환을 청구할 권리가 있습니다.
즉시 내용증명을 보내고 임차권등기명령을 신청하면 보증금을 반드시 돌려받을 수 있습니다.
""",
}

kernel = get_kernel()


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


async def run_signoff(domain: str, draft: str, max_retries: int = 2) -> dict:
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
            print(f"[재시도 {attempt + 1}] 누락 항목: {missing_list}")
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
        assert verdict.get("retry_prompt"), \
            "approved=false인데 retry_prompt가 비어 있음"

    if issues_set:
        assert not verdict["approved"], \
            "issues가 존재하는데 approved=true로 설정됨"

    # issues가 없는데 approved=false인 경우 — 모델 논리 오류
    if not issues_set:
        assert verdict["approved"], \
            "issues가 없는데 approved=false로 설정됨 (모델 논리 오류)"

    print("검증 통과!")


async def main():
    import sys as _sys
    domain = _sys.argv[1] if len(_sys.argv) > 1 else "admin"
    if domain not in REQUIRED_CODES:
        print(f"지원 도메인: {list(REQUIRED_CODES.keys())}")
        _sys.exit(1)

    verdict = await run_signoff(domain, MOCK_DRAFTS[domain])
    print(f"\n[{domain}] 판정 결과:")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    validate_verdict(verdict, domain)


if __name__ == "__main__":
    asyncio.run(main())
