# 내부 AI Search 프로비저닝: `sohobi-search-kr` koreacentral Basic

## 배경

- 2026-04-20 외부 Azure 구독 Phase 1 절단 handoff: [docs/session-reports/2026-04-20-external-sub-phase1-cutoff-handoff.md](../../session-reports/2026-04-20-external-sub-phase1-cutoff-handoff.md)
- 승인된 실행 플랜: `~/.claude/plans/rg-ejp-imperative-newell.md` (Phase 1 완료 시점까지 기록)
- 현 상태: `GOV_SEARCH_ENDPOINT` / `GOV_OPENAI_ENDPOINT` env 제거, Container App 신규 리비전 (`sohobi-backend--ext-cutoff-20260420`) 트래픽 100%. `gov_support_plugin` 무기능 상태. 원본 데이터 재확보는 다른 팀원에게 이관

## 범위

본 문서는 Phase 2 (`sohobi-search-kr` 프로비저닝) 를 **"왜·무엇을·얼마에"** 관점으로 기획한다. 실제 `az search service create` 등 CLI 절차는 승인된 플랜 문서가 source-of-truth. 본 문서는 비용·스키마·의존성 중심.

**범위 외** (별도 라인):

- 원본 데이터 확보 (`gov-programs-index` 재구축용 CSV/JSON) — 팀원 이관
- Phase 4 인덱스 upload 스크립트 (`scripts/ingest_gov_programs.py`) — 원본 확보 후 착수
- Phase 5 재연결 (Container App secret/env 복원)
- `legal-index` 신규 구축 — 본 리소스 재사용은 가능하나 본 문서 범위 외 ([legal-index-reconnect.md](legal-index-reconnect.md) 참조)

## 긴급도 (비긴급)

**rg-ejp-9638 이 유지되는 한 시급하지 않다**:

- 외부 호출은 이미 Phase 1 에서 0 건 (교육기관 청구 리스크 해소).
- 사용자 노출은 userchat 내부 배너 ([frontend/src/components/MaintenanceNotice.jsx](../../../frontend/src/components/MaintenanceNotice.jsx)) 로 고지됨.
- 복구 timeline 은 **원본 데이터 확보 시점에 종속** — 인프라보다 데이터가 bottleneck.

따라서 **go 결정은 원본 데이터 확보 완료 직후** 가 자연스럽다. 그 이전 선반영은 월 ~$75 비용 loss 없이 가능하나 실익 없음.

---

## 1. 리소스 정의

| 항목 | 값 | 근거 |
|---|---|---|
| 리소스명 | `sohobi-search-kr` | 내부 convention (`sohobi-*`), kr suffix 로 외부 `sohobi-search` (centralus) 와 구분 |
| 리전 | `koreacentral` | 사용자 결정 — 백엔드 Container App 과 동일 리전으로 latency·bandwidth 최소화 |
| SKU | `Basic` | 단일 인덱스 ~수천~수만 문서 규모. Free 는 semantic reranker 미지원 |
| Resource Group | `rg-ejp-9638` | 기존 리소스 그룹 재사용 |
| 용도 | `gov-programs-index` 단일 인덱스. 향후 `legal-index` 병용 가능 | Basic SKU 는 인덱스 15개·스토리지 2GB 허용 — 두 인덱스 수용 여유 |

## 2. Cost Breakdown

| 항목 | 월 추정 | 비고 |
|---|---|---|
| Basic SKU 기본료 | ~$75 (KRW 약 103,000원, 2026-Q2 환율 기준) | Azure AI Search Basic 고정료. 단위 시간 billing |
| 쿼리 요청 | 포함 (per-request 요금 없음) | Basic SKU 쿼리는 SKU 내 포함 |
| 벡터 스토리지 | 포함 2GB 한도 | `text-embedding-3-large` 3072d × 문서 수. 예: 1만 문서 → 약 120MB 벡터 ≈ 한도 내 |
| Outbound bandwidth | ~$0.05-0.09/GB | 같은 리전 Container App 간은 자동 최소. 외부 접근 없으면 사실상 0 |
| Semantic reranker | 포함 (Basic 부터 사용 가능) | Free SKU 는 미지원 |

**연간 ~$900 고정**. `rg-ejp-9638` 장기 유지 가정 하 감내 가능. rg-ejp-9638 이전 (별도 전략 — Memory `project_rg_ejp_migration.md` 참조) 시 해당 구독으로 이전 대상.

## 3. 인덱스 스키마 (`gov-programs-index`, v1)

복구 대상 인덱스가 만족해야 할 **런타임 계약**. 기존 외부 인덱스의 스키마를 복원하는 것이 아니라, 플러그인 코드가 기대하는 필드 세트를 **재구축** 한다.

### 3-1. 필드 (플러그인 `select` 역산)

[backend/plugins/gov_support_plugin.py:254-273](../../../backend/plugins/gov_support_plugin.py#L254-L273) select 절 기준:

| 필드 | 타입 | 속성 | 용도 |
|---|---|---|---|
| `id` | Edm.String | key, retrievable | document key |
| `program_name` | Edm.String | searchable, retrievable | 지원사업명 |
| `field` | Edm.String | retrievable | 분야 (창업·금융·판로 등) |
| `summary` | Edm.String | searchable, retrievable | 요약 |
| `target` | Edm.String | searchable, retrievable | 신청 대상 |
| `support_content` | Edm.String | searchable, retrievable | 지원 내용 |
| `criteria` | Edm.String | searchable, retrievable | 선정 기준 |
| `apply_deadline` | Edm.String | retrievable | 신청 마감 |
| `apply_method` | Edm.String | retrievable | 신청 방법 |
| `org_name` | Edm.String | filterable, retrievable | 주관 기관 |
| `phone` | Edm.String | retrievable | 문의 전화 |
| `url` | Edm.String | retrievable | 원문 링크 |
| `support_type` | Edm.String | filterable, retrievable | 단일 대표 지원 유형 |
| `target_region` | Collection(Edm.String) | filterable, retrievable | 지역 다중값 |
| `startup_stages` | Collection(Edm.String) | filterable, retrievable | 창업 단계 다중값 |
| `industries` | Collection(Edm.String) | filterable, retrievable | 업종 다중값 (`not industries/any(i: i eq '...')` 필터 사용 — [gov_support_plugin.py:242-243](../../../backend/plugins/gov_support_plugin.py#L242-L243)) |
| `support_types` | Collection(Edm.String) | filterable, retrievable | 지원 유형 다중값 |
| `max_amount` | Edm.Int64 | filterable, retrievable | 최대 지원금 (`max_amount ge ?` 필터 사용 — [gov_support_plugin.py:240](../../../backend/plugins/gov_support_plugin.py#L240)) |
| `quality_score` | Edm.Double | retrievable | 품질 가중치 |
| `embedding` | Collection(Edm.Single) | searchable (vector) | 벡터 필드명 하드코딩 — [gov_support_plugin.py:212](../../../backend/plugins/gov_support_plugin.py#L212) `fields="embedding"` |

### 3-2. 벡터 설정

- 필드명: **`embedding`** (legal-index 의 `content_vector` 와 **다름** — 하드코딩 충돌 주의).
- 알고리즘: HNSW.
- 차원: **3072** (`text-embedding-3-large`). Container App env `GOV_EMBEDDING_DEPLOYMENT=text-embedding-3-large` 와 정합. 재구축 시 반드시 동일 모델 버전 사용 — 차원 불일치 시 쿼리 실패.

### 3-3. 시맨틱 리랭커

- configuration 이름: **`sohobi-semantic`** ([gov_support_plugin.py:252](../../../backend/plugins/gov_support_plugin.py#L252) 하드코딩)
- title field 권장: `program_name`
- content fields 권장: `summary`, `support_content`, `criteria`
- 임베딩 모델: 내부 `ejp-9638-resource` 의 `text-embedding-3-large` v1 배포 재사용 (legal-index 와 공유 — 쿼터 통합 관리 필요)

## 4. Ingest 전략 (원칙만)

원본 데이터 확보 경로는 이관되었으므로 본 문서는 인덱스 쪽 계약만 명시한다. 실제 스크립트는 Phase 4 에서 작성.

- 적재 형식: `documents-for-indexing.jsonl` — 라인당 1 document, 위 §3-1 필드명과 정확 일치
- 임베딩 생성: 내부 `text-embedding-3-large` deployment 로 `summary + support_content + criteria` 합성 텍스트 임베딩
- 배치 크기: Azure SDK `SearchClient.upload_documents` 1000건 단위 (Basic SKU throughput 상 무리 없음)
- 쿼터 사전 확인:

  ```bash
  az cognitiveservices account deployment list \
    --name ejp-9638-resource -g rg-ejp-9638 \
    --query "[?name=='text-embedding-3-large'].{name:name,tpm:properties.currentCapacity,rate:properties.rateLimits}" -o table
  ```

## 5. 재연결 단계 의존성

```
[팀원] 원본 데이터 확보 ─────┐
                              ├─> Phase 4: 인덱스 생성 + ingest
[본 문서 승인] Phase 2 프로비저닝 ──┘              │
                                                   ├─> Phase 5: secret/env 복원 (rg-ejp-imperative-newell.md §Phase 5)
                                                   │       │
                                                   │       └─> 스모크 쿼리 PASS
                                                   │
                                                   └─> Phase 6: .env.example / handoff 갱신 + 점검 배너 제거
```

**임계 경로**: 원본 데이터 확보 (이관 작업자 주도) → Phase 2 실행 시점 결정. Phase 2 는 단독으로 언제든 실행 가능하나 Phase 4 와 근접 배치 권장 (유휴 비용 최소화).

## 6. Decision Gates

Phase 2 **go** 결정을 위한 체크리스트. 전부 충족될 때까지 보류:

- [ ] (data) 원본 데이터 확보 경로 확정 — 교육기관 인계 / 내부 백업 / 공공 API 재크롤 / 영구 비활성 중 택일 (팀원 이관)
- [ ] (data) 적어도 인덱스 문서 수 추정치 확보 (Basic SKU 2GB 한도 검증용)
- [ ] (cost) 월 ~$75 비용 승인 — **rg-ejp-9638 이 유지되는 한** 자동 승인 범위로 간주 가능. rg-ejp 이전 전략 ([memory: project_rg_ejp_migration.md](~/.claude/projects/-Users-eric-j-park-Documents-GitHub-SOHOBI/memory/project_rg_ejp_migration.md)) 과 충돌 없는지 재확인
- [ ] (quota) koreacentral 리전에서 `text-embedding-3-large` TPM/RPM 쿼터 확인 — 부족 시 eastus2 의 기존 배포 재사용 (cross-region 임베딩 호출)
- [ ] (영구 비활성 택시) 만약 "영구 비활성" 로 결정되면 본 문서 실행 불필요 → 점검 배너를 "정부지원 검색 기능 종료 안내" 로 교체

## 7. Traps

- **벡터 필드명 차이**: gov 는 `embedding`, legal 은 `content_vector`. 같은 Search 리소스에 두 인덱스 배치 시 필드명 공유되지 않으므로 혼동 주의. 스키마 JSON 리뷰 시 플러그인 하드코딩과 대조 필수
- **차원 불일치 영구 오류**: 인덱스 생성 시 차원을 잘못 고정하면 재인덱스만 답. 임베딩 모델 변경 시 전체 재적재
- **외부 구독 벡터 재사용 금지**: Phase 1 의 외부 리소스 무접근 원칙에 따라 외부 `sohobi-search` 에 남아있을 벡터 dump 로 shortcut 시도 불가. 반드시 원본 텍스트에서 내부 embedding 으로 재생성
- **배포 파이프라인 placeholder 재주입**: 2026-04-03 `f2a620b` 이후 `.env.example` placeholder 가 Container App secret 으로 자동 주입된 사고 이력 있음. Phase 6 `.env.example` 갱신 시 placeholder 형태 금지·실제 값 기재
- **Single-revision mode**: Phase 5 재연결 시 이전 리비전 (`sohobi-backend--ext-cutoff-20260420`) 을 롤백 대비 살려두려면 multiple-revision mode 확인:

  ```bash
  az containerapp show --name sohobi-backend -g rg-ejp-9638 \
    --query "properties.configuration.activeRevisionsMode"
  ```

- **PII 검토**: 원본 데이터에 신청 담당자 개인정보가 포함될 경우 인덱스 적재 전 마스킹. `phone`, `apply_method` 필드에 담당자 휴대폰·이메일 혼입 가능성 있음

---

## 연관 문서

- 승인된 실행 플랜: `~/.claude/plans/rg-ejp-imperative-newell.md` (Phase 1~6 Azure CLI 절차)
- Phase 1 handoff: [docs/session-reports/2026-04-20-external-sub-phase1-cutoff-handoff.md](../../session-reports/2026-04-20-external-sub-phase1-cutoff-handoff.md)
- 법무 인덱스 연결 가이드 (본 리소스 재사용 후보): [legal-index-reconnect.md](legal-index-reconnect.md)
- 백엔드 플러그인 계약: [backend/plugins/gov_support_plugin.py](../../../backend/plugins/gov_support_plugin.py)
