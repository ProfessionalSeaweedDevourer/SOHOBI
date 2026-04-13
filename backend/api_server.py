"""
통합 API 서버
- GET  /health               — 헬스 체크
- POST /api/v1/query         — Q&A: 질문 → 도메인 라우팅 → 에이전트 → Sign-off
- POST /api/v1/signoff       — draft 단독 Sign-off 검증
- POST /api/v1/doc/chat      — 문서 생성: 대화형 정보 수집 → 식품 영업 신고서 PDF (NAM)
- GET  /api/v1/stats         — 성능 통계 집계 (에이전트별 latency, 등급/상태 분포)
- GET  /api/v1/logs          — JSONL 로그 조회 (프론트엔드 로그 뷰어용)
"""

import asyncio
import json
import logging
import os
import time
import traceback
from contextlib import asynccontextmanager
from uuid import uuid4

_logger = logging.getLogger("sohobi.api")

import checklist_store
import domain_router
import httpx
import orchestrator
import session_store
from auth import verify_api_key
from auth_router import router as auth_router
from checklist_router import router as checklist_router
from dotenv import load_dotenv
from event_router import router as event_router
from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from feedback_router import router as feedback_router
from kernel_setup import _TOKEN_PROVIDER, get_signoff_client
from log_formatter import load_entries_json
from logger import _format_rejection_history, log_error, log_query
from map_data_router import router as map_data_router
from map_router import router as map_router
from my_router import router as my_router
from pydantic import BaseModel, Field
from realestate_router import router as realestate_router
from report_router import router as report_router
from roadmap_router import router as roadmap_router
from session_store import (
    get_doc_history,
    get_query_session,
    get_recent_history,
    save_doc_history,
    save_query_session,
)
from signoff.signoff_agent import run_signoff
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from variable_extractor import extract_financial_vars

load_dotenv()


# ── 헬퍼 함수 (Rate Limiter + 로깅 공용) ────────────────────────
def _get_client_ip(request: Request) -> str:
    """X-Forwarded-For 마지막 hop → 실제 클라이언트 IP (Azure Container Apps 환경)."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        # Azure Container Apps proxy가 append한 마지막 IP = 실제 클라이언트
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


# ── Rate Limiter ─────────────────────────────────────────────────
_RATE_LIMIT_EXEMPT_IPS: set[str] = {"127.0.0.1", "::1"}

_extra = os.getenv("RATE_LIMIT_EXEMPT_IPS", "")
if _extra:
    _RATE_LIMIT_EXEMPT_IPS.update(ip.strip() for ip in _extra.split(",") if ip.strip())


def _rate_limit_key(request: Request) -> str:
    """면제 IP → 빈 문자열(slowapi가 limit 체크 스킵), 그 외 → 실제 IP."""
    ip = _get_client_ip(request)
    return "" if ip in _RATE_LIMIT_EXEMPT_IPS else ip


limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=["60/minute"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await session_store.close()
    await checklist_store.close()


app = FastAPI(title="SOHOBI Integrated API", version="1.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda req, exc: JSONResponse(
        status_code=429,
        content={"error": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."},
        headers={"Retry-After": str(exc.limit.limit.get_expiry())},
    ),
)
app.add_middleware(SlowAPIMiddleware)
app.include_router(auth_router)
app.include_router(my_router)
app.include_router(map_router)
app.include_router(map_data_router, dependencies=[Depends(verify_api_key)])
app.include_router(realestate_router, dependencies=[Depends(verify_api_key)])
app.include_router(feedback_router, dependencies=[Depends(verify_api_key)])
app.include_router(event_router, dependencies=[Depends(verify_api_key)])
app.include_router(checklist_router, dependencies=[Depends(verify_api_key)])
app.include_router(report_router)
app.include_router(roadmap_router, dependencies=[Depends(verify_api_key)])

# ── CORS: 허용 origin 명시적 화이트리스트 ─────────────────────
_ALLOWED_ORIGINS = [
    "https://sohobi.net",
    "https://www.sohobi.net",
    "https://delightful-rock-0de6c000f.6.azurestaticapps.net",
]
_extra_origins = os.getenv("CORS_EXTRA_ORIGINS", "")
if _extra_origins:
    _ALLOWED_ORIGINS.extend([o.strip() for o in _extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
    max_age=600,
)

# 1KB 이상 응답만 gzip 압축 (SSE 스트림은 자동 제외됨)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── IP 화이트리스트 미들웨어 (환경변수 미설정 시 비활성화) ────
class _IPFilterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_ips: set[str]):
        super().__init__(app)
        self.allowed_ips = allowed_ips

    async def dispatch(self, request: Request, call_next):
        client_ip = _get_client_ip(request)
        if client_ip not in self.allowed_ips:
            import logging

            logging.getLogger("sohobi.security").warning(
                "IP_BLOCKED ip=%r path=%r", client_ip, request.url.path
            )
            return JSONResponse(
                status_code=403, content={"error": "접근이 제한된 IP입니다."}
            )
        return await call_next(request)


_allowed_ips_raw = os.getenv("ALLOWED_IPS", "")
_allowed_ips = {ip.strip() for ip in _allowed_ips_raw.split(",") if ip.strip()}
if _allowed_ips:
    # rate limit 면제 IP는 IP 필터도 자동 통과
    _allowed_ips |= _RATE_LIMIT_EXEMPT_IPS
    app.add_middleware(_IPFilterMiddleware, allowed_ips=_allowed_ips)


@app.middleware("http")
async def add_response_time_header(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    ms = round((time.monotonic() - t0) * 1000)
    response.headers["X-Response-Time-MS"] = str(ms)
    if ms > 30000:
        _logger.warning("SLOW_REQUEST path=%r latency=%dms", request.url.path, ms)
    return response


# ── 스키마 ────────────────────────────────────────────────────


class QueryRequest(BaseModel):
    question: str = Field(..., max_length=2000, description="최대 2,000자")
    session_id: str | None = Field(
        default=None, description="생략 시 서버가 새 UUID를 발급한다"
    )
    founder_context: str | None = Field(
        default=None,
        description="창업자 상황 요약 (예: '서울 마포구, 자본금 1000만 원, 테이크아웃 카페'). "
        "동일 세션에서는 최초 한 번만 전달하면 이후 요청에 자동 적용된다.",
    )
    domain: str | None = Field(
        default=None, description="없으면 domain_router로 자동 분류"
    )
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
from datetime import UTC

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


# signoff 구분자 인젝션 제거 — 질문에 삽입된 <<<DRAFT_END>>> 등을 사전 차단
_STRIP_PATTERNS = [
    (r"<<<DRAFT_END>>>\s*\{.*?\}\s*<<<DRAFT_START>>>", ""),  # signoff 판정 삽입 패턴
    (r"<<<[A-Z_]+>>>", ""),  # 구분자 일반
]


def _sanitize_question(text: str) -> str:
    """질문에서 signoff 구분자 및 판정 삽입 패턴을 제거한다."""
    for pattern, repl in _STRIP_PATTERNS:
        text = _re.sub(pattern, repl, text, flags=_re.DOTALL)
    return text.strip()


# ── 내부 헬퍼 ─────────────────────────────────────────────────


async def _extract_and_save(sid: str, session: dict, draft: str) -> None:
    """재무 변수를 백그라운드에서 추출해 세션에 저장한다. 실패해도 메인 플로우에 영향 없음."""
    try:
        new_vars = await extract_financial_vars(draft)
        if new_vars:
            session["extracted"].update(new_vars)
            await save_query_session(sid, session)
    except Exception as e:
        _logger.warning("재무 변수 백그라운드 추출 실패 sid=%s: %s", sid, e)


# ── 엔드포인트 ────────────────────────────────────────────────


@app.get("/health")
@limiter.exempt
async def health():
    return {
        "status": "ok",
        "version": "1.1.0",
        "domains": ["admin", "finance", "legal", "location", "chat"],
        "plugins": ["FinanceSim", "LegalSearch", "BusinessDoc"],
    }


@app.get("/api/v1/my-ip")
@limiter.limit("30/minute")
async def my_ip(request: Request):
    """서버가 인식하는 클라이언트 IP 반환 (RATE_LIMIT_EXEMPT_IPS 등록용)."""
    return {"ip": _get_client_ip(request)}


@app.post("/api/v1/query", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def query(req: QueryRequest, request: Request):
    """Q&A 플로우: 질문 → 도메인 분류 → 에이전트(창업자 컨텍스트 주입) → Sign-off → 최종 응답"""
    t0 = time.monotonic()
    try:
        # ── 구분자 인젝션 사전 제거 ────────────────────────────
        question = _sanitize_question(req.question)

        # ── 프롬프트 인젝션 의심 패턴 감지 (거부 없이 로깅만) ─
        if _detect_injection(question):
            import logging

            logging.getLogger("sohobi.security").warning(
                "INJECTION_SUSPECT question=%r", req.question[:200]
            )

        # ── 세션 복원 또는 신규 생성 ──────────────────────────
        sid = req.session_id or str(uuid4())
        session = await get_query_session(sid)

        # 새 창업자 컨텍스트가 전달되면 세션 프로필 갱신
        if req.founder_context:
            session["profile"] = req.founder_context

        # ── 도메인 분류 ───────────────────────────────────────
        # 라우터는 항상 실행한다 (클라이언트 domain 지정 여부와 무관)
        # 세션 히스토리와 이전 도메인을 함께 전달해 대화 맥락 기반 분류 활성화
        prior_history = get_recent_history(session["history"])
        classification = await domain_router.classify(
            question,
            prior_history=prior_history,
            last_domain=session.get("last_domain"),
        )
        router_domain = classification["domain"]
        router_confidence = classification.get("confidence", 0.0)

        if req.domain in ("admin", "finance", "legal", "location", "chat"):
            if router_domain != req.domain and router_confidence >= 0.8:
                import logging

                logging.getLogger("sohobi.security").warning(
                    "DOMAIN_OVERRIDE client=%r router=%r confidence=%.2f question=%r",
                    req.domain,
                    router_domain,
                    router_confidence,
                    req.question[:100],
                )
                domain = router_domain  # 라우터 결과 우선
            else:
                domain = req.domain  # 라우터 확신 부족 → 클라이언트 지정 존중
        else:
            domain = router_domain

        # ── 오케스트레이터 실행 ───────────────────────────────
        # current_params: 클라이언트 전달값 우선, 없으면 서버 세션 추출값 사용
        params = req.current_params or (
            session["extracted"] if session["extracted"] else None
        )
        result = await orchestrator.run(
            domain=domain,
            question=question,
            profile=session["profile"],
            session_id=sid,
            prior_history=prior_history,
            max_retries=req.max_retries,
            current_params=params,
            context=session.get("context", {}),
        )

        # 세션 대화 이력 누적
        session["history"].add_user_message(question)
        session["history"].add_assistant_message(result["draft"])

        # location agent가 context를 갱신했으면 세션에 반영
        if result.get("updated_context"):
            session.setdefault("context", {}).update(result["updated_context"])

        # 마지막 실무 도메인 기록 (chat 제외) — 다음 요청의 도메인 연속성 방어선으로 활용
        if domain != "chat":
            session["last_domain"] = domain

        # 세션 저장 후, 재무 변수 추출은 백그라운드에서 처리 (사용자 응답 지연 없음)
        await save_query_session(sid, session)
        if result.get("status") == "approved" and result.get("draft"):
            asyncio.create_task(_extract_and_save(sid, session, result["draft"]))

        # ── 로깅 ─────────────────────────────────────────────
        log_query(
            request_id=result["request_id"],
            session_id=sid,
            user_id=session.get("user_id", ""),
            client_ip=_get_client_ip(request),
            question=req.question,
            domain=domain,
            status=result["status"],
            grade=result.get("grade", ""),
            retry_count=result["retry_count"],
            rejection_history=result.get("rejection_history", []),
            draft=result["draft"],
            latency_ms=(time.monotonic() - t0) * 1000,
            signoff_ms=result.get("signoff_ms", 0),
            final_verdict=result.get("final_verdict"),
        )

        return {
            "session_id": sid,
            "request_id": result["request_id"],
            "status": result["status"],
            "domain": domain,
            "grade": result.get("grade", ""),
            "confidence_note": result.get("confidence_note", ""),
            "draft": result["draft"],
            "chart": result.get("chart"),
            "charts": result.get("charts", []),
            "updated_params": result.get("updated_params"),
            "retry_count": result["retry_count"],
            "agent_ms": result.get("agent_ms", 0),
            "signoff_ms": result.get("signoff_ms", 0),
            "message": result["message"],
            "rejection_history": _format_rejection_history(
                result.get("rejection_history", [])
            ),
            "suggested_actions": result.get("suggested_actions", []),
            "is_partial": result.get("is_partial", False),
        }
    except Exception as e:
        err_str = str(e).lower()
        is_content_filter = (
            "content_filter" in err_str
            or "content filter" in err_str
            or "responsibleai" in err_str
            or "content_management_policy" in err_str
        )
        safe_draft = (
            "죄송합니다. 해당 질의는 처리할 수 없습니다."
            if is_content_filter
            else "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        )
        log_error(
            request_id=str(uuid4()),
            session_id=req.session_id or "",
            client_ip=_get_client_ip(request),
            question=req.question,
            domain=req.domain or "unknown",
            error=str(e),
            latency_ms=(time.monotonic() - t0) * 1000,
        )
        # 사용자 질의에서 500을 반환하지 않는다 — 내부 오류를 외부에 노출하지 않기 위해
        # 에러 메시지는 서버 로그에만 기록되고, 클라이언트에는 안전한 메시지만 반환한다
        return {
            "session_id": req.session_id or "",
            "request_id": str(uuid4()),
            "status": "error",
            "domain": req.domain or "unknown",
            "grade": "",
            "confidence_note": "",
            "draft": safe_draft,
            "chart": None,
            "updated_params": None,
            "retry_count": 0,
            "agent_ms": 0,
            "signoff_ms": 0,
            "message": "",
            "rejection_history": [],
        }


@app.post("/api/v1/stream", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def stream_query(req: QueryRequest, request: Request):
    """Q&A 플로우: SSE로 실시간 진행 상황 전달.
    각 단계(에이전트 시작/완료, Sign-off 판정, 최종 결과)를 이벤트로 스트리밍한다.
    """
    sid = req.session_id or str(uuid4())
    session = await get_query_session(sid)
    client_ip = _get_client_ip(request)
    if req.founder_context:
        session["profile"] = req.founder_context

    async def generate():
        t0 = time.monotonic()
        try:
            # ── 도메인 분류 ───────────────────────────────────
            prior_history_for_router = get_recent_history(session["history"])
            if req.domain in ("admin", "finance", "legal", "location", "chat"):
                domain = req.domain
            else:
                classification = await domain_router.classify(
                    req.question,
                    prior_history=prior_history_for_router,
                    last_domain=session.get("last_domain"),
                )
                domain = classification["domain"]

            yield f"event: domain_classified\ndata: {json.dumps({'domain': domain, 'session_id': sid})}\n\n"

            # ── 오케스트레이터 스트리밍 ───────────────────────
            params = req.current_params or (
                session["extracted"] if session["extracted"] else None
            )
            final_result = None
            async for ev in orchestrator.run_stream(
                domain=domain,
                question=req.question,
                profile=session["profile"],
                session_id=sid,
                prior_history=prior_history_for_router,
                max_retries=req.max_retries,
                current_params=params,
                context=session.get("context", {}),
            ):
                event_name = ev.get("event", "message")

                if event_name == "complete":
                    # 세션 업데이트 및 저장
                    session["history"].add_user_message(req.question)
                    session["history"].add_assistant_message(ev["draft"])

                    if domain != "chat":
                        session["last_domain"] = domain

                    if ev.get("status") == "approved" and ev.get("draft"):
                        new_vars = await extract_financial_vars(ev["draft"])
                        if new_vars:
                            session["extracted"].update(new_vars)

                    if ev.get("updated_context"):
                        session.setdefault("context", {}).update(ev["updated_context"])

                    # 프론트 렌더링용 메시지 메타데이터 축적 (Cosmos 2MB 문서 한도 대비 cap)
                    _MAX_SESSION_MESSAGES = 50
                    msgs = session.setdefault("messages", [])
                    msgs.append(
                        {
                            "question": req.question,
                            "domain": domain,
                            "grade": ev.get("grade", ""),
                            "draft": ev.get("draft", ""),
                            "confidence_note": ev.get("confidence_note", ""),
                            "suggested_actions": ev.get("suggested_actions", []),
                        }
                    )
                    if len(msgs) > _MAX_SESSION_MESSAGES:
                        session["messages"] = msgs[-_MAX_SESSION_MESSAGES:]

                    await save_query_session(sid, session)

                    # SSE 페이로드는 flatten된 스키마로, log_query는 raw로 전달
                    # (log_query 내부에서 _format_rejection_history를 다시 호출하므로
                    # 여기서 미리 flatten 하면 이중 포맷되어 verdict 필드가 소실됨)
                    raw_rejection_history = ev.get("rejection_history", [])
                    ev["rejection_history"] = _format_rejection_history(
                        raw_rejection_history
                    )
                    ev["domain"] = domain

                    log_query(
                        request_id=ev["request_id"],
                        session_id=sid,
                        user_id=session.get("user_id", ""),
                        client_ip=client_ip,
                        question=req.question,
                        domain=domain,
                        status=ev["status"],
                        grade=ev.get("grade", ""),
                        retry_count=ev["retry_count"],
                        rejection_history=raw_rejection_history,
                        draft=ev["draft"],
                        latency_ms=(time.monotonic() - t0) * 1000,
                        signoff_ms=ev.get("signoff_ms", 0),
                        final_verdict=ev.get("final_verdict"),
                    )
                    final_result = ev  # noqa: F841

                yield f"event: {event_name}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"

        except Exception as e:
            err_str = str(e).lower()
            if "content_filter" in err_str or "content filter" in err_str:
                yield f"event: error\ndata: {json.dumps({'message': '죄송합니다. 해당 질의는 처리할 수 없습니다.'}, ensure_ascii=False)}\n\n"
                return
            log_error(
                request_id=str(uuid4()),
                session_id=sid,
                client_ip=client_ip,
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


@app.post("/api/v1/signoff", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def signoff(req: SignoffRequest, request: Request):
    """기존 draft를 Sign-off Agent에 단독으로 검증한다."""
    try:
        if req.domain not in ("admin", "finance", "legal", "location"):
            return JSONResponse(
                status_code=400,
                content={"error": f"지원하지 않는 도메인: {req.domain}"},
            )
        client = get_signoff_client()
        verdict = await run_signoff(client=client, domain=req.domain, draft=req.draft)
        return verdict
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/doc/chat", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def doc_chat(req: DocChatRequest, request: Request):
    """
    문서 생성 플로우 (NAM):
    대화형으로 사용자 정보를 수집한 뒤 식품 영업 신고서 PDF를 생성한다.
    Sign-off 대상이 아닌 별도 플로우.
    """
    import re

    from plugins.food_business_plugin import FoodBusinessPlugin
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.function_choice_behavior import (
        FunctionChoiceBehavior,
    )
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

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
        settings = kernel.get_service("default").get_prompt_execution_settings_class()(
            service_id="default"
        )
        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        # 이력은 Cosmos DB에서 복원
        history_raw = await get_doc_history(sid)
        history = ChatHistory()  # noqa: F821
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
            {"role": "user", "content": req.message},
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


# ── 성능 통계 ──────────────────────────────────────────────────────


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(int(len(sorted_vals) * p), len(sorted_vals) - 1)
    return sorted_vals[idx]


def _latency_stats(latencies: list[float]) -> dict:
    if not latencies:
        return {"n": 0, "avg_ms": 0, "p50_ms": 0, "p90_ms": 0, "max_ms": 0}
    latencies.sort()
    return {
        "n": len(latencies),
        "avg_ms": round(sum(latencies) / len(latencies)),
        "p50_ms": round(_percentile(latencies, 0.5)),
        "p90_ms": round(_percentile(latencies, 0.9)),
        "max_ms": round(latencies[-1]),
    }


@app.get("/api/v1/stats", dependencies=[Depends(verify_api_key)])
async def get_stats(hours: int = Query(24, ge=1, le=2160)):
    """최근 N시간 쿼리·에러 로그를 집계하여 성능 통계를 반환한다."""
    from datetime import datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    cutoff_str = cutoff.isoformat()

    queries = [
        e
        for e in load_entries_json(log_type="queries", limit=0)
        if e.get("ts", "") >= cutoff_str
    ]
    errors = [
        e
        for e in load_entries_json(log_type="errors", limit=0)
        if e.get("ts", "") >= cutoff_str
    ]

    all_latencies = [e["latency_ms"] for e in queries if e.get("latency_ms")]

    by_domain: dict[str, list[float]] = {}
    by_status: dict[str, int] = {}
    by_grade: dict[str, int] = {}
    for e in queries:
        domain = e.get("domain", "unknown")
        by_domain.setdefault(domain, [])
        if e.get("latency_ms"):
            by_domain[domain].append(e["latency_ms"])
        status = e.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        grade = e.get("grade", "-")
        if grade and grade != "-":
            by_grade[grade] = by_grade.get(grade, 0) + 1

    total = len(queries) + len(errors)
    return {
        "range_hours": hours,
        "total": total,
        "overall": _latency_stats(all_latencies),
        "by_domain": {d: _latency_stats(lats) for d, lats in sorted(by_domain.items())},
        "by_status": by_status,
        "by_grade": by_grade,
        "error_count": len(errors),
        "error_rate": round(len(errors) / len(queries), 4) if queries else 0.0,
    }


@app.get("/api/v1/logs/export", dependencies=[Depends(verify_api_key)])
async def export_logs(
    type: str = Query("queries", description="queries | rejections | errors"),
):
    """로그 JSONL 파일 전체를 원본 그대로 다운로드한다."""
    if type not in ("queries", "rejections", "errors"):
        return JSONResponse(
            status_code=400,
            content={"error": "type은 queries, rejections, errors 중 하나여야 합니다."},
        )

    from log_formatter import LOGS_DIR

    path = LOGS_DIR / f"{type}.jsonl"
    if not path.exists():
        return JSONResponse(
            status_code=404, content={"error": f"{type}.jsonl 파일이 없습니다."}
        )

    return FileResponse(
        path=str(path),
        media_type="application/x-ndjson",
        filename=f"{type}.jsonl",
    )


@app.get("/api/v1/logs", dependencies=[Depends(verify_api_key)])
async def get_logs(
    type: str = "queries", limit: int = 50, user_id: str = "", session_id: str = ""
):
    """JSONL 로그 파일을 파싱해 JSON 배열로 반환 (프론트엔드 로그 뷰어용).

    user_id 파라미터를 지정하면 해당 사용자의 로그만 반환한다.
    응답 엔트리에는 user_id, user_email, user_name 필드가 보강된다.
    """
    if type not in ("queries", "rejections", "errors"):
        return JSONResponse(
            status_code=400,
            content={"error": "type은 queries, rejections, errors 중 하나여야 합니다."},
        )
    try:
        import session_store as _ss
        from auth_router import get_user_info

        # 로드 — user_id 필터 없으면 limit 조기 적용 (enrichment 대상 축소)
        load_limit = 0 if user_id else limit
        entries = load_entries_json(log_type=type, limit=load_limit)

        # session_id 조기 필터 — raw entry에 session_id 필드 존재, enrichment 전에 가능
        if session_id:
            entries = [e for e in entries if session_id in e.get("session_id", "")]

        # user_id 없을 때 limit 조기 적용 (session_id 필터 후)
        if not user_id and limit > 0:
            entries = entries[:limit]

        # 1단계: 기존 로그(user_id 없음)의 session_id → user_id 역조회 (gather 병렬)
        session_ids_to_lookup = {
            e["session_id"]
            for e in entries
            if e.get("session_id") and not e.get("user_id")
        }
        sid_list = list(session_ids_to_lookup)
        sid_results = await asyncio.gather(
            *[_ss.get_user_id_by_session(sid) for sid in sid_list]
        )
        session_user_map: dict[str, str] = dict(zip(sid_list, sid_results))

        # 2단계: unique user_ids → {email, name} dedup 조회 (gather 병렬)
        all_user_ids = {
            e.get("user_id") or session_user_map.get(e.get("session_id", ""), "")
            for e in entries
        } - {""}
        uid_list = list(all_user_ids)
        uid_results = await asyncio.gather(*[get_user_info(uid) for uid in uid_list])
        user_info_map: dict[str, dict] = dict(zip(uid_list, uid_results))

        # 3단계: enrichment
        enriched = []
        for e in entries:
            uid = e.get("user_id") or session_user_map.get(e.get("session_id", ""), "")
            info = user_info_map.get(uid, {})
            enriched.append(
                {
                    **e,
                    "user_id": uid,
                    "user_email": info.get("email", ""),
                    "user_name": info.get("name", ""),
                }
            )

        # 4단계: user_id 필터 적용 (enrichment 이후, user_id 필터 있을 때만)
        if user_id:
            enriched = [e for e in enriched if e.get("user_id") == user_id]

        # 5단계: limit — user_id 필터 있을 때만 필요 (그 외는 이미 조기 적용)
        if user_id and limit > 0:
            enriched = enriched[:limit]

        return {"type": type, "count": len(enriched), "entries": enriched}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 로그에 등장한 사용자 목록 (드롭다운용) ───────────────────────────

_LOG_USERS_CACHE: tuple[float, list] = (0.0, [])
_LOG_USERS_CACHE_TTL = 300  # 5분


@app.get("/api/v1/logs/users", dependencies=[Depends(verify_api_key)])
async def get_log_users():
    """로그에 등장한 사용자 목록 반환. LogViewer 필터 드롭다운용."""
    global _LOG_USERS_CACHE
    now = time.time()
    expires_at, cached_users = _LOG_USERS_CACHE
    if expires_at > now:
        return {"count": len(cached_users), "users": cached_users}

    try:
        import session_store as _ss
        from auth_router import get_user_info

        entries = load_entries_json(log_type="queries", limit=0)

        session_ids_to_lookup = {
            e["session_id"]
            for e in entries
            if e.get("session_id") and not e.get("user_id")
        }
        sid_list = list(session_ids_to_lookup)
        sid_results = await asyncio.gather(
            *[_ss.get_user_id_by_session(sid) for sid in sid_list]
        )
        session_user_map: dict[str, str] = dict(zip(sid_list, sid_results))

        all_user_ids = {
            e.get("user_id") or session_user_map.get(e.get("session_id", ""), "")
            for e in entries
        } - {""}

        uid_list = sorted(all_user_ids)
        uid_results = await asyncio.gather(*[get_user_info(uid) for uid in uid_list])
        users = [
            {
                "user_id": uid,
                "email": info.get("email", ""),
                "name": info.get("name", ""),
            }
            for uid, info in zip(uid_list, uid_results)
        ]

        _LOG_USERS_CACHE = (now + _LOG_USERS_CACHE_TTL, users)
        return {"count": len(users), "users": users}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)


@app.get("/wms/{path:path}")
async def vworld_wms_proxy(path: str, request: Request):
    """VWorld WMS 프록시 — 프로덕션(Azure SWA)에서 /wms/* 요청을 VWorld로 전달"""
    url = f"https://api.vworld.kr/{path}"
    params = dict(request.query_params)
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=10.0)
    return Response(
        content=r.content,
        media_type=r.headers.get("content-type", "application/octet-stream"),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # [PR#51 수정] traceback 클라이언트 응답에서 제거 (OWASP A05 보안 취약점)
    #   내부 파일 경로·코드 구조가 외부에 노출되므로 콘솔 로깅만 유지
    error_detail = traceback.format_exc()
    print(f"Unhandled error: {error_detail}")  # 서버 콘솔에만 출력
    return JSONResponse(status_code=500, content={"detail": str(exc)})
