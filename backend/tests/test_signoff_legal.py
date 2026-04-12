"""
T-17 ~ T-19: 법령 Sign-off 루브릭 단위 테스트

Sign-off Agent는 실제 LLM을 호출하므로 AZURE_OPENAI_API_KEY가 필요합니다.
환경변수 미설정 시 전체 테스트가 skip됩니다.

실행:
    cd backend
    .venv/bin/python -m pytest tests/test_signoff_legal.py -v

루브릭 코드 (signoff_legal/evaluate/skprompt.txt):
  G1: 면책 조항 (법적 조언 아님) 존재 여부
  G2: 법령 기준 시점 / 개정 가능성 언급 여부
  G3: 전문가 상담 권고 여부
  G4: 법령명 + 조항 번호 인용 여부
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="AZURE_OPENAI_API_KEY 환경변수 미설정 — Sign-off LLM 테스트 skip",
)


# ---------------------------------------------------------------------------
# 공통 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def signoff_client():
    from kernel_setup import get_signoff_client

    return get_signoff_client()


# ---------------------------------------------------------------------------
# T-17: 법령명 미인용 시 G4 → issues, approved=false
# ---------------------------------------------------------------------------
class TestT17G4LawCitationMissing:
    """G4 루브릭: 법령명 + 조항 번호가 없는 draft는 반드시 거부되어야 합니다"""

    @pytest.mark.asyncio
    async def test_no_law_citation_fails_g4(self, signoff_client):
        from signoff.signoff_agent import run_signoff

        draft_without_law = """
본 응답은 법적 조언이 아닌 일반적인 정보 제공 목적입니다.
본 응답 작성 시점 기준 시행 법령을 참고하였으며 이후 개정될 수 있습니다.
구체적인 사안은 변호사 또는 법률구조공단(국번 없이 132)에 상담하시기 바랍니다.

임대차 계약 시 임차인은 일정한 보호를 받을 수 있습니다.
보증금 반환을 청구할 수 있으며, 계약 기간 내 임의 퇴거 요청에 대응할 수 있습니다.
        """.strip()

        verdict = await run_signoff(
            client=signoff_client,
            domain="legal",
            draft=draft_without_law,
        )

        issues_codes = [
            item["code"] if isinstance(item, dict) else item
            for item in verdict.get("issues", [])
        ]

        assert verdict["approved"] is False, (
            "법령명이 없는 draft는 approved=false여야 합니다"
        )
        assert "G4" in issues_codes, (
            f"G4(법령 인용 없음)가 issues에 포함되어야 합니다. "
            f"실제 issues: {verdict.get('issues')}"
        )
        assert verdict.get("retry_prompt"), (
            "approved=false일 때 retry_prompt가 비어 있으면 안 됩니다"
        )


# ---------------------------------------------------------------------------
# T-18: 면책조항 미포함 시 G1 → issues, approved=false
# ---------------------------------------------------------------------------
class TestT18G1DisclaimerMissing:
    """G1 루브릭: 면책 조항 표현이 없는 draft는 반드시 거부되어야 합니다"""

    @pytest.mark.asyncio
    async def test_no_disclaimer_fails_g1(self, signoff_client):
        from signoff.signoff_agent import run_signoff

        draft_without_disclaimer = """
식품위생법 제36조 제1항에 따라 음식점을 영업하려면 관할 시·군·구청에 영업신고를 해야 합니다.
영업신고 시 필요한 서류는 다음과 같습니다:
1. 영업신고서 (식품위생법 시행규칙 제42조 별지 제37호 서식)
2. 영업시설 배치도
3. 위생교육 이수증 (식품위생교육기관 발급)

신청 후 관할청에서 현장 확인을 거쳐 영업신고증을 교부합니다.
        """.strip()

        verdict = await run_signoff(
            client=signoff_client,
            domain="legal",
            draft=draft_without_disclaimer,
        )

        issues_codes = [
            item["code"] if isinstance(item, dict) else item
            for item in verdict.get("issues", [])
        ]

        assert verdict["approved"] is False, (
            "면책조항 없는 draft는 approved=false여야 합니다"
        )
        assert "G1" in issues_codes, (
            f"G1(면책조항 없음)가 issues에 포함되어야 합니다. "
            f"실제 issues: {verdict.get('issues')}"
        )

    @pytest.mark.asyncio
    async def test_no_consultation_advice_may_fail_g3(self, signoff_client):
        """G3: 전문가 상담 권고 없는 draft — G3 issues 여부 확인"""
        from signoff.signoff_agent import run_signoff

        draft_without_consultation = """
본 응답은 법적 조언이 아닌 일반적인 정보 제공 목적입니다.
본 응답 작성 시점 기준 시행 법령을 참고하였으며 이후 개정될 수 있습니다.

식품위생법 제36조 제1항에 따라 음식점 영업신고를 해야 합니다.
        """.strip()

        verdict = await run_signoff(
            client=signoff_client,
            domain="legal",
            draft=draft_without_consultation,
        )

        issues_codes = [
            item["code"] if isinstance(item, dict) else item
            for item in verdict.get("issues", [])
        ]

        # G3 없으면 issues 또는 warnings 중 하나에 포함되어야 함
        all_codes = issues_codes + [
            item["code"] if isinstance(item, dict) else item
            for item in verdict.get("warnings", [])
        ]
        assert "G3" in all_codes or verdict["approved"] is False, (
            "전문가 상담 권고 없는 draft는 G3 issues/warnings 또는 approved=false여야 합니다"
        )


# ---------------------------------------------------------------------------
# T-19: 완전한 응답에서 G1~G4 모두 통과
# ---------------------------------------------------------------------------
class TestT19FullCompliantDraft:
    """G1~G4 + C1~C5 모두 포함한 완전한 draft는 approved=true, grade=A 또는 B여야 합니다"""

    @pytest.mark.asyncio
    async def test_full_compliant_draft_is_approved(self, signoff_client):
        from signoff.signoff_agent import run_signoff

        full_draft = """
본 응답은 법적 조언이 아닌 일반적인 정보 제공 목적입니다.
본 응답 작성 시점 기준 시행 법령을 참고하였으며 이후 개정될 수 있습니다.
구체적인 사안은 변호사 또는 법률구조공단(국번 없이 132)에 상담하시기 바랍니다.

음식점을 영업하려면 식품위생법 제36조 제1항에 따라 관할 시·군·구청에 영업신고를 해야 합니다.

[절차]
1. 위생교육 이수 (식품위생법 제41조) — 영업 신고 전 6시간 이상 이수
2. 영업신고서 제출 (식품위생법 시행규칙 제42조, 별지 제37호 서식)
   - 필요 서류: 영업시설 배치도, 위생교육 이수증, 신분증
3. 관할청 현장 확인 후 영업신고증 교부

위생교육은 한국외식업중앙회 또는 식품의약품안전처 지정 교육기관에서 이수할 수 있습니다.
법령은 개정될 수 있으므로 최신 내용을 관할 구청 위생과에서 확인하시기 바랍니다.
        """.strip()

        verdict = await run_signoff(
            client=signoff_client,
            domain="legal",
            draft=full_draft,
        )

        assert verdict["approved"] is True, (
            f"완전한 draft는 approved=true여야 합니다. "
            f"issues: {verdict.get('issues')}, "
            f"retry_prompt: {verdict.get('retry_prompt', '')[:100]}"
        )
        assert verdict.get("grade") in ("A", "B"), (
            f"완전한 draft는 grade A 또는 B여야 합니다. 실제: {verdict.get('grade')}"
        )

    @pytest.mark.asyncio
    async def test_all_required_codes_covered(self, signoff_client):
        """Sign-off 응답에 필수 코드 15개가 모두 포함되어 있는지 확인"""
        from signoff.signoff_agent import run_signoff

        full_draft = """
본 응답은 법적 조언이 아닌 일반적인 정보 제공 목적입니다.
본 응답 작성 시점 기준 시행 법령을 참고하였으며 이후 개정될 수 있습니다.
구체적인 사안은 변호사 또는 법률구조공단(국번 없이 132)에 상담하시기 바랍니다.

상가건물임대차보호법 제10조에 따라 임차인은 계약 갱신 요구권을 행사할 수 있습니다.
갱신 요구권은 전체 임대차 기간이 10년을 초과하지 않는 범위에서 행사할 수 있습니다.
        """.strip()

        verdict = await run_signoff(
            client=signoff_client,
            domain="legal",
            draft=full_draft,
        )

        required_codes = {
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "G1",
            "G2",
            "G3",
            "G4",
            "SEC1",
            "SEC2",
            "SEC3",
            "RJ1",
            "RJ2",
            "RJ3",
        }

        all_evaluated = (
            set(verdict.get("passed", []))
            | {
                item["code"] if isinstance(item, dict) else item
                for item in verdict.get("issues", [])
            }
            | {
                item["code"] if isinstance(item, dict) else item
                for item in verdict.get("warnings", [])
            }
        )

        missing = required_codes - all_evaluated
        assert not missing, (
            f"Sign-off 응답에 다음 코드가 누락되었습니다: {missing}. "
            f"평가된 코드: {all_evaluated}"
        )
