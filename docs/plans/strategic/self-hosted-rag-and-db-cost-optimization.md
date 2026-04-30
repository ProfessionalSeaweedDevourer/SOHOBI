# 자체 RAG 전환 + DB 인프라 비용 재평가

> 본 문서는 2026-04-30 세션에서 PR #339(Azure AI Search Basic 차단)에 이어지는 후속 전략. 단기 결정이 아닌 **장기 방향성**.
> 관련 산출물:
> - 비용 baseline: [azure-cost-and-tenant-strategy.md](azure-cost-and-tenant-strategy.md) §2-1
> - 인덱스 빌드 파이프라인: PR #325 / [legal-index-reconnect.md](legal-index-reconnect.md)
> - 차단 PR: #339 (AI Search 라이브 자원 + Bicep 모듈 비활성화)

---

## 1. 출발점 — PR #339 결정 배경

Azure AI Search Basic SKU는 데이터 크기·쿼리량과 무관하게 **$73/월 정액**으로 청구된다 (Search Unit 기반 시간당 ~$0.10 lease). 본 프로젝트의 인덱싱 데이터 규모는 두 인덱스 합 ~170MB로 Basic 스토리지 한도(2GB) 대비 8% 수준이며, 현 시점(`sohobi-backend` Container App quickstart placeholder 상태)에서는 검색 기능이 실 사용 0건이다.

→ 비활성 자원에 정액을 지불하는 구조는 portfolio·개발 환경 정체성([azure-cost-and-tenant-strategy.md §1](azure-cost-and-tenant-strategy.md))과 충돌. 즉시 차단 후 **재가동 전 자체 RAG 대안을 결정**하는 것이 본 문서의 목적.

## 2. 비용 구조 — 가정 정정

PR #339 적용 후 월 청구 추정:

| 자원 | USD | 변동성 | 절감 여지 |
|------|----:|--------|-----------|
| PG B1ms (야간 정지) | 8-10 | 야간 cron 적용 후 유일한 변수 | 작음 — RAG 흡수 시 단위 비용 가치↑ |
| Container Apps (idle) | 3-5 | minReplicas=0 적용 | 0 |
| ACR Basic | 5 | 정액 (최저 tier) | 0 (비공개 이미지 → Docker Hub 대안 불가) |
| OpenAI 토큰 | 5-15 | 사용량 비례 (quota 승인 후) | rate limit으로 상한 가능 |
| Cosmos Serverless | <1 | 사용량 비례, $0.07 실측 | **0 — 절감 여지 없음** |
| Storage / LA / DNS | 1-2 | 정액 + 미세 변동 | 0 |
| **월 총** | **22-37** | | |

**핵심 정정**: 본 세션 초기 "DB 비용이 크다, ChromaDB 등으로 절감"이라는 가설이 제기되었으나, 실측상 Cosmos Serverless는 $0.07/월로 **DB 영역의 비용 절감 여지는 사실상 없다**. ChromaDB는 vector store이지 운영 데이터(세션·이벤트·피드백·체크리스트·로드맵·사용자) 저장소가 아니므로 Cosmos 대체 후보가 될 수 없다.

PG B1ms는 sangkwon_sales / sangkwon_store(50만+ 행) 운영 데이터의 정당한 비용이며, 야간 정지 cron(PR #337)으로 right-sizing 완료. 본 문서는 RAG 자체 호스팅에만 집중한다.

## 3. RAG 후보 4종 비교

데이터 규모 기준점:
- legal-index: ~4,500 docs × 1536d 임베딩 ≈ 28MB 벡터 + 14MB raw text ≈ 50MB
- gov-programs-index: 7,019 docs × 3072d 임베딩 ≈ 86MB 벡터 + 메타데이터 ≈ 120MB
- 합계 ~170MB

| 후보 | 인프라 추가비 | SK plugin 통합 | 백업·복구 | Container Apps 호환 | 운영 복잡도 |
|------|:-----------:|:---------------:|:----------:|:------------------:|:-----------:|
| **A. PostgreSQL pgvector** | **$0** | 신규 plugin (DAO 패턴 재사용) | `pg_dump` 통합 | 완벽 (이미 PG 연결 풀) | 낮음 |
| B. SQLite + sqlite-vec | $0 | 신규 plugin + 파일 mount | 파일 1개 backup | Container Apps 영속 디스크 어려움 (재시작 시 휘발) | 중간 |
| C. FAISS 디스크 영속 | $0 | 신규 plugin + 파일 mount | 파일 backup | scale-to-zero 충돌 (메모리 로드 시간) | 높음 |
| D. ChromaDB persistent | $0 | python-chromadb 의존 | sqlite + parquet 파일 | B와 동일 영속 디스크 이슈 | 중간 |

### 권장 — A. PostgreSQL pgvector

근거 6가지:

1. **인프라 추가비 0**. 운영 중인 `sohobi-prod-pg` B1ms에 `CREATE EXTENSION vector;` 한 줄로 활성화. PG Flexible Server의 `azure_extensions` allowlist에 `vector` 포함되어 있어 별도 이미지 빌드 불필요.

2. **backend 코드 자산 재사용**. [backend/db/dao/baseDAO.py:14-33](../../backend/db/dao/baseDAO.py)의 `ThreadedConnectionPool(minconn=2, maxconn=10)`이 RAG 워크로드까지 흡수. 신규 connection 라이브러리·프로필·인증 흐름 불필요.

3. **cutover 백업·복구 단순화**. 기존 [2026-04-26-azure-tenant-migration.md](../2026-04-26-azure-tenant-migration.md)의 cutover 절차는 (a) Cosmos JSONL export, (b) Blob azcopy sync, (c) pg_dump 3개 채널을 동기화해야 했음. RAG가 PG로 통합되면 (c) 단일 명령으로 RAG까지 포함 — cutover 시간 윈도우 단축.

4. **Container Apps 호환성 우월**. pgvector는 PG 서버에 상주하므로 backend Container App의 scale-to-zero·cold-start와 완전히 분리. SQLite-vec/FAISS/ChromaDB persistent는 모두 Container App 영속 디스크가 필요하나 minReplicas=0과 충돌 위험 (mount 형태에 따라 cold-start latency 증가, 또는 인스턴스 재생성 시 데이터 유실 가능).

5. **인덱스 증분 갱신 단순**. [scripts/legal_index/05_upload.py:194-217](../../scripts/legal_index/05_upload.py)의 `mergeOrUpload` 멱등 의미는 `INSERT ... ON CONFLICT (id) DO UPDATE` 1줄로 보존. 빌드 파이프라인 4단계 산출물(JSONL)을 그대로 입력으로 받음.

6. **법령명 OData 필터 → SQL 변환 직관적**. [backend/plugins/legal_search_plugin.py:49-54](../../backend/plugins/legal_search_plugin.py)의 `_detect_law_filter()`는 `WHERE law_name ILIKE '식품위생법%'` 등 1:1 대응. gov-programs-index의 복합 필터(`target_region`, `startup_stages`, `support_types`, `max_amount`, `industries`) 또한 SQL `WHERE`로 자연 변환.

### 탈락 사유

- **B. SQLite-vec**: 단일 파일 mount는 Container App 인스턴스 단위 sticky가 어렵고, 다중 인스턴스 환경에서 일관성 보장 곤란. 향후 minReplicas≥1 시나리오에서 곧 한계.
- **C. FAISS**: 메모리 기반 인덱스가 cold-start마다 디스크에서 재로드되면 첫 쿼리 latency 증가. minReplicas=0과 본질적 충돌.
- **D. ChromaDB**: 운영 모드로 쓰려면 별도 서버 프로세스 띄우거나 persistent client 사용해야 하는데 둘 다 Container App과 부조화. 또한 backend 의존이 PG 위주라 새 vector store SDK 추가가 가치 대비 부담.

## 4. 코드 변경 영향 면적

`backend/plugins/legal_search_plugin.py` + `backend/plugins/gov_support_plugin.py` 의 Azure SDK 직접 호출을 **추상 인터페이스**로 분리하고, 구현체를 pgvector로 교체한다.

```
LegalSearchPlugin (시그니처 불변)
  ├─ AbstractRagBackend (신규)
  │    ├─ AzureSearchBackend (현재 코드를 이전, fallback 보존)
  │    └─ PgvectorBackend (신규)
  └─ @kernel_function search_legal_docs (legal_agent.py 무영향)

GovSupportPlugin (동일 패턴)
  └─ filter_dict 인자로 region/stage/support_type/min_amount 추상화
```

| 파일 | 변경 |
|------|------|
| [backend/plugins/legal_search_plugin.py](../../backend/plugins/legal_search_plugin.py) | `__init__`에 backend 주입. 검색 본문은 backend 위임. 시그니처·로깅 불변 |
| [backend/plugins/gov_support_plugin.py](../../backend/plugins/gov_support_plugin.py) | 동일 패턴. backend 인터페이스에 `filter_dict` 추가 |
| `backend/plugins/rag_backend/abstract.py` (신규) | `AbstractRagBackend`: `embed(text)`, `search(vector, filter_dict, top_k)` |
| `backend/plugins/rag_backend/azure_search.py` (신규) | 현 코드를 backend 구현체로 이동. 환경변수 fallback 보존 |
| `backend/plugins/rag_backend/pgvector.py` (신규) | psycopg2 + pgvector. baseDAO 풀 재사용 |
| `scripts/legal_index/05_upload_pgvector.py` (신규) | [05_upload.py](../../scripts/legal_index/05_upload.py)의 변종. JSONL → `INSERT ... ON CONFLICT` |
| `scripts/legal_index/00_init_pgvector_schema.sql` (신규) | `CREATE EXTENSION vector` + 두 테이블 + HNSW 인덱스 |
| [backend/.env.example](../../backend/.env.example) | `RAG_BACKEND={azure_search|pgvector}` 플래그 |
| [backend/tests/test_legal_search_plugin.py](../../backend/tests/test_legal_search_plugin.py) | T-04~T-08 paramtrize로 두 backend 모두 커버 |

**SK plugin 시그니처 불변** → [backend/agents/legal_agent.py:64-65](../../backend/agents/legal_agent.py), [backend/agents/admin_agent.py:76-80](../../backend/agents/admin_agent.py) 무수정. orchestrator 무영향. 회귀 표면 최소화.

## 5. 마이그레이션 phase

| Phase | 산출물 PR | 의존 |
|-------|-----------|------|
| **A. 인터페이스 추상화** | `rag_backend/abstract.py` + `azure_search.py` + 단위 테스트 | 없음. 실 동작 azure_search 그대로 (회귀 0) |
| **B. pgvector schema + 빌드 파이프라인** | `00_init_pgvector_schema.sql` + `05_upload_pgvector.py` + legal-index 첫 빌드 | A |
| **C. PgvectorBackend 구현 + 듀얼 운영** | `rag_backend/pgvector.py` + `RAG_BACKEND` 플래그. 두 backend recall@k / latency 비교 | B |
| **D. gov-programs-index** | 외부 데이터 확보 후 동일 파이프라인 (text-embedding-3-large 유지) | C + 외부 데이터 |
| **E. AI Search 모듈 폐기** | `infra/bicep/modules/ai-search.bicep` 삭제 + main.bicep `enableAiSearch` 제거 | C 또는 D 종료 후 |

Phase A·B는 OpenAI quota 승인 무관 즉시 진행 가능. Phase C는 임베딩 호출 필요. `text-embedding-3-large` Standard SKU는 신규 구독 default quota 350(= 350K TPM) 기존 부여되어 있어 즉시 가능 — `gpt-5.4-mini` GlobalStandard quota 승인은 RAG 자체에는 무관.

## 6. 검증

### Phase A 완료 후
- 단위 테스트 PASS: `backend/.venv/bin/python3 -m pytest backend/tests/test_legal_search_plugin.py`
- 회귀: 기존 azure_search backend 동작 동일 (T-04~T-06 결과 비교)

### Phase B 완료 후
- 로컬 PG에 schema 적용: `psql -h $PG_HOST -d sohobi -f scripts/legal_index/00_init_pgvector_schema.sql`
- 빌드 dry-run: `python3 scripts/legal_index/05_upload_pgvector.py --in data/legal/embedded.jsonl --table legal_docs --batch-size 1000`
- row count: `SELECT count(*) FROM legal_docs;` ≈ 4,500
- 인덱스 사이즈: `SELECT pg_size_pretty(pg_total_relation_size('legal_docs'));` ≈ 50-80MB

### Phase C 완료 후 (품질 비교)
- 정답 쿼리 셋 신규 작성: `backend/tests/fixtures/rag_eval_queries.json` (15-30 쿼리 + 정답 doc_id)
- recall@5: pgvector ≥ azure_search × 0.95 합격
- latency P95: pgvector ≤ 500ms 합격 (azure_search 기준 P95 ~300ms)

### 비용 검증
- Phase E 후: 다음 청구 사이클 AI Search $73 → 0 확인
- pgvector 추가 후 PG B1ms 컴퓨트·스토리지 사용률 모니터링 (32GB 한도 대비 < 5% 예상)

## 7. 결정 필요 사항

본 strategic 문서가 머지된 이후 팀 회의에서 합의 필요:

1. **권장(pgvector)에 동의**하는가, 또는 다른 후보(SQLite-vec / ChromaDB / FAISS)를 우선시하는가?
2. **마이그레이션 시작 시점** — 즉시 Phase A 착수 vs cutover 일정 후순위?
3. **품질 측정 정답 쿼리 셋** 작성 책임 — Park 단독 vs 팀 분담 (도메인 지식 필요)
4. **Phase D gov-programs-index 외부 데이터 확보** 워크스트림 책임자 — 현재 [carry-over unresolved](../../session-reports/2026-04-27-azure-tenant-foundation-handoff.md) 상태

## 8. 위험 / 트레이드오프

- **단일점 장애 강화**: PG가 운영 데이터 + RAG 데이터 모두 보유 → PG 장애 시 검색 + sangkwon 동시 영향. 단 portfolio 환경 SLA 요구 0이라 수용 가능. Production 전환 시 read replica 검토.
- **PG B1ms 자원 한계**: 1 vCPU / 2 GiB RAM. HNSW 인덱스 빌드는 일회성이지만 메모리 압박 가능 → `maintenance_work_mem` 임시 상향 + `SET LOCAL` 패턴으로 빌드 시간만 격리.
- **dimension 차이**: legal(1536d, small) vs gov(3072d, large). 통일 시 legal 재빌드 필요. 별 테이블로 두면 storage 추가 10-20% — 통일 안 해도 무방.
- **AI Search semantic reranking 의존**: 현재 두 plugin 모두 `query_type='semantic'` + `reranker_score` 임계값 필터. pgvector는 BM25는 PG full-text search로 대체 가능하나 **시맨틱 리랭커는 자체 구현 필요** (cross-encoder 모델 또는 임베딩 cosine 재정렬). Phase C 품질 비교에서 가장 큰 변수.

## 9. 향후 검토 후보 (본 문서 범위 외)

- **Container App rate limit + 일별 OpenAI 토큰 상한**: 트래픽 급증 방어. 별도 PR 후보.
- **Defender for Cloud 비활성화**: [azure-cost-and-tenant-strategy.md §3-B](azure-cost-and-tenant-strategy.md) 권고. 신규 테넌트에서 활성 여부 확인 필요.
- **AAD 인증 전환**: 현재 backend 코드가 OpenAI/Search에 API key 사용. Container App system identity 기반으로 변경 — 보안 마감 작업, 별도 PR.
