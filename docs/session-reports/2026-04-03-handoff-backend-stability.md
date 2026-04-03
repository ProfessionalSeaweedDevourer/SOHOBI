# 세션 인수인계 — 2026-04-03 (백엔드 안정성)

## 브랜치
`PARK`

## 이번 세션에서 한 일

### 1. 백엔드 재시작 (2회)
- 증상: 모든 엔드포인트 504 Gateway Timeout, Azure 상태는 "Running"
- 재시작 명령 (다음에도 바로 사용 가능):
```bash
az containerapp revision restart \
  --name sohobi-backend \
  --resource-group rg-ejp-9638 \
  --revision $(az containerapp revision list --name sohobi-backend \
    --resource-group rg-ejp-9638 --query "[?properties.active].name" -o tsv)
```

### 2. PR #126 — variable_extractor sign_off 버그 (머지 대기)
- **원인**: `a6a6896` (2026-04-02) 리팩토링에서 `variable_extractor.py` 누락
  - 커널 서비스가 `"sign_off"` 단일 → `admin/finance/legal/location/chat/router` 6개로 분리됐는데 `variable_extractor.py:57`은 여전히 `get_service("sign_off")` 참조
- **결과**: 재무 에이전트 세션 변수 누적(Path B) 기능이 어제부터 완전 불능
- **수정**: `variable_extractor.py:57` `"sign_off"` → `"finance"`
- **PR**: https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/126

### 3. PR #128 — DB 풀 고갈 + 서버 다운 근본 원인 수정 (머지 대기)
- **Critical 원인 1**: `maxconn=5` → 상권 비교 분석 시 동시 커넥션이 풀 초과
- **Critical 원인 2**: DB 쿼리에 타임아웃 없음 → PostgreSQL 지연 시 스레드 무한 블록 → ThreadPool 고갈 → 서버 전체 무응답 → Azure 230초 → 504
- **수정**: `db/repository.py` — maxconn 5→20, connect_timeout=10s, statement_timeout=15s 추가
- **High 원인**: `session_store.py` 인메모리 세션 무제한 누적 → OOM 위험
- **수정**: `session_store.py` — 최대 500세션 LRU 방출
- **PR**: https://github.com/ProfessionalSeaweedDevourer/SOHOBI/pull/128

## 미완료 작업 (다음 세션 처리)

| 우선순위 | 작업 | 파일 | 내용 |
|----------|------|------|------|
| 1 | PR #126, #128 머지 | — | 검증 후 main 머지 |
| 2 | matplotlib 스레드 안전성 | `chart/location_chart.py` | 동시 상권 분석 시 plt 글로벌 상태 충돌 → Lock 추가 |
| 3 | Kernel 싱글톤 | `kernel_setup.py` | 매 요청마다 Kernel 재생성 → 모듈 레벨 싱글톤으로 변경 |

## 다음 세션 인수 요약

백엔드가 오늘 두 차례 다운되어 원인을 분석·수정했다. 핵심 원인은 DB 연결 풀(`maxconn=5`) 고갈과 쿼리 타임아웃 미설정으로, 상권 비교 분석 시 스레드가 무한 블록되어 서버 전체가 멈추는 구조였다. 두 PR(#126, #128)이 머지 대기 중이며 배포 후 검증 필요. 추가로 matplotlib 스레드 안전성(동시 상권 분석 race condition)과 Kernel 싱글톤 적용이 남아 있다.
