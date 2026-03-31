"""
Sign-off Agent: 하위 에이전트 draft의 품질을 판정한다.
출처: PARK/Code_EJP/step3_domain_signoff.py
"""

import json
import os
import re
from pathlib import Path

import openai

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_SECURITY_CODES  = {"SEC1", "SEC2", "SEC3"}
_REJECTION_CODES = {"RJ1", "RJ2", "RJ3"}

REQUIRED_CODES = {
    "admin":    {"C1", "C2", "C3", "C4", "C5", "A1", "A2", "A3", "A4", "A5"} | _SECURITY_CODES | _REJECTION_CODES,
    "finance":  {"C1", "C2", "C3", "C4", "C5", "F1", "F2", "F3", "F4", "F5"} | _SECURITY_CODES | _REJECTION_CODES,
    "legal":    {"C1", "C2", "C3", "C4", "C5", "G1", "G2", "G3", "G4"}       | _SECURITY_CODES | _REJECTION_CODES,
    "location": {"C1", "C2", "C3", "C4", "C5", "S1", "S2", "S3", "S4", "S5"} | _SECURITY_CODES | _REJECTION_CODES,
}


_DRAFT_START = "<<<DRAFT_START>>>"
_DRAFT_END   = "<<<DRAFT_END>>>"


def _build_messages(domain: str, draft: str) -> list[dict]:
    prompt_file = PROMPTS_DIR / f"signoff_{domain}" / "evaluate" / "skprompt.txt"
    # draft 내 구분자 이스케이프 — 사용자 입력이 draft에 포함될 경우 signoff 판정 인젝션 방지
    sanitized = draft.replace(_DRAFT_END, "[DRAFT_END]").replace(_DRAFT_START, "[DRAFT_START]")
    safe_draft = f"{_DRAFT_START}\n{sanitized}\n{_DRAFT_END}"
    raw = prompt_file.read_text(encoding="utf-8").replace("{{$draft}}", safe_draft)

    messages = []
    for m in re.finditer(r'<message role="(\w+)">(.*?)</message>', raw, re.DOTALL):
        role, content = m.group(1), m.group(2).strip()
        if role in ("system", "user"):
            messages.append({"role": role, "content": content})
    return messages


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


async def run_signoff(client: openai.AsyncAzureOpenAI, domain: str, draft: str, max_retries: int = 0) -> dict:
    required_codes = REQUIRED_CODES[domain]
    deployment = os.getenv("AZURE_SIGNOFF_DEPLOYMENT")
    messages = _build_messages(domain, draft)

    for attempt in range(max_retries + 1):
        response = await client.chat.completions.create(
            model=deployment,
            messages=messages,
            response_format={"type": "json_object"},
        )
        result_text = response.choices[0].message.content
        m = re.search(r'\{.*\}', result_text, re.DOTALL)
        try:
            verdict = json.loads(m.group() if m else result_text)
        except json.JSONDecodeError:
            verdict = {
                "approved": False, "grade": "C",
                "passed": [], "warnings": [], "issues": [],
                "retry_prompt": "응답을 JSON 형식으로만 출력하십시오",
                "confidence_note": "",
            }

        passed_set   = set(verdict.get("passed", []))
        issues_set   = {i["code"] if isinstance(i, dict) else i for i in verdict.get("issues", [])}
        warnings_set = {w["code"] if isinstance(w, dict) else w for w in verdict.get("warnings", [])}
        missing = required_codes - (passed_set | issues_set | warnings_set)

        if not missing:
            # grade와 approved를 확정적으로 설정한다 (LLM 출력 신뢰도 보정)
            verdict["approved"] = len(issues_set) == 0
            if "grade" not in verdict:
                verdict["grade"] = _derive_grade(verdict)
            # approved=False인데 retry_prompt가 없으면 빈 문자열 방지
            if not verdict["approved"] and not verdict.get("retry_prompt"):
                verdict["retry_prompt"] = "응답 품질을 개선하십시오. 관련 법령 조항, 절차, 기관명을 구체적으로 포함하세요."
            return verdict

        if attempt < max_retries:
            missing_list = ", ".join(sorted(missing))
            messages.append({"role": "assistant", "content": result_text})
            messages.append({"role": "user", "content":
                f"다음 항목이 passed, warnings, issues 중 어디에도 누락되어 있습니다: {missing_list}\n"
                f"이 항목들을 포함하여 전체 평가를 다시 JSON 형식으로 출력하십시오."
            })

    # 최대 재시도 후에도 커버리지 미달 시 가용 verdict 반환
    issues_codes = {i["code"] if isinstance(i, dict) else i for i in verdict.get("issues", [])}
    verdict["approved"] = len(issues_codes) == 0
    if "grade" not in verdict:
        verdict["grade"] = _derive_grade(verdict)
    # approved=False인데 retry_prompt가 없으면 빈 문자열 방지
    if not verdict["approved"] and not verdict.get("retry_prompt"):
        verdict["retry_prompt"] = "응답 품질을 개선하십시오. 관련 법령 조항, 절차, 기관명을 구체적으로 포함하세요."
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
