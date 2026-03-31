"""
Azure Functions — 정부지원사업 데이터 자동 수집 & AI Search 갱신

매주 월요일 새벽 3시(KST)에 실행:
1. 정부24 API + 추가 API에서 최신 데이터 수집
2. 추가 소스(소진공, 중기부, 신보 등) 큐레이션 데이터 병합
3. Cosmos DB 적재
4. Azure AI Search 인덱스 재구축 (임베딩 포함)

수동 실행:
- HTTP 트리거로 즉시 실행 가능 (POST /api/refresh_data)

배포:
  cd NAM2/azure_functions
  func azure functionapp publish <함수앱이름>

필요 환경변수 (Azure Portal → 함수 앱 → 구성):
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
  AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
  COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE_NAME,
  AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME,
  AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER,
  GOV24_API_KEY,
  KSTARTUP_API_KEY (선택), SME24_API_KEY (선택), BIZINFO_API_KEY (선택)
"""

import logging
import json
import azure.functions as func

from data_collector import collect_all_sources
from data_pipeline import run_pipeline

app = func.FunctionApp()


# ━━━ 1. 주간 자동 수집 (매주 월요일 새벽 3시 KST = UTC 18:00 일요일) ━━━
@app.timer_trigger(
    schedule="0 0 18 * * 0",  # UTC 일요일 18:00 = KST 월요일 03:00
    arg_name="timer",
    run_on_startup=False,
)
def weekly_data_refresh(timer: func.TimerRequest) -> None:
    """매주 자동으로 전체 데이터 수집 + AI Search 갱신"""
    logging.info("=== 주간 데이터 자동 갱신 시작 ===")

    try:
        # Step 1: 전체 소스에서 데이터 수집
        logging.info("[Step 1] 데이터 수집 중...")
        collect_result = collect_all_sources()
        logging.info(f"  수집 완료: {collect_result['total']}건")

        # Step 2: Cosmos DB + AI Search 갱신
        logging.info("[Step 2] 파이프라인 실행 중...")
        pipeline_result = run_pipeline(collect_result["data"])
        logging.info(
            f"  Cosmos DB: {pipeline_result['cosmos_count']}건, "
            f"AI Search: {pipeline_result['search_count']}건"
        )

        logging.info("=== 주간 데이터 갱신 완료 ===")

    except Exception as e:
        logging.error(f"주간 갱신 실패: {e}", exc_info=True)
        raise


# ━━━ 2. 수동 즉시 실행 (HTTP 트리거) ━━━
@app.route(route="refresh_data", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def manual_refresh(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/refresh_data — 수동으로 즉시 데이터 갱신"""
    logging.info("=== 수동 데이터 갱신 요청 ===")

    try:
        collect_result = collect_all_sources()
        pipeline_result = run_pipeline(collect_result["data"])

        result = {
            "status": "success",
            "collected": collect_result["total"],
            "sources": collect_result["source_stats"],
            "cosmos_count": pipeline_result["cosmos_count"],
            "search_count": pipeline_result["search_count"],
        }
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as e:
        logging.error(f"수동 갱신 실패: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
        )


# ━━━ 3. 헬스체크 ━━━
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/health — 함수 앱 상태 확인"""
    return func.HttpResponse(
        json.dumps({"status": "ok", "service": "sohobi-data-pipeline"}),
        mimetype="application/json",
    )
