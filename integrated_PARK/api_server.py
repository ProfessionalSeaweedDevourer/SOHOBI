"""
통합 API 서버
- GET  /health               — 헬스 체크
- POST /api/v1/query         — Q&A: 질문 → 도메인 라우팅 → 에이전트 → Sign-off
- POST /api/v1/signoff       — draft 단독 Sign-off 검증
- POST /api/v1/doc/chat      — 문서 생성: 대화형 정보 수집 → 식품 영업 신고서 PDF (NAM)
- GET  /api/v1/logs          — JSONL 로그 조회 (프론트엔드 로그 뷰어용)
"""

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

import domain_router
import orchestrator
from signoff.signoff_agent import run_signoff
from kernel_setup import get_kernel, get_signoff_client, _TOKEN_PROVIDER
from logger import log_query, log_error
from log_formatter import load_entries_json
from logger import _format_rejection_history
from variable_extractor import extract_financial_vars
from session_store import (
    get_query_session, save_query_session,
    get_doc_history, save_doc_history,
    get_recent_history,
)
import session_store

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await session_store.close()


app = FastAPI(title="SOHOBI Integrated API", version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 스키마 ────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., max_length=2000, description="최대 2,000자")
    session_id: str | None = Field(default=None, description="생략 시 서버가 새 UUID를 발급한다")
    founder_context: str | None = Field(
        default=None,
        description="창업자 상황 요약 (예: '서울 마포구, 자본금 1000만 원, 테이크아웃 카페'). "
                    "동일 세션에서는 최초 한 번만 전달하면 이후 요청에 자동 적용된다.",
    )
    domain: str | None = Field(default=None, description="없으면 domain_router로 자동 분류")
    max_retries: int = Field(default=3, ge=0, le=10)
    current_params: dict | None = Field(
        default=None,
        description="재무 에이전트 누적 파라미터. 이전 응답의 updated_params를 그대로 전달한다.",
    )


class SignoffRequest(BaseModel):
    domain: str = Field(description="admin | finance | legal | location")
    draft: str


class DocChatRequest(BaseModel):
    message: str
    session_id: str = Field(default="default")


# ── 보안: 프롬프트 인젝션 의심 패턴 ──────────────────────────
import re as _re

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?.*instruction",
    r"approved\s*[=:]\s*true",
    r"\{\{.*\}\}",
    r"\[SYSTEM\]",
    r"<<<",
    r"override\s+(the\s+)?rubric",
    r"evaluation\s+rule",
    r"무조건\s*(통과|승인|approved)",
    r"평가\s*(규칙|기준).*(무시|비활성|적용\s*하지)",
]

def _detect_injection(text: str) -> bool:
    """의심 패턴 감지 — 거부가 아닌 로깅 목적."""
    t = text.lower()
    return any(_re.search(p, t) for p in _INJECTION_PATTERNS)


# ── 내부 헬퍼 ─────────────────────────────────────────────────

async def _extract_and_save(sid: str, session: dict, draft: str) -> None:
    """재무 변수를 백그라운드에서 추출해 세션에 저장한다. 실패해도 메인 플로우에 영향 없음."""
    try:
        new_vars = await extract_financial_vars(draft)
        if new_vars:
            session["extracted"].update(new_vars)
            await save_query_session(sid, session)
    except Exception:
        pass


# ── 엔드포인트 ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.1.0",
        "domains": ["admin", "finance", "legal", "location"],
        "plugins": ["SeoulCommercial", "FinanceSim", "LegalSearch", "BusinessDoc"],
    }


@app.post("/api/v1/query")
async def query(req: QueryRequest):
    """Q&A 플로우: 질문 → 도메인 분류 → 에이전트(창업자 컨텍스트 주입) → Sign-off → 최종 응답"""
    t0 = time.monotonic()
    try:
        # ── 프롬프트 인젝션 의심 패턴 감지 (거부 없이 로깅만) ─
        if _detect_injection(req.question):
            import logging
            logging.getLogger("sohobi.security").warning(
                "INJECTION_SUSPECT question=%r", req.question[:200]
            )

        # ── 세션 복원 또는 신규 생성 ──────────────────────────
        sid     = req.session_id or str(uuid4())
        session = await get_query_session(sid)

        # 새 창업자 컨텍스트가 전달되면 세션 프로필 갱신
        if req.founder_context:
            session["profile"] = req.founder_context

        # ── 도메인 분류 ───────────────────────────────────────
        # 라우터는 항상 실행한다 (클라이언트 domain 지정 여부와 무관)
        classification = await domain_router.classify(req.question)
        router_domain = classification["domain"]
        router_confidence = classification.get("confidence", 0.0)

        if req.domain in ("admin", "finance", "legal", "location"):
            if router_domain != req.domain and router_confidence >= 0.8:
                import logging
                logging.getLogger("sohobi.security").warning(
                    "DOMAIN_OVERRIDE client=%r router=%r confidence=%.2f question=%r",
                    req.domain, router_domain, router_confidence, req.question[:100],
                )
                domain = router_domain   # 라우터 결과 우선
            else:
                domain = req.domain      # 라우터 확신 부족 → 클라이언트 지정 존중
        else:
            domain = router_domain

        # ── 오케스트레이터 실행 ───────────────────────────────
        # current_params: 클라이언트 전달값 우선, 없으면 서버 세션 추출값 사용
        params = req.current_params or (session["extracted"] if session["extracted"] else None)
        result = await orchestrator.run(
            domain=domain,
            question=req.question,
            profile=session["profile"],
            session_id=sid,
            prior_history=get_recent_history(session["history"]),
            max_retries=req.max_retries,
            current_params=params,
        )

        # 세션 대화 이력 누적
        session["history"].add_user_message(req.question)
        session["history"].add_assistant_message(result["draft"])

        # 세션 저장 후, 재무 변수 추출은 백그라운드에서 처리 (사용자 응답 지연 없음)
        await save_query_session(sid, session)
        if result.get("status") == "approved" and result.get("draft"):
            asyncio.create_task(_extract_and_save(sid, session, result["draft"]))

        # ── 로깅 ─────────────────────────────────────────────
        log_query(
            request_id        = result["request_id"],
            session_id        = sid,
            question          = req.question,
            domain            = domain,
            status            = result["status"],
            grade             = result.get("grade", ""),
            retry_count       = result["retry_count"],
            rejection_history = result.get("rejection_history", []),
            draft             = result["draft"],
            latency_ms        = (time.monotonic() - t0) * 1000,
        )

        return {
            "session_id":        sid,
            "request_id":        result["request_id"],
            "status":            result["status"],
            "domain":            domain,
            "grade":             result.get("grade", ""),
            "confidence_note":   result.get("confidence_note", ""),
            "draft":             result["draft"],
            "chart":             result.get("chart"),
            "updated_params":    result.get("updated_params"),
            "retry_count":       result["retry_count"],
            "agent_ms":          result.get("agent_ms", 0),
            "signoff_ms":        result.get("signoff_ms", 0),
            "message":           result["message"],
            "rejection_history": _format_rejection_history(
                result.get("rejection_history", [])
            ),
        }
    except Exception as e:
        err_str = str(e).lower()
        if "content_filter" in err_str or "content filter" in err_str:
            return JSONResponse(
                status_code=400,
                content={"error": "죄송합니다. 해당 질의는 처리할 수 없습니다."},
            )
        log_error(
            request_id=str(uuid4()),
            session_id=req.session_id or "",
            question=req.question,
            domain=req.domain or "unknown",
            error=str(e),
            latency_ms=(time.monotonic() - t0) * 1000,
        )
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/stream")
async def stream_query(req: QueryRequest):
    """Q&A 플로우: SSE로 실시간 진행 상황 전달.
    각 단계(에이전트 시작/완료, Sign-off 판정, 최종 결과)를 이벤트로 스트리밍한다.
    """
    sid     = req.session_id or str(uuid4())
    session = await get_query_session(sid)
    if req.founder_context:
        session["profile"] = req.founder_context

    async def generate():
        t0 = time.monotonic()
        try:
            # ── 도메인 분류 ───────────────────────────────────
            if req.domain in ("admin", "finance", "legal", "location"):
                domain = req.domain
            else:
                classification = await domain_router.classify(req.question)
                domain = classification["domain"]

            yield f"event: domain_classified\ndata: {json.dumps({'domain': domain, 'session_id': sid})}\n\n"

            # ── 오케스트레이터 스트리밍 ───────────────────────
            params = req.current_params or (session["extracted"] if session["extracted"] else None)
            final_result = None
            async for ev in orchestrator.run_stream(
                domain=domain,
                question=req.question,
                profile=session["profile"],
                session_id=sid,
                max_retries=req.max_retries,
                current_params=params,
            ):
                event_name = ev.get("event", "message")

                if event_name == "complete":
                    # 세션 업데이트 및 저장
                    session["history"].add_user_message(req.question)
                    session["history"].add_assistant_message(ev["draft"])

                    if ev.get("status") == "approved" and ev.get("draft"):
                        new_vars = await extract_financial_vars(ev["draft"])
                        if new_vars:
                            session["extracted"].update(new_vars)

                    await save_query_session(sid, session)

                    # rejection_history 포맷 변환 후 complete 이벤트에 포함
                    ev["rejection_history"] = _format_rejection_history(
                        ev.get("rejection_history", [])
                    )
                    ev["domain"] = domain

                    log_query(
                        request_id        = ev["request_id"],
                        session_id        = sid,
                        question          = req.question,
                        domain            = domain,
                        status            = ev["status"],
                        grade             = ev.get("grade", ""),
                        retry_count       = ev["retry_count"],
                        rejection_history = ev.get("rejection_history", []),
                        draft             = ev["draft"],
                        latency_ms        = (time.monotonic() - t0) * 1000,
                    )
                    final_result = ev

                yield f"event: {event_name}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"

        except Exception as e:
            err_str = str(e).lower()
            if "content_filter" in err_str or "content filter" in err_str:
                yield f"event: error\ndata: {json.dumps({'message': '죄송합니다. 해당 질의는 처리할 수 없습니다.'}, ensure_ascii=False)}\n\n"
                return
            log_error(
                request_id=str(uuid4()),
                session_id=sid,
                question=req.question,
                domain=req.domain or "unknown",
                error=str(e),
                latency_ms=(time.monotonic() - t0) * 1000,
            )
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/v1/signoff")
async def signoff(req: SignoffRequest):
    """기존 draft를 Sign-off Agent에 단독으로 검증한다."""
    try:
        if req.domain not in ("admin", "finance", "legal", "location"):
            return JSONResponse(status_code=400, content={"error": f"지원하지 않는 도메인: {req.domain}"})
        client = get_signoff_client()
        verdict = await run_signoff(client=client, domain=req.domain, draft=req.draft)
        return verdict
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/doc/chat")
async def doc_chat(req: DocChatRequest):
    """
    문서 생성 플로우 (NAM):
    대화형으로 사용자 정보를 수집한 뒤 식품 영업 신고서 PDF를 생성한다.
    Sign-off 대상이 아닌 별도 플로우.
    """
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
    from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
    from plugins.food_business_plugin import FoodBusinessPlugin
    import re

    _DOC_SYSTEM = (
        "당신은 1인 창업가를 돕는 AI 행정 비서입니다. "
        "식품 영업 신고서 작성을 위해 아래 정보를 대화하듯 수집하세요.\n"
        "1. 대표자: 이름, 주민등록번호, 집 주소, 휴대전화 번호\n"
        "2. 영업소: 상호명, 매장 전화번호, 매장 주소, 영업 종류, 매장 면적\n"
        "모든 정보가 모이면 반드시 BusinessDoc-create_food_report 도구를 호출하세요."
    )

    try:
        sid = req.session_id

        # 매 요청마다 kernel·settings 재구성 (직렬화 불가 객체)
        _doc_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        kernel = Kernel()
        kernel.add_service(
            AzureChatCompletion(
                deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME"),
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=_doc_api_key if _doc_api_key else None,
                ad_token_provider=None if _doc_api_key else _TOKEN_PROVIDER,
                api_version="2024-12-01-preview",
            )
        )
        kernel.add_plugin(FoodBusinessPlugin(), plugin_name="BusinessDoc")
        settings = kernel.get_service("default")\
            .get_prompt_execution_settings_class()(service_id="default")
        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        # 이력은 Cosmos DB에서 복원
        history_raw = await get_doc_history(sid)
        history = ChatHistory()
        history.add_system_message(_DOC_SYSTEM)
        for msg in history_raw:
            if msg["role"] == "user":
                history.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                history.add_assistant_message(msg["content"])

        history.add_user_message(req.message)
        result = await kernel.get_service("default").get_chat_message_content(
            chat_history=history,
            settings=settings,
            kernel=kernel,
        )
        reply = result.content
        history.add_message(result)

        # 이력 저장 (system 메시지 제외)
        new_raw = history_raw + [
            {"role": "user",      "content": req.message},
            {"role": "assistant", "content": reply},
        ]
        await save_doc_history(sid, new_raw)

        pdf_url = None
        match = re.search(r"영업신고서_.*\.pdf", reply)
        if match:
            pdf_url = f"/files/{match.group(0)}"

        return {"reply": reply, "pdf_url": pdf_url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/v1/logs/export")
async def export_logs(
    type: str = Query("queries", description="queries | rejections | errors"),
    key: str = Query(..., description="EXPORT_SECRET 값"),
):
    """로그 JSONL 파일 전체를 원본 그대로 다운로드한다."""
    secret = os.getenv("EXPORT_SECRET", "")
    if not secret or key != secret:
        return JSONResponse(status_code=403, content={"error": "인증 실패"})
    if type not in ("queries", "rejections", "errors"):
        return JSONResponse(status_code=400, content={"error": "type은 queries, rejections, errors 중 하나여야 합니다."})

    from log_formatter import LOGS_DIR
    path = LOGS_DIR / f"{type}.jsonl"
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": f"{type}.jsonl 파일이 없습니다."})

    return FileResponse(
        path=str(path),
        media_type="application/x-ndjson",
        filename=f"{type}.jsonl",
    )


@app.get("/api/v1/logs")
async def get_logs(type: str = "queries", limit: int = 50):
    """JSONL 로그 파일을 파싱해 JSON 배열로 반환 (프론트엔드 로그 뷰어용)."""
    if type not in ("queries", "rejections", "errors"):
        return JSONResponse(status_code=400, content={"error": "type은 queries, rejections, errors 중 하나여야 합니다."})
    try:
        entries = load_entries_json(log_type=type, limit=limit)
        return {"type": type, "count": len(entries), "entries": entries}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
