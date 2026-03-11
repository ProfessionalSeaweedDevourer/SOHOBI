import asyncio
import json
import sys
from pathlib import Path

# OUTDATED/ 하위에서 실행 시 부모(Code_EJP/)를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory
from kernel_setup import get_kernel

kernel = get_kernel()

SYSTEM_PROMPT = """
당신은 AI 에이전트 응답의 품질을 검증하는 Sign-off Agent입니다.

[평가 규칙 — 반드시 준수]
1. 아래 루브릭의 모든 항목 C1, C2, C3, C4, C5를 반드시 평가해야 한다.
   평가가 끝난 후 스스로 점검하라: passed 배열과 issues 배열을 합쳤을 때
   C1, C2, C3, C4, C5가 모두 정확히 한 번씩 포함되어 있는가?
   하나라도 빠져 있으면 출력하지 말고 다시 평가하라.
2. 각 항목은 반드시 "passed" 배열 또는 "issues" 배열 중 하나에 포함되어야 한다.
3. 단 하나의 항목이라도 issues에 포함되면 approved는 false여야 한다.
4. 판단이 애매한 경우 issues로 분류하고 이유를 구체적으로 기술하라.
5. approved가 false인 경우 retry_prompt는 반드시 비어 있지 않아야 한다.
   issues의 각 항목을 해결하기 위한 구체적인 수정 지시문을 작성하라.

[L1 공통 루브릭]
- C1 질문 응답성: 사용자 질문에 실질적으로 답하고 있는가
- C2 완결성: 답변이 중간에 끊기지 않고 완전한가
- C3 내부 일관성: 답변 내 수치·사실이 서로 모순되지 않는가
- C4 톤 적절성: 공식적이고 신뢰할 수 있는 어조인가
- C5 할루시네이션 징후 부재: 불확실한 사실을 단정하고 있지는 않은가.
         특히 수치(기간·금액·비율), 법령 조항, 서류 목록을 단정적으로 기술하면 위반이다.

[출력 형식 — JSON만 출력, 다른 텍스트 절대 금지]
{
  "approved": true/false,
  "passed": ["통과한 항목 코드"],
  "issues": [{"code": "실패 코드", "reason": "구체적 이유"}],
  "retry_prompt": "재작업 지시문 (approved=true이면 빈 문자열)"
}
"""

MOCK_DRAFT = """
[사용자 질문]
식품 가게를 창업하려고 하는데 영업신고는 어떻게 하나요?

[에이전트 응답]
식품영업신고는 영업 시작 전에 관할 구청 위생과에 신고해야 합니다.
필요 서류는 신분증, 영업장 도면, 위생교육 이수증입니다.
신고 후 약 3일 내에 신고증이 발급됩니다.
"""


async def run_signoff():
    chat_service = kernel.get_service("sign_off")

    history = ChatHistory()
    history.add_system_message(SYSTEM_PROMPT)
    history.add_user_message(f"다음 draft를 평가하십시오:\n\n{MOCK_DRAFT}")

    settings = AzureChatPromptExecutionSettings(
        response_format={"type": "json_object"}
    )

    result = await chat_service.get_chat_message_content(
        chat_history=history,
        settings=settings,
    )

    verdict = json.loads(str(result))
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    validate_verdict(verdict)
    return verdict


def validate_verdict(verdict: dict) -> None:
    required_codes = {"C1", "C2", "C3", "C4", "C5"}

    passed_set = set(verdict.get("passed", []))
    issues_set = {i["code"] for i in verdict.get("issues", [])}

    # 1. 모든 항목이 평가됐는지
    evaluated = passed_set | issues_set
    missing = required_codes - evaluated
    assert not missing, f"누락된 평가 항목: {missing}"

    # 2. 중복 분류 없는지
    overlap = passed_set & issues_set
    assert not overlap, f"passed와 issues에 동시에 분류된 항목: {overlap}"

    # 3. approved=false면 retry_prompt 필수
    if not verdict["approved"]:
        assert verdict.get("retry_prompt"), \
            "approved=false인데 retry_prompt가 비어 있음"

    # 4. issues가 있으면 approved는 반드시 false
    if issues_set:
        assert not verdict["approved"], \
            "issues가 존재하는데 approved=true로 설정됨"

    print("검증 통과!")


asyncio.run(run_signoff())
