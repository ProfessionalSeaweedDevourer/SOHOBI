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

_SECURITY_CODES = {"SEC1", "SEC2", "SEC3"}
_REJECTION_CODES = {"RJ1", "RJ2", "RJ3"}

REQUIRED_CODES = {
    "admin": {"C1", "C2", "C3", "C4", "C5", "A1", "A2", "A3", "A4", "A5"}
    | _SECURITY_CODES
    | _REJECTION_CODES,
    "finance": {"C1", "C2", "C3", "C4", "C5", "F1", "F2", "F3", "F4", "F5"}
    | _SECURITY_CODES
    | _REJECTION_CODES,
    "legal": {"C1", "C2", "C3", "C4", "C5", "G1", "G2", "G3", "G4"}
    | _SECURITY_CODES
    | _REJECTION_CODES,
    "location": {"C1", "C2", "C3", "C4", "C5", "S1", "S2", "S3", "S4", "S5"}
    | _SECURITY_CODES
    | _REJECTION_CODES,
    "chat": {"C1", "C2", "C3", "C4", "C5", "CH1", "CH2", "CH3", "CH4", "CH5"}
    | _SECURITY_CODES
    | _REJECTION_CODES,
}


_DRAFT_START = "<<<DRAFT_START>>>"
_DRAFT_END = "<<<DRAFT_END>>>"


# SEC1 결정론적 누출 패턴 — LLM 판정 전 선행 검사.
# 에이전트 프롬프트의 템플릿 라벨·SK 구조·내부 마커가 실제 응답에 그대로 나타나면
# 시스템 내부 구조가 사용자에게 노출된 것으로 간주한다.
_SEC1_LEAK_PATTERNS: list[tuple[str, str]] = [
    (r"\[사용자 질문\]", "템플릿 라벨 '[사용자 질문]' 노출"),
    (r"\[에이전트 응답\]", "템플릿 라벨 '[에이전트 응답]' 노출"),
    (r"<<<DRAFT_(?:START|END)>>>", "내부 구분자 마커 노출"),
    (r"\{\{\$[A-Za-z_]\w*\}\}", "SK 템플릿 변수 미렌더 노출"),
    (r"<message\s+role=", "SK 프롬프트 구조 태그 노출"),
    (r"skprompt\.txt", "내부 프롬프트 파일명 노출"),
]


def detect_sec1_leakage(draft: str) -> list[str]:
    """draft에서 시스템 프롬프트·템플릿 라벨 누출 패턴을 탐지한다.

    Returns:
        탐지된 누출 설명 문자열 목록 (중복 제거, 탐지 없으면 빈 리스트).
    """
    hits: list[str] = []
    for pattern, label in _SEC1_LEAK_PATTERNS:
        if re.search(pattern, draft):
            hits.append(label)
    return hits


def _enforce_sec1_issue(verdict: dict, leaks: list[str]) -> dict:
    """SEC1을 issues에 강제 배치하고 관련 필드를 보정한다 (LLM 판정 무시)."""
    reason = "; ".join(leaks)
    # 기존 passed/warnings에서 SEC1 제거
    verdict["passed"] = [c for c in verdict.get("passed", []) if c != "SEC1"]
    verdict["warnings"] = [
        w
        for w in verdict.get("warnings", [])
        if (w.get("code") if isinstance(w, dict) else w) != "SEC1"
    ]
    issues = [
        i
        for i in verdict.get("issues", [])
        if (i.get("code") if isinstance(i, dict) else i) != "SEC1"
    ]
    issues.append(
        {
            "code": "SEC1",
            "reason": f"시스템 내부 구조가 응답에 노출됨: {reason}",
        }
    )
    verdict["issues"] = issues
    verdict["approved"] = False
    verdict["grade"] = "C"
    if not verdict.get("retry_prompt"):
        verdict["retry_prompt"] = (
            "응답에서 시스템 내부 템플릿 라벨·구분자·프롬프트 구조를 모두 제거하고, "
            "사용자 질문에 대한 실제 답변 본문만 출력하십시오."
        )
    return verdict


def _build_messages(domain: str, draft: str) -> list[dict]:
    prompt_file = PROMPTS_DIR / f"signoff_{domain}" / "evaluate" / "skprompt.txt"
    # draft 내 구분자 이스케이프 — 사용자 입력이 draft에 포함될 경우 signoff 판정 인젝션 방지
    sanitized = draft.replace(_DRAFT_END, "[DRAFT_END]").replace(
        _DRAFT_START, "[DRAFT_START]"
    )
    safe_draft = f"{_DRAFT_START}\n{sanitized}\n{_DRAFT_END}"
    raw = prompt_file.read_text(encoding="utf-8").replace("{{$draft}}", safe_draft)

    messages = []
    for m in re.finditer(r'<message role="(\w+)">(.*?)</message>', raw, re.DOTALL):
        role, content = m.group(1), m.group(2).strip()
        if role in ("system", "user"):
            messages.append({"role": role, "content": content})
    return messages


# severity 무시하고 강제로 high 취급 — 사용자 안전·거절 신호
_FORCED_HIGH_CODES = _SECURITY_CODES | _REJECTION_CODES


def _issue_severity(issue) -> str:
    """issue 항목의 severity를 반환한다. 누락·미지정 시 'high' 기본값 (후방호환)."""
    if not isinstance(issue, dict):
        return "high"
    if issue.get("code") in _FORCED_HIGH_CODES:
        return "high"
    sev = issue.get("severity", "high")
    if sev not in ("high", "medium", "low"):
        return "high"
    return sev


def _derive_grade(verdict: dict) -> str:
    """issues/warnings와 severity에서 grade를 결정한다.

    C: high/medium severity issue 1개 이상 (blocking)
    B: low severity issue만 있거나 warnings 1개 이상 (non-blocking)
    A: issues·warnings 모두 없음
    """
    issues = verdict.get("issues", [])
    if issues:
        if any(_issue_severity(i) in ("high", "medium") for i in issues):
            return "C"
        return "B"
    if verdict.get("warnings"):
        return "B"
    return "A"


async def run_signoff(
    client: openai.AsyncAzureOpenAI, domain: str, draft: str, max_retries: int = 0
) -> dict:
    required_codes = REQUIRED_CODES[domain]
    deployment = os.getenv("AZURE_SIGNOFF_DEPLOYMENT")
    messages = _build_messages(domain, draft)
    # SEC1 누출은 결정론적으로 선행 탐지하고, LLM 판정 후 강제 덮어쓰기 한다.
    sec1_leaks = detect_sec1_leakage(draft)

    for attempt in range(max_retries + 1):
        response = await client.chat.completions.create(
            model=deployment,
            messages=messages,
            response_format={"type": "json_object"},
        )
        result_text = response.choices[0].message.content
        m = re.search(r"\{.*\}", result_text, re.DOTALL)
        try:
            verdict = json.loads(m.group() if m else result_text)
        except json.JSONDecodeError:
            verdict = {
                "approved": False,
                "grade": "C",
                "passed": [],
                "warnings": [],
                "issues": [],
                "retry_prompt": "응답을 JSON 형식으로만 출력하십시오",
                "confidence_note": "",
            }

        passed_set = set(verdict.get("passed", []))
        issues_set = {
            i["code"] if isinstance(i, dict) else i for i in verdict.get("issues", [])
        }
        warnings_set = {
            w["code"] if isinstance(w, dict) else w for w in verdict.get("warnings", [])
        }
        missing = required_codes - (passed_set | issues_set | warnings_set)

        if not missing:
            # grade와 approved를 확정적으로 설정한다 (LLM 출력 신뢰도 보정)
            verdict["approved"] = len(issues_set) == 0
            verdict["grade"] = _derive_grade(verdict)
            # approved=False인데 retry_prompt가 없으면 빈 문자열 방지
            if not verdict["approved"] and not verdict.get("retry_prompt"):
                verdict["retry_prompt"] = (
                    "응답 품질을 개선하십시오. 관련 법령 조항, 절차, 기관명을 구체적으로 포함하세요."
                )
            if sec1_leaks:
                verdict = _enforce_sec1_issue(verdict, sec1_leaks)
            return verdict

        if attempt < max_retries:
            missing_list = ", ".join(sorted(missing))
            messages.append({"role": "assistant", "content": result_text})
            messages.append(
                {
                    "role": "user",
                    "content": f"다음 항목이 passed, warnings, issues 중 어디에도 누락되어 있습니다: {missing_list}\n"
                    f"이 항목들을 포함하여 전체 평가를 다시 JSON 형식으로 출력하십시오.",
                }
            )

    # 최대 재시도 후에도 커버리지 미달 시 가용 verdict 반환
    issues_codes = {
        i["code"] if isinstance(i, dict) else i for i in verdict.get("issues", [])
    }
    verdict["approved"] = len(issues_codes) == 0
    verdict["grade"] = _derive_grade(verdict)
    # approved=False인데 retry_prompt가 없으면 빈 문자열 방지
    if not verdict["approved"] and not verdict.get("retry_prompt"):
        verdict["retry_prompt"] = (
            "응답 품질을 개선하십시오. 관련 법령 조항, 절차, 기관명을 구체적으로 포함하세요."
        )
    if sec1_leaks:
        verdict = _enforce_sec1_issue(verdict, sec1_leaks)
    return verdict


def validate_verdict(verdict: dict, domain: str) -> None:
    required_codes = REQUIRED_CODES[domain]
    passed_set = set(verdict.get("passed", []))
    issues_set = {i["code"] for i in verdict.get("issues", [])}
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
        assert verdict.get("retry_prompt"), (
            "approved=false인데 retry_prompt가 비어 있음"
        )

    # grade 일관성 검사 (severity 반영)
    grade = verdict.get("grade")
    if grade:
        expected = _derive_grade(verdict)
        assert grade == expected, (
            f"grade={grade}이지만 severity 기반 계산값은 {expected}"
        )
