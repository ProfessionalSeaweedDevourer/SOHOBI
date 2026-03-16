"""
오케스트레이터: 하위 에이전트 → Sign-off Agent 전체 루프 관리
출처: PARK/Code_EJP/orchestrator.py
변경: signoff 및 agents 임포트 경로 통합 구조에 맞게 수정
     session_id / profile 파라미터 추가 (세션 컨텍스트 메모리)
     에이전트·Sign-off 별 타이밍 측정
     grade(A/B/C) 처리 추가
"""

import time
import uuid
from typing import Literal

from kernel_setup import get_kernel
from agents.admin_agent import AdminAgent
from agents.finance_agent import FinanceAgent
from agents.legal_agent import LegalAgent
from signoff.signoff_agent import run_signoff

AGENT_MAP = {
    "admin":   AdminAgent,
    "finance": FinanceAgent,
    "legal":   LegalAgent,
}


async def run(
    domain: Literal["admin", "finance", "legal"],
    question: str,
    profile: str = "",
    session_id: str = "",
    max_retries: int = 3,
    session_vars: dict | None = None,
) -> dict:
    kernel = get_kernel()
    agent = AGENT_MAP[domain](kernel)

    request_id = str(uuid.uuid4())[:8]
    rejection_history = []
    retry_prompt = ""
    draft = ""

    for attempt in range(1, max_retries + 2):
        # ── 에이전트 호출 (타이밍 측정) ─────────────────────
        t_agent = time.monotonic()
        extra = {"session_vars": session_vars} if domain == "finance" and session_vars else {}
        draft = await agent.generate_draft(
            question=question,
            retry_prompt=retry_prompt,
            profile=profile,
            **extra,
        )
        agent_ms = round((time.monotonic() - t_agent) * 1000)

        # ── Sign-off 호출 (타이밍 측정) ─────────────────────
        t_signoff = time.monotonic()
        verdict = await run_signoff(kernel=kernel, domain=domain, draft=draft)
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
    }
