"""
통합 API 서버
- GET  /health               — 헬스 체크
- POST /api/v1/query         — Q&A: 질문 → 도메인 라우팅 → 에이전트 → Sign-off
- POST /api/v1/signoff       — draft 단독 Sign-off 검증
- POST /api/v1/doc/chat      — 문서 생성: 대화형 정보 수집 → 식품 영업 신고서 PDF (NAM)
- GET  /api/v1/logs          — JSONL 로그 조회 (프론트엔드 로그 뷰어용)
"""

import os
import time
from uuid import uuid4

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from semantic_kernel.contents import ChatHistory

import domain_router
import orchestrator
from signoff.signoff_agent import run_signoff
from kernel_setup import get_kernel
from logger import log_query, log_error
from log_formatter import load_entries_json
from logger import _format_rejection_history
from variable_extractor import extract_financial_vars

load_dotenv()

app = FastAPI(title="SOHOBI Integrated API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 스키마 ────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    session_id: str | None = Field(default=None, description="생략 시 서버가 새 UUID를 발급한다")
    founder_context: str | None = Field(
        default=None,
        description="창업자 상황 요약 (예: '서울 마포구, 자본금 1000만 원, 테이크아웃 카페'). "
                    "동일 세션에서는 최초 한 번만 전달하면 이후 요청에 자동 적용된다.",
    )
    domain: str | None = Field(default=None, description="없으면 domain_router로 자동 분류")
    max_retries: int = Field(default=3, ge=0, le=10)


class SignoffRequest(BaseModel):
    domain: str = Field(description="admin | finance | legal | location")
    draft: str


class DocChatRequest(BaseModel):
    message: str
    session_id: str = Field(default="default")


# ── 세션 스토어 ────────────────────────────────────────────────
# _query_sessions: Q&A 플로우의 창업자 프로필 + 대화 이력 (인메모리)
# _doc_sessions:   문서 생성 플로우 (기존)
_query_sessions: dict = {}  # session_id → {"profile": str, "history": ChatHistory}
_doc_sessions:   dict = {}


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
        # ── 세션 복원 또는 신규 생성 ──────────────────────────
        sid = req.session_id or str(uuid4())
        session = _query_sessions.setdefault(sid, {"profile": "", "history": ChatHistory(), "extracted": {}})

        # 새 창업자 컨텍스트가 전달되면 세션 프로필 갱신
        if req.founder_context:
            session["profile"] = req.founder_context

        # ── 도메인 분류 ───────────────────────────────────────
        if req.domain in ("admin", "finance", "legal", "location"):
            domain = req.domain
        else:
            classification = await domain_router.classify(req.question)
            domain = classification["domain"]

        # ── 오케스트레이터 실행 ───────────────────────────────
        result = await orchestrator.run(
            domain=domain,
            question=req.question,
            profile=session["profile"],
            session_id=sid,
            max_retries=req.max_retries,
            session_vars=session["extracted"] if session["extracted"] else None,
        )

        # 세션 대화 이력 누적 (프론트엔드 표시 또는 향후 활용)
        session["history"].add_user_message(req.question)
        session["history"].add_assistant_message(result["draft"])

        # ── 재무 변수 추출 및 세션 누적 ──────────────────────
        if result.get("status") == "approved" and result.get("draft"):
            new_vars = await extract_financial_vars(result["draft"])
            if new_vars:
                session["extracted"].update(new_vars)

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
            "retry_count":       result["retry_count"],
            "agent_ms":          result.get("agent_ms", 0),
            "signoff_ms":        result.get("signoff_ms", 0),
            "message":           result["message"],
            "rejection_history": _format_rejection_history(
                result.get("rejection_history", [])
            ),
        }
    except Exception as e:
        log_error(
            request_id=str(uuid4()),
            session_id=req.session_id or "",
            question=req.question,
            domain=req.domain or "unknown",
            error=str(e),
            latency_ms=(time.monotonic() - t0) * 1000,
        )
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/signoff")
async def signoff(req: SignoffRequest):
    """기존 draft를 Sign-off Agent에 단독으로 검증한다."""
    try:
        if req.domain not in ("admin", "finance", "legal", "location"):
            return JSONResponse(status_code=400, content={"error": f"지원하지 않는 도메인: {req.domain}"})
        kernel = get_kernel()
        verdict = await run_signoff(kernel=kernel, domain=req.domain, draft=req.draft)
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

    try:
        sid = req.session_id
        if sid not in _doc_sessions:
            kernel = Kernel()
            kernel.add_service(
                AzureChatCompletion(
                    deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME"),
                    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    api_version="2024-12-01-preview",
                )
            )
            kernel.add_plugin(FoodBusinessPlugin(), plugin_name="BusinessDoc")

            history = ChatHistory()
            history.add_system_message(
                "당신은 1인 창업가를 돕는 AI 행정 비서입니다. "
                "식품 영업 신고서 작성을 위해 아래 정보를 대화하듯 수집하세요.\n"
                "1. 대표자: 이름, 주민등록번호, 집 주소, 휴대전화 번호\n"
                "2. 영업소: 상호명, 매장 전화번호, 매장 주소, 영업 종류, 매장 면적\n"
                "모든 정보가 모이면 반드시 BusinessDoc-create_food_report 도구를 호출하세요."
            )
            settings = kernel.get_service("default")\
                .get_prompt_execution_settings_class()(service_id="default")
            settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
            _doc_sessions[sid] = {"kernel": kernel, "history": history, "settings": settings}

        session = _doc_sessions[sid]
        kernel = session["kernel"]
        history: ChatHistory = session["history"]
        settings = session["settings"]

        history.add_user_message(req.message)
        result = await kernel.get_service("default").get_chat_message_content(
            chat_history=history,
            settings=settings,
            kernel=kernel,
        )
        reply = result.content
        history.add_message(result)

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
