# python step3_domain_signoff_enhanced.py pass   # PASS 케이스만
# python step3_domain_signoff_enhanced.py fail   # FAIL 케이스만
# python step3_domain_signoff_enhanced.py both   # 기본값, 둘 다

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import semantic_kernel as sk
from dotenv import load_dotenv
from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureChatPromptExecutionSettings

load_dotenv()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

REQUIRED_CODES = {
    "admin":   {"C1", "C2", "C3", "C4", "C5", "A1", "A2", "A3", "A4", "A5"},
    "finance": {"C1", "C2", "C3", "C4", "C5", "F1", "F2", "F3", "F4", "F5"},
    "legal":   {"C1", "C2", "C3", "C4", "C5", "G1", "G2", "G3", "G4"},
}

# ─────────────────────────────────────────────────────────────
# MOCK_DRAFTS_FAIL : 기존 불완전 draft (approved=false 검증용)
# MOCK_DRAFTS_PASS : 완성도 높은 draft (approved=true 검증용)
# ─────────────────────────────────────────────────────────────

MOCK_DRAFTS_FAIL = {
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
대출 한도는 최대 5억 원이며 원금 손실 없이 안정적으로 이용하실 수 있습니다.
""",
    "legal": """
[사용자 질문]
임대차 계약 만료 후 집주인이 보증금을 돌려주지 않으면 어떻게 하나요?

[에이전트 응답]
주택임대차보호법 제3조에 따라 임차인은 보증금 반환을 청구할 권리가 있습니다.
즉시 내용증명을 보내고 임차권등기명령을 신청하면 보증금을 반드시 돌려받을 수 있습니다.
""",
}

MOCK_DRAFTS_PASS = {
    "admin": """
[사용자 질문]
식품 가게를 창업하려고 하는데 영업신고는 어떻게 하나요?

[에이전트 응답]
식품위생법 관련 규정에 따라 식품영업을 시작하기 전에 영업신고 절차를 완료하는 것이 요구됩니다.
관련 법령은 식품위생법 제37조이며, 신고 시 식품의약품안전처에서 지정한 신고서 양식을 사용합니다.
정확한 서식 번호와 양식명은 관할 구청 위생과 또는 정부24(www.gov.kr)에서 확인하시기 바랍니다.

절차는 아래 순서로 진행됩니다.
1단계: 위생교육 이수 — 영업신고 전 식품위생법에 따른 사전 위생교육을 이수합니다.
2단계: 서류 준비 — 영업신고서, 영업장 평면도, 위생교육 이수증, 임대차 계약서(해당 시)를 준비합니다.
3단계: 접수 — 영업장 소재지 관할 시·군·구청 위생과(또는 식품위생과)에 방문 또는 정부24를 통해 온라인으로 접수합니다.
4단계: 검토 및 발급 — 담당 공무원 검토 후 영업신고증이 발급됩니다. 처리 기간은 통상 3~7영업일이며, 관할 기관 및 시기에 따라 달라질 수 있습니다.

업종(일반음식점, 휴게음식점 등)에 따라 요구 서류와 시설 기준이 다를 수 있으므로, 신고 전 관할 구청 위생과에 사전 문의하시기 바랍니다.
""",

    "finance": """
[사용자 질문]
소규모 카페 창업 시 초기 6개월 재무 시뮬레이션을 보여주세요. 초기 투자금은 5,000만 원입니다.

[에이전트 응답]
아래 시뮬레이션은 다음 가정을 전제로 합니다.
- 초기 투자금: 5,000만 원 (보증금 1,500만 원, 인테리어·설비 2,500만 원, 운영 예비금 1,000만 원)
- 대출 없음 (자기자본 100% 구조 가정)
- 기본 시나리오 월 매출: 750만 원 (서울 도심 소규모 카페 20석 이하 기준 추정 중간값)
- 금리 영향 없음 (자기자본 구조이므로 이자 비용 미발생)

기본 시나리오 월 비용 구조 (단위: 원)
- 임차료: 1,500,000원
- 원재료비 (매출의 30%): 2,250,000원
- 인건비: 1,500,000원
- 기타 고정비: 500,000원
- 합계: 5,750,000원

월 순이익 (세전): 7,500,000원 - 5,750,000원 = 1,750,000원
6개월 누적 순이익 추정: 약 10,500,000원
초기 투자금 회수 예상 기간: 약 28~30개월

시나리오별 신뢰 구간
- 낙관 (월 매출 10,000,000원): 월 순이익 약 2,750,000원, 회수 기간 약 18개월
- 기본 (월 매출 7,500,000원): 월 순이익 약 1,750,000원, 회수 기간 약 28개월
- 비관 (월 매출 6,000,000원): 월 순이익 약 850,000원, 회수 기간 약 49개월 이상

[리스크 경고] 위 수치는 가정 기반 추정치로 실제 결과와 다를 수 있습니다. 입지, 경쟁 환경, 계절 변동, 임차료 인상, 원재료 가격 변동 등 외부 변수에 따라 손실이 발생할 수 있습니다. 투자 전 세무사 또는 창업 전문가와의 개별 상담을 권장합니다.
""",

    "legal": """
[사용자 질문]
임대차 계약 만료 후 집주인이 보증금을 돌려주지 않으면 어떻게 하나요?

[에이전트 응답]
[안내 사항] 본 응답은 법적 조언이 아닌 일반적인 정보 제공 목적으로 작성되었습니다.
아래 내용은 본 응답 작성 시점 기준 시행 법령을 참고하였으며, 이후 법령 개정 가능성이 있습니다.
개별 사안에 따라 결과가 달라질 수 있으므로, 구체적인 조치 전 변호사 또는 법률구조공단(국번 없이 132)에 상담하시기 바랍니다.

임대차 계약 만료 후 임대인이 보증금을 반환하지 않는 경우 아래 절차를 고려하실 수 있습니다.

1단계 — 내용증명 발송: 보증금 반환을 서면으로 공식 요청합니다. 직접적인 법적 효력은 없으나 향후 분쟁 시 의사 표시 증거로 활용됩니다.

2단계 — 임차권등기명령 신청: 주택임대차보호법 제3조의3에 따라 계약 종료 후 보증금을 반환받지 못한 경우 관할 지방법원에 임차권등기명령을 신청할 수 있습니다. 등기 완료 시 이사 후에도 대항력과 우선변제권이 유지될 수 있습니다. 다만 이것이 보증금 반환을 보장하지는 않으며, 임대인의 재산 상태 등에 따라 실제 회수 여부가 달라질 수 있습니다.

3단계 — 지급명령 또는 소액사건심판: 보증금 규모에 따라 소액사건심판 또는 지급명령 절차를 활용할 수 있습니다.

4단계 — 전세보증금반환보증 청구: 해당 보험에 가입한 경우 주택도시보증공사(HUG) 또는 SGI서울보증에 청구할 수 있습니다(주택임대차보호법 제6조의2 참조).
""",
}

kernel = sk.Kernel()
kernel.add_service(
    AzureChatCompletion(
        service_id="sign_off",
        deployment_name=os.getenv("AZURE_ENHANCED_DEPLOYMENT_NAME"),
        endpoint=os.getenv("AZURE_ENHANCED_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
    )
)


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
            print(f"  [재시도 {attempt + 1}] 누락 항목: {missing_list}")
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

    print("  검증 통과!")


async def run_suite(drafts: dict, label: str) -> None:
    """drafts 딕셔너리의 모든 도메인을 순서대로 실행한다."""
    print(f"\n{'#' * 60}")
    print(f"  {label}")
    print(f"{'#' * 60}")

    for domain, draft in drafts.items():
        print(f"\n{'=' * 50}")
        print(f"  도메인: {domain.upper()}")
        print("=" * 50)

        verdict = await run_signoff(domain, draft)
        approved_str = "✅ APPROVED" if verdict["approved"] else "❌ REJECTED"
        print(f"  판정: {approved_str}")
        print(json.dumps(verdict, ensure_ascii=False, indent=2))

        try:
            validate_verdict(verdict, domain)
        except AssertionError as e:
            print(f"  검증 실패: {e}")


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    if mode == "fail":
        await run_suite(MOCK_DRAFTS_FAIL, "[ FAIL 케이스 — 불완전 draft ]")
    elif mode == "pass":
        await run_suite(MOCK_DRAFTS_PASS, "[ PASS 케이스 — 완성도 높은 draft ]")
    elif mode == "both":
        await run_suite(MOCK_DRAFTS_FAIL, "[ FAIL 케이스 — 불완전 draft ]")
        await run_suite(MOCK_DRAFTS_PASS, "[ PASS 케이스 — 완성도 높은 draft ]")
    else:
        print("사용법: python step3_domain_signoff_enhanced.py [fail|pass|both]")
        print("  fail : 불완전 draft만 실행 (approved=false 예상)")
        print("  pass : 완성도 높은 draft만 실행 (approved=true 예상)")
        print("  both : 두 케이스 모두 실행 (기본값)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
