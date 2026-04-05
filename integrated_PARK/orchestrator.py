"""
오케스트레이터: 하위 에이전트 → Sign-off Agent 전체 루프 관리
출처: PARK/Code_EJP/orchestrator.py
변경: signoff 및 agents 임포트 경로 통합 구조에 맞게 수정
     session_id / profile 파라미터 추가 (세션 컨텍스트 메모리)
     에이전트·Sign-off 별 타이밍 측정
     grade(A/B/C) 처리 추가
     run_stream(): SSE 스트리밍용 async generator 추가
"""

import time
import uuid
from typing import AsyncGenerator, Literal

from kernel_setup import get_kernel, get_signoff_client
from agents.admin_agent import AdminAgent
from agents.finance_agent import FinanceAgent
from agents.legal_agent import LegalAgent
from agents.location_agent import LocationAgent
from signoff.signoff_agent import run_signoff
from checklist_store import auto_check_items as _auto_check

AGENT_MAP = {
    "admin":    AdminAgent,
    "finance":  FinanceAgent,
    "legal":    LegalAgent,
    "location": LocationAgent,
}


async def run(
    domain: Literal["admin", "finance", "legal", "location", "chat"],
    question: str,
    profile: str = "",
    session_id: str = "",
    prior_history: list[dict] | None = None,
    max_retries: int = 3,
    current_params: dict | None = None,
    context: dict | None = None,
) -> dict:
    kernel = get_kernel()

    # ── chat 도메인: SignOff 없이 즉시 반환 ──────────────────
    if domain == "chat":
        from agents.chat_agent import ChatAgent
        t0 = time.monotonic()
        draft = await ChatAgent(kernel).generate_draft(
            question=question,
            profile=profile,
            prior_history=prior_history,
        )
        return {
            "status":            "approved",
            "grade":             "A",
            "confidence_note":   "",
            "retry_count":       0,
            "request_id":        str(uuid.uuid4())[:8],
            "session_id":        session_id,
            "agent_ms":          round((time.monotonic() - t0) * 1000),
            "signoff_ms":        0,
            "message":           "",
            "rejection_history": [],
            "draft":             draft,
            "chart":             None,
            "updated_params":    None,
            "adm_codes":         [],
            "analysis_type":     "",
        }

    signoff_client = get_signoff_client()
    agent = AGENT_MAP[domain](kernel)

    request_id = str(uuid.uuid4())[:8]
    rejection_history = []
    retry_prompt = ""
    draft = ""
    prev_draft = None

    chart = None
    updated_params = None
    adm_codes: list = []
    analysis_type: str = ""
    updated_context: dict | None = None

    for attempt in range(1, max_retries + 2):
        # ── 에이전트 호출 (타이밍 측정) ─────────────────────
        t_agent = time.monotonic()
        extra: dict = {}
        if domain == "finance" and current_params:
            extra["current_params"] = current_params
        if context:
            extra["context"] = context
        raw = await agent.generate_draft(
            question=question,
            retry_prompt=retry_prompt,
            profile=profile,
            prior_history=prior_history,
            **extra,
        )
        agent_ms = round((time.monotonic() - t_agent) * 1000)

        # finance/location 에이전트는 dict를 반환
        if isinstance(raw, dict):
            draft = raw.get("draft", "")
            chart = raw.get("chart")                    # finance: 단일 chart dict
            charts = raw.get("charts", []) or []        # location: 차트 list (CHOI)
            updated_params = raw.get("updated_params")
            adm_codes = raw.get("adm_codes", [])
            analysis_type = raw.get("type", "")
            # location agent가 반환한 지역·업종으로 context 갱신
            if domain == "location" and adm_codes:
                updated_context = dict(context) if context else {}
                updated_context["adm_codes"]     = adm_codes
                updated_context["business_type"] = raw.get("business_type", updated_context.get("business_type", ""))
                updated_context["location_name"] = raw.get("location_name", updated_context.get("location_name", ""))
        else:
            draft = raw
            charts = []

        # 이전 attempt와 draft가 동일하면 재시도해도 개선 불가 → 조기 종료
        if draft == prev_draft:
            break
        prev_draft = draft

        # ── Sign-off 호출 (타이밍 측정) ─────────────────────
        t_signoff = time.monotonic()
        verdict = await run_signoff(client=signoff_client, domain=domain, draft=draft)
        signoff_ms = round((time.monotonic() - t_signoff) * 1000)

        # issues 없이 approved=false → 모델 논리 오류, 강제 통과
        if not verdict.get("issues") and not verdict.get("approved"):
            verdict["approved"] = True
            verdict["grade"] = "A"

        grade = verdict.get("grade", "A" if verdict.get("approved") else "C")

        if verdict["approved"]:
            checked_ids: list[str] = []
            if session_id and draft:
                try:
                    checked_ids = await _auto_check(session_id, draft)
                except Exception:
                    pass
            return {
                "status":           "approved",
                "grade":            grade,
                "confidence_note":  verdict.get("confidence_note", ""),
                "retry_count":      attempt - 1,
                "request_id":       request_id,
                "session_id":       session_id,
                "agent_ms":         agent_ms,
                "signoff_ms":       signoff_ms,
                "message":          "",
                "rejection_history": rejection_history,
                "draft":            draft,
                "chart":            chart,
                "charts":           charts,
                "updated_params":   updated_params,
                "adm_codes":        adm_codes,
                "analysis_type":    analysis_type,
                "updated_context":  updated_context,
                "checked_items":    checked_ids,
            }

        rejection_history.append({
            "attempt": attempt,
            "verdict": verdict,
            "agent_ms": agent_ms,
            "signoff_ms": signoff_ms,
        })
        retry_prompt = verdict.get("retry_prompt", "")

        if attempt > max_retries:
            break

    actual_retries = len(rejection_history)
    last_reason = rejection_history[-1]["verdict"].get("retry_prompt", "") if rejection_history else ""
    esc_checked_ids: list[str] = []
    if session_id and draft:
        try:
            esc_checked_ids = await _auto_check(session_id, draft)
        except Exception:
            pass
    return {
        "status":           "escalated",
        "grade":            "C",
        "confidence_note":  "",
        "retry_count":      actual_retries,
        "request_id":       request_id,
        "session_id":       session_id,
        "agent_ms":         0,
        "signoff_ms":       0,
        "message":          f"재시도 {actual_retries}회 초과. 마지막 거부 이유: {last_reason}",
        "rejection_history": rejection_history,
        "draft":            draft,
        "chart":            chart,
        "charts":           charts,
        "updated_params":   updated_params,
        "adm_codes":        adm_codes,
        "analysis_type":    analysis_type,
        "updated_context":  updated_context,
        "checked_items":    esc_checked_ids,
    }


async def run_stream(
    domain: Literal["admin", "finance", "legal", "location", "chat"],
    question: str,
    profile: str = "",
    session_id: str = "",
    prior_history: list[dict] | None = None,
    max_retries: int = 3,
    current_params: dict | None = None,
    context: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """SSE 스트리밍용 async generator.
    각 단계마다 event dict를 yield한다.

    이벤트 종류:
      agent_start    — 에이전트 호출 시작
      agent_done     — 에이전트 draft 완료
      signoff_start  — Sign-off 호출 시작
      signoff_result — Sign-off 판정 결과 (통과/반려)
      complete       — 전체 완료 (최종 결과 포함)
      error          — 예외 발생
    """
    kernel = get_kernel()

    # ── chat 도메인: SignOff 없이 즉시 complete yield ────────
    if domain == "chat":
        from agents.chat_agent import ChatAgent
        yield {"event": "agent_start", "attempt": 1, "max_attempts": 1}
        t0 = time.monotonic()
        draft = await ChatAgent(kernel).generate_draft(
            question=question,
            profile=profile,
            prior_history=prior_history,
        )
        agent_ms = round((time.monotonic() - t0) * 1000)
        rid = str(uuid.uuid4())[:8]
        yield {"event": "agent_done", "attempt": 1, "agent_ms": agent_ms}
        yield {
            "event":             "complete",
            "status":            "approved",
            "grade":             "A",
            "confidence_note":   "",
            "retry_count":       0,
            "request_id":        rid,
            "session_id":        session_id,
            "agent_ms":          agent_ms,
            "signoff_ms":        0,
            "message":           "",
            "rejection_history": [],
            "draft":             draft,
            "chart":             None,
            "updated_params":    None,
            "adm_codes":         [],
            "analysis_type":     "",
        }
        return

    signoff_client = get_signoff_client()
    agent = AGENT_MAP[domain](kernel)

    request_id = str(uuid.uuid4())[:8]
    rejection_history = []
    retry_prompt = ""
    draft = ""
    prev_draft = None
    chart = None
    charts: list = []
    updated_params = None
    adm_codes: list = []
    analysis_type: str = ""
    updated_context: dict | None = None

    for attempt in range(1, max_retries + 2):
        yield {"event": "agent_start", "attempt": attempt, "max_attempts": max_retries + 1}

        t_agent = time.monotonic()
        extra: dict = {}
        if domain == "finance" and current_params:
            extra["current_params"] = current_params
        if context:
            extra["context"] = context
        raw = await agent.generate_draft(
            question=question,
            retry_prompt=retry_prompt,
            profile=profile,
            prior_history=prior_history,
            **extra,
        )
        agent_ms = round((time.monotonic() - t_agent) * 1000)

        if isinstance(raw, dict):
            draft = raw.get("draft", "")
            chart = raw.get("chart")                    # finance: 단일 chart dict
            charts = raw.get("charts", []) or []        # location: 차트 list (CHOI)
            updated_params = raw.get("updated_params")
            adm_codes = raw.get("adm_codes", [])
            analysis_type = raw.get("type", "")
            if domain == "location" and adm_codes:
                updated_context = dict(context) if context else {}
                updated_context["adm_codes"]     = adm_codes
                updated_context["business_type"] = raw.get("business_type", updated_context.get("business_type", ""))
                updated_context["location_name"] = raw.get("location_name", updated_context.get("location_name", ""))
        else:
            draft = raw
            charts = []

        if draft == prev_draft:
            break
        prev_draft = draft

        yield {"event": "agent_done", "attempt": attempt, "agent_ms": agent_ms}

        yield {"event": "signoff_start", "attempt": attempt}

        t_signoff = time.monotonic()
        verdict = await run_signoff(client=signoff_client, domain=domain, draft=draft)
        signoff_ms = round((time.monotonic() - t_signoff) * 1000)

        if not verdict.get("issues") and not verdict.get("approved"):
            verdict["approved"] = True
            verdict["grade"] = "A"

        grade = verdict.get("grade", "A" if verdict.get("approved") else "C")

        yield {
            "event":        "signoff_result",
            "attempt":      attempt,
            "approved":     verdict["approved"],
            "grade":        grade,
            "passed":       verdict.get("passed", []),
            "issues":       verdict.get("issues", []),
            "warnings":     verdict.get("warnings", []),
            "retry_prompt": verdict.get("retry_prompt", ""),
            "signoff_ms":   signoff_ms,
        }

        if verdict["approved"]:
            stream_checked_ids: list[str] = []
            if session_id and draft:
                try:
                    stream_checked_ids = await _auto_check(session_id, draft)
                except Exception:
                    pass
            yield {
                "event":            "complete",
                "status":           "approved",
                "grade":            grade,
                "confidence_note":  verdict.get("confidence_note", ""),
                "retry_count":      attempt - 1,
                "request_id":       request_id,
                "session_id":       session_id,
                "agent_ms":         agent_ms,
                "signoff_ms":       signoff_ms,
                "message":          "",
                "rejection_history": rejection_history,
                "draft":            draft,
                "chart":            chart,
                "charts":           charts,
                "updated_params":   updated_params,
                "adm_codes":        adm_codes,
                "analysis_type":    analysis_type,
                "updated_context":  updated_context,
                "checked_items":    stream_checked_ids,
            }
            return

        rejection_history.append({
            "attempt":    attempt,
            "verdict":    verdict,
            "agent_ms":   agent_ms,
            "signoff_ms": signoff_ms,
        })
        retry_prompt = verdict.get("retry_prompt", "")

        if attempt > max_retries:
            break

    actual_retries = len(rejection_history)
    stream_esc_checked_ids: list[str] = []
    if session_id and draft:
        try:
            stream_esc_checked_ids = await _auto_check(session_id, draft)
        except Exception:
            pass
    yield {
        "event":            "complete",
        "status":           "escalated",
        "grade":            "C",
        "confidence_note":  "",
        "retry_count":      actual_retries,
        "request_id":       request_id,
        "session_id":       session_id,
        "agent_ms":         0,
        "signoff_ms":       0,
        "message":          f"재시도 {actual_retries}회 초과.",
        "rejection_history": rejection_history,
        "draft":            draft,
        "chart":            chart,
        "charts":           charts,
        "updated_params":   updated_params,
        "adm_codes":        adm_codes,
        "analysis_type":    analysis_type,
        "updated_context":  updated_context,
        "checked_items":    stream_esc_checked_ids,
    }
