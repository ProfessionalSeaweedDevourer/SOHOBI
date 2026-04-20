# 법무 RAG: 신규 legal-index 연결 가이드 (2026-04-20)

## 배경

- 세션 인수인계: [2026-04-20-legal-rag-dead-and-gov-env-sync-handoff.md](../session-reports/2026-04-20-legal-rag-dead-and-gov-env-sync-handoff.md)
- 현 상태 요약:
  - `choiasearchhh.search.windows.net` DNS NXDOMAIN (외부 구독 삭제 추정)
  - Container App `azure-search-endpoint` / `azure-search-key` 시크릿이 literal placeholder (`<AZURE_SEARCH_ENDPOINT>`, `<AZURE_SEARCH_KEY>`)
  - 결과: `search_legal_docs` 호출은 실패 문자열을 반환하나 에이전트(gpt-4o)가 이를 무시하고 hallucination 으로 grade A 응답 생성. 로그 보존 전 구간 79건 중 RAG 인용 0건.

## 범위

이 플랜은 **"어딘가에 정상 legal-index 가 새로 구축된 상태"** 를 전제로, 그것을 프로덕션 백엔드에 연결·검증하는 작업만 다룬다.

**범위 외** (별도 플랜):

- 인덱스 스키마 설계·데이터 원본 확보·임베딩 생성 → koreacentral consolidation 플랜 (`2026-04-20-ai-search-koreacentral-consolidation.md`, 미작성)
- `_available` 가드 placeholder 감지 — 본 플랜에 포함 (연결 작업과 불가분)

---

## 1. 전제조건 — 신규 인덱스가 갖춰야 할 계약

플러그인 코드 [backend/plugins/legal_search_plugin.py](../../backend/plugins/legal_search_plugin.py) 가 런타임에 기대하는 인덱스 스펙.

### 1-1. 필드

[legal_search_plugin.py:132-145](../../backend/plugins/legal_search_plugin.py#L132-L145) `select` 절 참조 필드 전원 존재 필수:

| 필드 | 용도 | 타입 |
|---|---|---|
| `id` | key | Edm.String |
| `lawName` | 법령명 — `_detect_law_filter` 정확 매칭 대상 | Edm.String, filterable |
| `mst` | 법령 master 식별자 | Edm.String |
| `articleNo` | 조항 번호 (예: "제4조") | Edm.String |
| `chapterTitle`, `sectionTitle`, `articleTitle` | 계층 헤더 포맷용 | Edm.String |
| `content`, `fullText` | 본문 (fullText 우선, fallback content) | Edm.String, searchable |
| `source`, `docType`, `category` | 보조 메타 | Edm.String |
| `content_vector` | 벡터 검색 필드 | Collection(Edm.Single) |

### 1-2. 벡터 설정

- 벡터 필드명: **`content_vector`** (코드 하드코딩, [legal_search_plugin.py:125](../../backend/plugins/legal_search_plugin.py#L125))
- 알고리즘: HNSW (k_nearest_neighbors 사용)
- **차원**: embedding deployment 와 정확 일치 필수
  - `text-embedding-3-small` → 1536
  - `text-embedding-3-large` → 3072 (gov-programs-index 와 동일 차원)
- 같은 AI Search 인스턴스에 gov/legal 두 인덱스를 올릴 경우에도 차원은 인덱스별 독립

### 1-3. 시맨틱 리랭커

- configuration 이름: **`semantic-config`** ([legal_search_plugin.py:129](../../backend/plugins/legal_search_plugin.py#L129) 하드코딩)
- title field, content fields 정의 (권장: `articleTitle` → title, `fullText` → content)
- 코드가 `reranker_score < 1.5` 미만을 드롭 ([legal_search_plugin.py:152](../../backend/plugins/legal_search_plugin.py#L152)) — 신규 인덱스에서 의미 있는 점수 분포가 나오는지 스모크 확인 필요

### 1-4. 법령명 표기 정규화

[legal_search_plugin.py:31-46](../../backend/plugins/legal_search_plugin.py#L31-L46) `_LAW_NAMES` 14개와 `lawName` 값이 **prefix 기준 일치**해야 OData 필터(`search.ismatch('식품위생법*', 'lawName')`)가 적중함. 인덱스 구축 시 lawName 정규화 규칙이 이 목록과 맞는지 사전 확인.

---

## 2. 연결 단계

### 2-1. Container App 시크릿 교체

현재는 시크릿 값 자체가 placeholder 문자열이므로 **시크릿 재등록 필수**:

```bash
az containerapp secret set \
  --name sohobi-backend -g rg-ejp-9638 \
  --secrets \
    azure-search-endpoint="https://<신규 search resource>.search.windows.net" \
    azure-search-key="<실 admin 또는 query key>" \
    azure-openai-endpoint="https://<openai resource>.openai.azure.com/" \
    azure-openai-api-key="<실 key>"
```

### 2-2. 환경변수 확인

시크릿을 참조하는 env 매핑과 상수 env 를 확인:

```bash
az containerapp show --name sohobi-backend -g rg-ejp-9638 \
  --query "properties.template.containers[0].env[?name=='AZURE_SEARCH_ENDPOINT' \
           || name=='AZURE_SEARCH_KEY' \
           || name=='AZURE_SEARCH_INDEX' \
           || name=='AZURE_OPENAI_ENDPOINT' \
           || name=='AZURE_OPENAI_API_KEY' \
           || name=='AZURE_EMBEDDING_DEPLOYMENT' \
           || name=='AZURE_EMBEDDING_API_VERSION']"
```

기대값:

| env | 값 | 비고 |
|---|---|---|
| `AZURE_SEARCH_ENDPOINT` | secretRef: azure-search-endpoint | |
| `AZURE_SEARCH_KEY` | secretRef: azure-search-key | |
| `AZURE_SEARCH_INDEX` | `legal-index` (또는 신규 인덱스명) | |
| `AZURE_OPENAI_ENDPOINT` | secretRef: azure-openai-endpoint | |
| `AZURE_OPENAI_API_KEY` | secretRef: azure-openai-api-key | |
| `AZURE_EMBEDDING_DEPLOYMENT` | **명시 필수** (예: `text-embedding-3-large`) | 기본값 `text-embedding-3-small` 함정 (§6 참조) |
| `AZURE_EMBEDDING_API_VERSION` | `2024-02-01` (기본값 동일 시 생략 가능) | |

### 2-3. 새 리비전 롤

시크릿만 교체한 경우에도 새 리비전이 롤아웃돼야 프로세스에 반영:

```bash
az containerapp update --name sohobi-backend -g rg-ejp-9638 \
  --revision-suffix legalfix-$(date +%Y%m%d)
```

single-revision mode 가 아닐 경우 traffic split 확인:

```bash
az containerapp revision list --name sohobi-backend -g rg-ejp-9638 \
  --query "[].{name:name, active:properties.active, weight:properties.trafficWeight}"
```

### 2-4. 로컬 `.env` 동기화 (로컬 테스트 시만)

```
AZURE_SEARCH_ENDPOINT=https://<신규 search>.search.windows.net
AZURE_SEARCH_KEY=<실 key>
AZURE_SEARCH_INDEX=legal-index
AZURE_OPENAI_ENDPOINT=https://<openai>.openai.azure.com/
AZURE_OPENAI_API_KEY=<실 key>
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large
```

- `backend/.env` 는 gitignored — **커밋·pastebin·외부 디렉토리 복사 금지**
- `GOV_SEARCH_*` 변수와 분리 유지 (같은 리소스를 공유하더라도 변수 이름은 분리)

---

## 3. 가드 강화 (연결과 동시에 배포)

### 3-1. `_available` placeholder 감지

현재 [legal_search_plugin.py:70-72](../../backend/plugins/legal_search_plugin.py#L70-L72):

```python
self._available = bool(
    search_key and search_endpoint and openai_endpoint and openai_key
)
```

`<AZURE_SEARCH_ENDPOINT>` 같은 literal placeholder 가 non-empty str 로 truthy 판정되는 문제가 이번 사고의 핵심. 다음 가드 추가:

```python
def _is_placeholder(v: str) -> bool:
    v = (v or "").strip()
    return v.startswith("<") and v.endswith(">")

self._available = all(
    s and not _is_placeholder(s)
    for s in (search_key, search_endpoint, openai_endpoint, openai_key)
)
```

### 3-2. 실패 응답 문구 강화

[legal_search_plugin.py:105](../../backend/plugins/legal_search_plugin.py#L105) 의 비가용 문구가 에이전트에게 "도구가 없으니 내 지식으로 답하라" 로 해석되지 않도록:

```python
return (
    "LEGAL_RAG_UNAVAILABLE: 법령 검색 서비스가 중단 상태입니다. "
    "본 응답은 법령 데이터베이스를 참조하지 못한 상태임을 사용자에게 고지해야 합니다."
)
```

[backend/agents/legal_agent.py](../../backend/agents/legal_agent.py) 지시사항에도 추가:

> 도구 응답이 `LEGAL_RAG_UNAVAILABLE` 로 시작하면 그 문구를 그대로 사용자에게 전달하고, 구체 법령·조항 번호·문구 인용 생성을 중단한다.

### 3-3. 검색 예외 시 동일 처리

[legal_search_plugin.py:179-180](../../backend/plugins/legal_search_plugin.py#L179-L180) 의 except 블록도 동일 prefix (`LEGAL_RAG_UNAVAILABLE:`) 를 쓰도록 통일해 runtime DNS/권한 실패와 설정 누락을 한 채널로 처리.

---

## 4. 검증 (연결 직후 — 필수)

### 4-1. 단위 검증 — 스모크 쿼리 3건

```bash
source backend/.env
for q in \
  "식품위생법상 영업신고 대상" \
  "부가가치세 간이과세 기준" \
  "근로기준법 연차유급휴가 발생 요건"
do
  echo "=== $q ==="
  curl -s -X POST "$BACKEND_HOST/api/v1/query" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"$q\"}" | jq -r '.answer' | head -20
done
```

통과 기준: 3건 모두 응답에 `[법령명 > …]` 형식 헤더 또는 구체 조항 번호(`제N조`)가 lawName 출처와 함께 포함.

### 4-2. 로그 기반 검증

```bash
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=50" \
  | jq -r '.queries[] | select(.domain=="legal") | .answer' \
  | grep -Ec '^\['
```

`limit=50` 으로 최근 legal 쿼리 중 RAG 헤더(`[`로 시작) 매칭 건수 확인. 이전에는 79건 중 0건이었음 → **스모크 직후 3건 이상** 이면 통과.

### 4-3. 리랭커 점수 분포 확인

Container App 로그에서:

```bash
az containerapp logs show --name sohobi-backend -g rg-ejp-9638 --tail 200 \
  | grep "LegalSearch"
```

- `낮은 리랭커 점수 제외` 가 **모든 쿼리에서 발생** 하면 `1.5` 임계값이 신규 인덱스 스코어 스케일과 맞지 않음 → 임계값 튜닝 필요
- 반대로 한 번도 발생하지 않으면 쿼리 품질 검증용 noise 데이터로 threshold 가 실질 무력화됐는지 점검

### 4-4. gov 무회귀 확인

legal 연결 작업이 gov 에 영향을 주지 않았는지 확인 (같은 엔드포인트 공유 시 의존):

```bash
curl -s -X POST "$BACKEND_HOST/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "서울시 소상공인 창업 지원금 알려줘"}' | jq -r '.answer' | head -10
```

`sohobi-search` 의 `gov-programs-index` 에서 프로그램명이 출력돼야 함.

---

## 5. 롤백

문제 발생 시:

```bash
# 이전 리비전으로 트래픽 100%
az containerapp revision list --name sohobi-backend -g rg-ejp-9638 \
  --query "[?properties.active].{name:name}"
az containerapp ingress traffic set --name sohobi-backend -g rg-ejp-9638 \
  --revision-weight <previous-revision>=100
```

**단, 이전 리비전은 placeholder 상태 = 무기능** 이므로 "롤백 = 법무 도메인 hallucination 상태 회귀". 일시 차단이 더 안전하면 `legal` 도메인 라우팅을 비활성화하거나 프런트에 "법령 DB 점검 중" 배너를 띄우는 쪽을 우선 검토.

---

## 6. 주의 (traps)

- **embedding 모델 버전 동일성**: 인덱스 구축에 사용한 모델과 런타임 쿼리 임베딩이 **정확히 동일 버전** 이어야 벡터 호환. text-embedding-3-large v1 인덱스는 동일 v1 에서만 호환
- **`AZURE_EMBEDDING_DEPLOYMENT` 기본값 함정**: [legal_search_plugin.py:62](../../backend/plugins/legal_search_plugin.py#L62) 기본값은 `text-embedding-3-small` (1536d). env 미설정 + 3072d 인덱스 조합 시 400 차원 불일치 — 신규 연결 시 env 명시 필수
- **`gov_*` 변수와 분리**: legal 은 `AZURE_SEARCH_*` / `AZURE_OPENAI_*`, gov 는 `GOV_SEARCH_*` / `GOV_OPENAI_*`. 같은 리소스를 공유해도 변수군은 분리
- **lawName 표기**: `_detect_law_filter` 은 prefix 매칭 → 인덱스 구축 시 `_LAW_NAMES` 목록과 표기 동일화. 불일치 시 필터 미적용으로 무관 법령이 top-k 에 혼입 가능
- **`semantic-config` 이름 하드코딩**: 다른 이름으로 구성 시 런타임 실패. 인덱스 빌더 스크립트에서도 동일 이름 사용 강제
- **Container App 시크릿 = 리비전 바인딩**: 시크릿 변경 후 새 리비전을 롤아웃하지 않으면 기존 프로세스에는 반영 안 됨
- **placeholder 재주입 회귀 경로**: 2026-04-03 커밋 `f2a620b` 에서 `.env.example` 의 키를 placeholder 로 바꾼 이후 배포 파이프라인이 그 placeholder 를 실 시크릿 대신 주입한 정황. 신규 연결 후 **배포 스크립트의 secret 치환 로직을 점검** 해야 재발 방지 (§7)
- **리랭커 임계값 1.5**: CHOI p03 기준 경험값 — 신규 인덱스에서는 재튜닝 가능성 열어둘 것
- **외부 구독 리소스 의존 재발 방지**: 신규 인덱스는 가급적 `rg-ejp-9638` 내부 구독에 배치. 외부 구독 사용 시 삭제·결제 중단 이벤트를 본 계정 Activity Log 로 추적 불가 (choiasearchhh 사고 재현 가능성)

---

## 7. 후속 작업 (본 연결 완료 후)

1. 배포 파이프라인의 시크릿 치환 로직 점검 — placeholder 재주입 원인 추적
2. App Insights 도입 시 `LegalSearch 검색 오류` / `LEGAL_RAG_UNAVAILABLE` 카운터 추가 → 동일 사고 조기 감지
3. koreacentral consolidation 플랜 작성 및 실행 (`docs/plans/2026-04-20-ai-search-koreacentral-consolidation.md`) — 본 가이드의 endpoint/key 만 교체하면 재적용 가능
4. `_LAW_NAMES` 리스트 코드 하드코딩 → 인덱스 메타로 이전 가능성 검토 (장기, 선택)
