# model_config.py
# ---------------------------------------------------------
# 유료/무료 구독 티어별 모델 배포 매핑
#
# 활성화 절차:
#   1. kernel_setup.py — create_kernel(domain, tier) 시그니처 추가,
#      MODEL_CONFIG[tier][domain] 으로 deployment name 선택
#   2. orchestrator.py — run()/run_stream() 에 user_tier: str = "free" 추가
#   3. api_server.py — QueryRequest 에 user_tier: Literal["free","premium"] = "free" 추가
#   4. agents/finance_agent.py — param 추출 LLM / 결과 설명 LLM 을
#      각각 finance_param / finance_explain deployment 로 분리
# ---------------------------------------------------------
#
# 채택 모델 (Claude 계열 Azure 지역 미지원으로 GPT 전용)
# ┌──────────────┬───────────────────────────────────────────────────────────┐
# │ gpt-5.4-mini │ 극속·저비용 — 모든 무료 티어 에이전트 기본 모델            │
# │ gpt-5.4-pro  │ 고품질 추론 — 유료 티어 전용 (법령·재무 설명 정확도↑)      │
# └──────────────┴───────────────────────────────────────────────────────────┘
#
# 제외 모델
#   claude-haiku-4-5 / claude-sonnet-4-5 / claude-opus-4-1
#       → Azure AI Foundry 지역 선택 불가 (배포 버튼 존재하나 비활성)
#   gpt-5.4 (full)  — reasoning 모델, 무료 티어 응답 시간 10-40s → UX 부적합
#   gpt-5.3-codex   — 코드 특화, 법령·상권 텍스트 분석에 부적합
#   gpt-5.2 / 5.2-chat  — 구세대, 5.4 대비 우위 없음
#   grok-4-1-fast-reasoning — Azure 통합 경로 불명확, 한국어 품질 불확실
# ---------------------------------------------------------

MODEL_CONFIG = {
    "free": {
        "router":          "gpt-5.4-mini",  # 도메인 분류 — 모든 요청 선행, 속도 최우선
        "chat":            "gpt-5.4-mini",  # FAQ·사용법 안내 — sign-off 없음, 단순 텍스트
        "admin":           "gpt-5.4-mini",  # 3개 플러그인 통합·법령 검증
        "finance_param":   "gpt-5.4-mini",  # JSON 파라미터 추출 — 구조화 입력 파싱
        "finance_explain": "gpt-5.4-mini",  # 시뮬레이션 결과 해설
        "location":        "gpt-5.4-mini",  # DB 결과 분석·상권 해설
        "legal":           "gpt-5.4-mini",  # RAG 법령 인용·계약 해석
        "signoff":         "gpt-5.4-mini",  # JSON 루브릭 판정 (구조화 출력)
    },
    "premium": {
        "router":          "gpt-5.4-mini",  # 분류만 → 업그레이드 불필요
        "chat":            "gpt-5.4-mini",  # FAQ → 업그레이드 불필요
        "admin":           "gpt-5.4",       # 플러그인이 품질 결정 → pro 불필요
        "finance_param":   "gpt-5.4-mini",  # 파라미터 추출 → 업그레이드 불필요
        "finance_explain": "gpt-5.4",       # 시뮬레이션이 품질 결정 → pro 불필요
        "location":        "gpt-5.4",       # DB 조회가 품질 결정 → pro 불필요
        "legal":           "o3",            # 단계적 추론 — 법령 충돌·엣지케이스 해석
        "signoff":         "o4-mini",       # 백엔드 전용, latency 허용 — 루브릭 판정 정확도↑
    },
}
