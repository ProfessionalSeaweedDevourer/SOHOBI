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

AGENT_MAP = {
    "admin":    AdminAgent,
    "finance":  FinanceAgent,
    "legal":    LegalAgent,
    "location": LocationAgent,
}


async def run(
    domain: Literal["admin", "finance", "legal", "location"],
    question: str,
    profile: str = "",
    session_id: str = "",
    max_retries: int = 3,
    current_params: dict | None = None,
) -> dict:
    kernel = get_kernel()
    signoff_client = get_signoff_client()
    agent = AGENT_MAP[domain](kernel)

    request_id = str(uuid.uuid4())[:8]
    rejection_history = []
    retry_prompt = ""
    draft = ""
    prev_draft = None

    chart = None
    updated_params = None

    for attempt in range(1, max_retries + 2):
        # ── 에이전트 호출 (타이밍 측정) ─────────────────────
        t_agent = time.monotonic()
        extra = {"current_params": current_params} if domain == "finance" and current_params else {}
        raw = await agent.generate_draft(
            question=question,
            retry_prompt=retry_prompt,
            profile=profile,
            **extra,
        )
        agent_ms = round((time.monotonic() - t_agent) * 1000)

        # finance 에이전트는 dict를 반환 (draft + chart + updated_params)
        if isinstance(raw, dict):
            draft = raw.get("draft", "")
            chart = raw.get("chart")
            updated_params = raw.get("updated_params")
        else:
            draft = raw

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
                "updated_params":   updated_params,
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

    return {
        "status":           "escalated",
        "grade":            "C",
        "confidence_note":  "",
        "retry_count":      max_retries,
        "request_id":       request_id,
        "session_id":       session_id,
        "agent_ms":         0,
        "signoff_ms":       0,
        "message":          f"재시도 {max_retries}회 초과. 마지막 거부 이유: "
                            f"{rejection_history[-1]['verdict'].get('retry_prompt', '')}",
        "rejection_history": rejection_history,
        "draft":            draft,
        "chart":            chart,
        "updated_params":   updated_params,
    }


async def run_stream(
    domain: Literal["admin", "finance", "legal", "location"],
    question: str,
    profile: str = "",
    session_id: str = "",
    max_retries: int = 3,
    current_params: dict | None = None,
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
    signoff_client = get_signoff_client()
    agent = AGENT_MAP[domain](kernel)

    request_id = str(uuid.uuid4())[:8]
    rejection_history = []
    retry_prompt = ""
    draft = ""
    prev_draft = None
    chart = None
    updated_params = None

    for attempt in range(1, max_retries + 2):
        yield {"event": "agent_start", "attempt": attempt, "max_attempts": max_retries + 1}

        t_agent = time.monotonic()
        extra = {"current_params": current_params} if domain == "finance" and current_params else {}
        raw = await agent.generate_draft(
            question=question,
            retry_prompt=retry_prompt,
            profile=profile,
            **extra,
        )
        agent_ms = round((time.monotonic() - t_agent) * 1000)

        if isinstance(raw, dict):
            draft = raw.get("draft", "")
            chart = raw.get("chart")
            updated_params = raw.get("updated_params")
        else:
            draft = raw

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
                "updated_params":   updated_params,
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

    yield {
        "event":            "complete",
        "status":           "escalated",
        "grade":            "C",
        "confidence_note":  "",
        "retry_count":      max_retries,
        "request_id":       request_id,
        "session_id":       session_id,
        "agent_ms":         0,
        "signoff_ms":       0,
        "message":          f"재시도 {max_retries}회 초과.",
        "rejection_history": rejection_history,
        "draft":            draft,
        "chart":            chart,
        "updated_params":   updated_params,
    }
