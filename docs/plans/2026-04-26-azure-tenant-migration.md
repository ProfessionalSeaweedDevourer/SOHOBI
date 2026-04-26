# SOHOBI Azure 별도 테넌트·구독 이전 기획안

> 작성일: 2026-04-26
> 상태: **문서화 단계** (실행 미착수)
> 동기 메모: `~/.claude/.../memory/project_rg_ejp_migration.md` (2026-04-20)
> Claude 내부 플랜 사본: `~/.claude/plans/azure-vast-owl.md`

## Context

`rg-ejp-9638` 산하 모든 SOHOBI 인프라는 현재 `eric.park@miee.dev` 테넌트 산하 구독에 있다. 사용자는 이 전체를 **별도 테넌트(Tenant B) + 별도 구독(Subscription B)** 으로 이전할 예정이다.

**왜 이전인가**: 장기 운영·계정 분리 전략 (2026-04-20 결정). 본 문서는 사용자가 직접 기획을 요청한 시점(2026-04-26)에 작성된 1차 기획안이며, 실행 일정은 미정.

**제약**:
- 테넌트가 다르므로 `az account move`/`az resource move` 사용 불가 → **데이터 export/import 방식만 가능**
- Cutover 다운타임 허용: **1~2시간 점검**
- AI Search 인덱스는 외부 계정 접근 차단 사고를 겪었으므로(과거 `choiasearchhh` 사고 맥락), 신규 구독에서 **소스에서 재빌드**. 단 소스 위치 자체가 팀원 접촉 후에야 확정 가능 → 별도 워크스트림으로 분리
- IaC 미존재. 이번 이전을 기회로 **프로젝트 리소스 전부 Bicep화**

**최종 목표**: 1~2시간 cutover 윈도우로 sohobi.net 트래픽이 신규 구독 Container App으로 전환되고, 기존 세션·로그·위치 DB는 모두 보존된 상태로 서비스 정상 동작.

---

## 이전 대상 분류

### 데이터 이전 필수 (Stateful)
| 리소스 | 도구 | 데이터 크기 추정 | 점검 윈도우 영향 |
|--------|------|------------------|------------------|
| Cosmos DB (`sessions`, `roadmap_votes`, `feedback`, `checklists`) | `azure-cosmos` SDK 기반 export/import 스크립트 | 수십 MB ~ 수백 MB | freeze + 증분 복제 |
| Azure PostgreSQL Flexible (위치/상권 데이터) | `pg_dump` / `pg_restore` | 수백 MB ~ GB | 사전 dump 후 freeze 시 증분만 |
| Blob Storage (`sohobi9638logs`) | `azcopy sync` | GB 단위(append blob) | freeze 후 마지막 sync |

### 재빌드 (Source-driven)
| 리소스 | 방법 | 리스크 |
|--------|------|--------|
| AI Search `legal-index` | 소스 PDF/JSON에서 재인덱싱 (`backend/plugins/legal_search_plugin.py`) | **소스 위치 미확정** — 팀원 접촉 필요 |
| AI Search `gov-programs-index` | 소스에서 재인덱싱 (`backend/plugins/gov_support_plugin.py`) | 동일 + Function App 자동수집 파이프라인 재구성 |

### 재배포 (Stateless)
| 리소스 | 방법 |
|--------|------|
| Container App `sohobi-backend` | 신규 ACR push → Container App 신규 생성 |
| Static Web Apps (sohobi.net) | GitHub Actions workflow 재구성 |
| Azure OpenAI 배포 | 신규 리소스에 동일 deployment 이름으로 재배포 |
| DNS Zone | Cutover 옵션별 분기 (Phase 2 참조) |

---

## 신규 구독 사전 명명 규약

| 항목 | 기존 | 신규 (제안) |
|------|------|-------------|
| Resource Group | `rg-ejp-9638` | `rg-sohobi-prod` |
| Container App | `sohobi-backend` | `sohobi-backend` (동일) |
| Storage Account (logs) | `sohobi9638logs` | `sohobistoragelogs` (글로벌 unique) |
| Cosmos Account | (현 이름) | `sohobi-cosmos` |
| PostgreSQL | (현 이름) | `sohobi-pg` |
| AI Search | (현 이름 2개) | `sohobi-search-legal`, `sohobi-search-gov` |
| ACR | (현 이름) | `sohobiacr` |

---

## 단계별 실행 플랜

### Phase 0 — 사전 준비 (D-7 ~ D-1, 무중단)

1. **AI Search 소스 데이터 조사 워크스트림 분기**
   - 법령/정부지원사업 raw source 보유 팀원 식별 → Slack/이슈로 공식 요청
   - 소스 부재 시 fallback: 법제처 OpenAPI·정부24 API 재수집 파이프라인 설계
   - 본 워크스트림은 cutover 일정과 분리. AI Search는 **cutover 후 백필**해도 되도록 router에서 일시적 fallback 처리(아래 8 참조)

2. **Bicep IaC 작성**
   - 신규 디렉토리 `infra/bicep/` 생성. 모듈 분리:
     - `main.bicep` (RG 단위 entrypoint)
     - `modules/container-app.bicep` (ACR + Container App + managed identity)
     - `modules/cosmos.bicep`
     - `modules/postgres.bicep`
     - `modules/storage.bicep`
     - `modules/ai-search.bicep`
     - `modules/openai.bicep`
     - `modules/static-web-app.bicep`
     - `modules/dns.bicep`
     - `modules/log-analytics.bicep`
   - `.github/workflows/deploy-infra.yml` 신설 (manual dispatch, what-if 출력 후 apply)
   - 기존 `rg-ejp-9638` 구성은 `az resource list` + Portal 비교로 역공학 (CLAUDE.md 환경변수 참조)

3. **신규 Azure 계정/테넌트/구독 발급 및 OIDC Federated Credential 등록**
   - GitHub repo의 federated credential subject에 신규 Tenant B의 App Registration 추가
   - GitHub secrets: `AZURE_CLIENT_ID_B`, `AZURE_TENANT_ID_B`, `AZURE_SUBSCRIPTION_ID_B` 신규 등록 (기존 secret은 cutover까지 보존)

4. **신규 구독에 인프라 프로비저닝**
   - `deploy-infra.yml --target=B` 실행 → Bicep what-if → apply
   - Cosmos는 빈 컨테이너만, AI Search는 빈 인덱스만 생성. RBAC: Container App managed identity → Cosmos/Blob/Search 데이터 평면 권한 부여

5. **Cosmos export/import 스크립트 작성**
   - `scripts/migrate/cosmos_export.py`: 4개 컨테이너 → JSON Lines (gzip) export
   - `scripts/migrate/cosmos_import.py`: JSONL → 신규 Cosmos 입력. 멱등(upsert by id)
   - `--since <ISO ts>` 인자로 증분 export 지원 (cutover 시 마지막 1~2시간 데이터만 재push)

6. **PostgreSQL 사전 dump 리허설**
   - `pg_dump` (구) → `pg_restore` (신) 1회 dry-run. 스키마/인덱스/시퀀스 일치 확인
   - cutover 시 동일 명령어 재실행 예정

7. **Blob Storage azcopy 사전 sync**
   - `azcopy sync` (구→신) 1회 실행하여 대량 전송 미리 처리
   - cutover 시점 마지막 sync는 분 단위로 끝나도록 함

### Phase 1 — 코드 측 듀얼 환경 지원 준비 (D-3, 무중단)

8. **Backend 환경변수 추상화 검증**
   - 백엔드 코드는 모든 Azure 자원을 환경변수로 주입받음 — 코드 변경 없음 확인
   - 단, `legal_search_plugin.py` / `gov_support_plugin.py`에 **인덱스 비어있을 시 fallback 응답** 추가 (AI Search 백필 전까지 동작 보장):
     - `search_results == []` → "관련 정보 일시 점검 중" 안내 또는 LLM-only 응답
   - 변경 PR: `feat/park-search-empty-fallback` (이전 작업과 독립적으로 머지 가능)

9. **신규 구독 환경에서 스테이징 부하 테스트**
   - 신규 Container App에 동일 image 배포, `.env`에 신규 endpoint 주입
   - 별도 임시 도메인(예: `staging.sohobi.net` 또는 Container App default FQDN)으로 E2E TC 실행
   - CLAUDE.md "PR 생성 후 테스트 실행 루틴"을 그대로 적용

### Phase 2 — Cutover (점검 D-day, 1~2시간 윈도우)

**T-0**: 사용자 점검 공지 게시. 프론트엔드에 read-only 배너 표시 또는 503 maintenance 페이지 전환

**T+0:00 ~ T+0:10** — 트래픽 차단
- 기존 Container App `sohobi-backend`에 ingress 차단 규칙 적용 또는 maintenance 페이지로 redirect
- 백엔드 자체는 살려두고 마지막 데이터 추출만 수행

**T+0:10 ~ T+0:40** — 데이터 최종 이전
- Cosmos: `cosmos_export.py --since <D-1>` → `cosmos_import.py` (증분만)
- PostgreSQL: 마지막 `pg_dump` → `pg_restore`. (위치 데이터는 거의 정적이므로 사실상 사전 dump로 충분)
- Blob: `azcopy sync --delete-destination=false` 마지막 실행
- 검증: 컨테이너별 row count, 최신 row id 일치 확인

**T+0:40 ~ T+0:55** — 신규 환경 활성화
- 신규 Container App `.env`에 신규 Cosmos/PG/Blob/OpenAI 키 설정
- 이미 배포된 신규 image revision activate
- E2E smoke test (CLAUDE.md TC 루틴): `/api/v1/query`, 세션 생성, 로그 저장

**T+0:55 ~ T+1:30** — DNS 전환

**옵션 A**: 신규 계정의 Azure DNS Zone으로 완전 이전
- 신규 구독에 sohobi.net DNS Zone 생성 → 모든 record 복제
- 도메인 등록사(가비아 등)에서 NS record를 신규 zone NS로 변경
- 장점: 양 계정 완전 분리. 단점: NS 전파 최대 48시간(이 시간 동안 일부 사용자는 구 zone 응답)

**옵션 B**: 기존 DNS Zone 유지, A/CNAME만 변경
- 구 zone에서 sohobi.net A record를 신규 Container App custom domain IP로 변경
- 장점: TTL만큼만 다운타임(보통 5분~1시간). 단점: 구 계정 종속 유지

**권장**: 즉시 cutover 안정성을 위해 **옵션 B로 시작 → 안정화 후 옵션 A로 2차 마이그**. 두 단계 분리

**T+1:30** — 점검 종료
- 503 페이지 해제. 사용자 트래픽 수용
- 모니터링 30분 (Container App revision 로그, Cosmos 4xx/5xx 메트릭)

### Phase 3 — Post-cutover (D+1 ~ D+7, 무중단)

10. **AI Search 백필**
    - 소스 데이터 확보 후 신규 search service에 인덱싱 파이프라인 실행
    - 인덱스 채워지면 fallback 분기 제거 PR

11. **NAM2 Function App 재배치**
    - 정부지원사업 자동수집 Function App을 신규 구독에 신규 배포 + AI Search endpoint 신규로 변경

12. **구 계정 cleanup**
    - 1주일 모니터링 후 구 `rg-ejp-9638` snapshot 보관(Storage Account 백업 → cold tier) 후 RG 삭제
    - 옵션 A 선택했다면 구 DNS Zone 삭제, 옵션 B면 A record 신규 IP로 영구 유지

---

## 핵심 파일 / 신규 작성 산출물

| 경로 | 용도 |
|------|------|
| `infra/bicep/main.bicep` + `modules/*.bicep` | 신규 구독 인프라 IaC (신규) |
| `.github/workflows/deploy-infra.yml` | Bicep what-if/apply 워크플로우 (신규) |
| `scripts/migrate/cosmos_export.py` | Cosmos 컨테이너 JSONL export (신규) |
| `scripts/migrate/cosmos_import.py` | JSONL → 신규 Cosmos upsert (신규) |
| `scripts/migrate/pg_dump_restore.sh` | PG dump→restore wrapper (신규) |
| `scripts/migrate/blob_sync.sh` | azcopy sync wrapper (신규) |
| `backend/plugins/legal_search_plugin.py` | 빈 인덱스 fallback 분기 추가 |
| `backend/plugins/gov_support_plugin.py` | 동일 fallback 분기 추가 |
| `docs/runbooks/azure-cutover.md` | cutover 당일 단계별 runbook (신규) |

---

## 검증 (End-to-end)

### Phase 0~1 검증
```bash
# Bicep what-if
az deployment sub what-if --location koreacentral \
  --template-file infra/bicep/main.bicep \
  --parameters environment=staging

# 스테이징 백엔드 E2E
curl -s -X POST https://<신규-staging-fqdn>/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트 질문"}'
```

### Cutover 직후 검증
```bash
# 1. 백엔드 헬스
curl -s "$NEW_BACKEND_HOST/api/v1/logs?type=queries&limit=5"

# 2. 세션 생성→조회 (Cosmos write/read)
curl -s -X POST "$NEW_BACKEND_HOST/api/v1/query" -d '{...}'
# → 응답에 session_id 있으면 동일 id로 재요청

# 3. 위치 에이전트 (PostgreSQL read)
curl -s -X POST "$NEW_BACKEND_HOST/api/v1/query" \
  -d '{"question": "강남역 카페 상권"}'

# 4. 로그가 신규 Blob Storage append blob에 기록되는지
az storage blob show --account-name sohobistoragelogs \
  --container-name sohobi-logs --name queries.jsonl

# 5. AI Search fallback 작동 (인덱스 비어있을 때)
curl -s -X POST "$NEW_BACKEND_HOST/api/v1/query" \
  -d '{"question": "음식점 영업신고 절차"}'
# → 응답이 5xx 아닌 LLM-only 안내 응답이어야 함
```

### 데이터 무결성 검증
```bash
# Cosmos row count 일치
python scripts/migrate/cosmos_verify.py --container sessions
# → 구/신 row count diff = 마지막 freeze 이후 증분 (0이어야 정상)

# PostgreSQL row count 일치
psql $OLD_PG -c "SELECT count(*) FROM sangkwon_sales"
psql $NEW_PG -c "SELECT count(*) FROM sangkwon_sales"
```

---

## 리스크와 완화

| 리스크 | 영향 | 완화책 |
|--------|------|--------|
| AI Search 소스 데이터 미확보 | gov/legal 응답 품질 저하 | fallback 분기로 503 회피 + 사용자 안내 + 백필 워크스트림 별도 운영 |
| OIDC federated credential subject 충돌 | GitHub Actions 배포 실패 | 신규 secret을 `_B` suffix로 병행, 워크플로우에서 환경별 분기 |
| Cosmos 증분 export 누락 | 일부 세션/피드백 데이터 손실 | freeze 시점 timestamp 기록 + post-cutover 1시간 동안 구 환경에 read-only mount하여 재export 가능하게 유지 |
| DNS NS 전파 지연 (옵션 A) | 일부 사용자 구 환경 도달 → 503 | 옵션 B(A record 변경)로 1차 cutover, 옵션 A는 안정화 후 별도 이벤트 |
| Container App custom domain TLS 인증서 재발급 | 인증서 발급 지연으로 cutover 지연 | cutover 전날 신규 환경에서 managed cert 미리 발급(staging.sohobi.net 등) |
| 구 계정 권한 만료/접근 차단 (AI Search 사고 재현) | 데이터 export 자체 불가 | Phase 0의 Cosmos export·PG dump·Blob sync는 cutover **이전에** 1차 실행 완료. cutover 시는 증분만 |

---

## 비포함 (의도적 제외)

- **온프레미스 Oracle DB**: 별도 네트워크에 있고 본 이전 범위 아님. 기존 연결 설정만 신규 Container App에 동일하게 주입
- **외부 공공 API 키** (서울시, VWorld, 카카오, 정부24 등): 환경변수만 신규 환경에 복제
- **Azure OpenAI 모델 업그레이드/변경**: 본 이전에서는 동일 deployment 이름·모델 유지. 모델 변경은 별도 이벤트
- **AI Search 인덱스 export/import**: 사용자 결정에 따라 소스 재빌드만 수행

---

## 다음 액션 (실행 트리거 시)

1. 신규 Azure 계정/테넌트 발급 일정 확정
2. AI Search 소스 데이터 보유 팀원 식별 (가장 큰 미확정 변수)
3. 위 두 가지 확정 후 Phase 0의 Bicep 작성 PR을 가장 먼저 시작 (`infra/bicep/`)
