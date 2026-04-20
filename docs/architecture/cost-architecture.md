# SOHOBI Azure 비용 아키텍처

> **데이터 스냅샷**: 2026-04-20 기준 / 측정 구간 2026-03-21 ~ 2026-04-19 (30일)
> **출처**: `az rest` Cost Management Query API (`Microsoft.CostManagement/query`)
> **구독**: `ME-M365EDU102388-joowonjeong-1` (5919b1b2…1661b)
> **리소스 그룹**: `rg-ejp-9638` (SOHOBI 전용)

---

## 1. 개요 & TL;DR

SOHOBI는 `rg-ejp-9638`에 13개 Azure 리소스를 운영 중이며, **최근 30일 실측 비용은 $95.76**다.
비용 절반 이상(약 54%)은 **PostgreSQL Flexible Server**가 차지한다.

| 카테고리 | 30일 비용 | 비중 |
|---------|-----------|------|
| PostgreSQL (compute + storage) | $52.05 | 54.4% |
| Microsoft Defender for Cloud (CSPM/Storage/AI/Cosmos) | $20.50 | 21.4% |
| Azure Container Apps + ACR | $14.91 | 15.6% |
| Azure OpenAI (Foundry GPT5 + 기타) | $8.03 | 8.4% |
| 기타 (Cosmos, Log Analytics, DNS, Blob, Bandwidth) | $0.27 | 0.3% |
| **합계** | **$95.76** | **100%** |

**3대 변동 요인**:
1. **PG Flex 가동 시간** (B2s Burstable, 24/7) — 정지하면 컴퓨트 비용 0
2. **Defender for Cloud 플랜** — 리소스 추가 시 자동 과금 ($20/mo는 학습 환경에 비해 큼)
3. **Azure OpenAI 토큰** — gpt-5.4 시리즈 사용량에 비례

**즉시 검토 권장**:
- Defender for Cloud 플랜 다운그레이드 (Free 티어로 전환 시 ~$20/월 절감)
- 외부 의존인 **Azure AI Search (`choiasearchhh`, CHOI 소유)** 비용은 본 구독에서 추적 불가 → CHOI 협의 필요 (8장 참조)

**독자**: PARK(인프라 담당), 팀 리더(예산 결정), 신규 합류자(원가 감 잡기)

---

## 2. 리소스 인벤토리 (rg-ejp-9638)

### 2.1 컴퓨팅

| 리소스 | 타입 | SKU/스펙 | 리전 | 청구 모델 |
|--------|------|----------|------|-----------|
| `sohobi-backend` | Container Apps | 0.5 vCPU / 1Gi / minReplicas 1 / maxReplicas 3 | KR Central | Consumption (vCPU·메모리·요청 시간당) |
| `sohobi-env` | Managed Environment | — | KR Central | $0 (자체 과금 없음) |
| `sohobi-frontend` | Static Web Apps | Free | East US 2 | $0 (대역폭 100GB/mo 한도) |

### 2.2 데이터

| 리소스 | 타입 | SKU/스펙 | 리전 | 청구 모델 |
|--------|------|----------|------|-----------|
| `sohobi-db-prod` | PostgreSQL Flex | Standard_B2s Burstable / 32GB P4 / 단일 인스턴스 / v17 | KR Central | 시간당 + 스토리지 GB |
| `sohobi-ejp-9638` | Cosmos DB | Serverless / GlobalDocumentDB / 단일 East US 2 | East US 2 | RU 사용량 + 저장 GB |

### 2.3 AI

| 리소스 | 타입 | SKU/스펙 | 리전 | 청구 모델 |
|--------|------|----------|------|-----------|
| `ejp-9638-resource` | AI Services (OpenAI) | S0 / 8개 deployment | East US 2 | 모델별 입출력 토큰당 |

**활성 deployment**:
- `gpt-4.1-mini`, `gpt-5.4-mini`, `gpt-5.4`, `gpt-5.4-pro`
- `o3`, `o4-mini`
- `text-embedding-3-large`
- `Kimi-K2.5` (사용 빈도 확인 필요 — 비활성이라면 제거 권장)

**외부 의존 (별도 RG)**:

| 리소스 | 위치 | 청구 책임 | 비고 |
|--------|------|-----------|------|
| `choiasearchhh` (Azure AI Search) | CHOI 소유 RG | **CHOI 개인 구독** | 본 구독에서 가시성 없음 — 8장 협의 사항 참조 |

### 2.4 보조 리소스

| 리소스 | 타입 | SKU/스펙 | 리전 | 청구 모델 |
|--------|------|----------|------|-----------|
| `sohobi9638acr` | Container Registry | Basic | KR Central | 일 정액 (~$0.167/일) |
| `sohobi9638logs` | Storage Account | Standard_LRS Hot StorageV2 | KR Central | GB·트랜잭션·송신 |
| `sohobi9638logs-…systemTopic` | EventGrid System Topic | — | KR Central | 100만 이벤트당 $0.60 |
| `workspace-rgejp9638yX5E` | Log Analytics | Pay-as-you-go | KR Central | GB 수집 |
| `sohobi.net` | DNS Zone | — | global | 호스팅 + 100만 쿼리당 |
| `sohobi.net` | Domain Registration | — | global | 연 정액 (.net) |

---

## 3. 실측 비용 (2026-03-21 ~ 2026-04-19, 30일)

### 3.1 리소스별 30일 비용

| 리소스 | 서비스 | 30일 합계 | 일평균 | 월 환산 |
|--------|--------|----------:|-------:|--------:|
| `sohobi-db-prod` | PostgreSQL Flex | $55.38 | $1.85 | $56.22 |
| `ejp-9638-resource` | AI Services | $12.61 | $0.42 | $12.81 |
| `sohobi9638logs` | Storage (대부분 Defender) | $12.60 | $0.42 | $12.79 |
| `sohobi-backend` | Container Apps | $8.60 | $0.29 | $8.73 |
| `sohobi9638acr` | Container Registry | $6.31 | $0.21 | $6.41 |
| `workspace-rgejp9638yX5E` | Log Analytics | $0.10 | $0.003 | $0.10 |
| `sohobi.net` | Azure DNS | $0.09 | $0.003 | $0.09 |
| `sohobi-ejp-9638` | Cosmos Serverless | $0.07 | $0.002 | $0.07 |
| **합계** | | **$95.76** | **$3.19** | **$97.22** |

> **주의**: `sohobi9638logs` 비용 $12.60 중 약 $8.27이 **Microsoft Defender for Storage** 플랜 (구독 레벨 활성). Storage 본체 사용은 $0.007에 불과.

### 3.2 서비스 카테고리별 30일 비용

| 카테고리 | 세부 | 30일 비용 | 비중 |
|---------|------|----------:|-----:|
| **PostgreSQL** | Flex Burstable BS 컴퓨트 | $49.30 | 51.5% |
| **PostgreSQL** | Flex 스토리지 | $2.76 | 2.9% |
| **Defender for Cloud** | for Storage | $8.27 | 8.6% |
| **Defender for Cloud** | CSPM | $7.65 | 8.0% |
| **Defender for Cloud** | for AI Services | $4.58 | 4.8% |
| **Defender for Cloud** | for Cosmos DB | $0.01 | 0.0% |
| **Container Apps** | (Compute) | $8.60 | 9.0% |
| **Container Registry** | Basic | $6.31 | 6.6% |
| **Foundry Models** | Azure OpenAI GPT5 | $6.74 | 7.0% |
| **Foundry Models** | Azure OpenAI (기타) | $1.29 | 1.3% |
| **Log Analytics** | | $0.10 | 0.1% |
| **Azure DNS** | | $0.09 | 0.1% |
| **Cosmos DB** | Serverless + Data Transfer | $0.06 | 0.1% |
| **Storage** | Blob | $0.01 | 0.0% |
| **합계** | | **$95.76** | **100%** |

### 3.3 가격 변동 요인 (트래픽 vs 고정)

**고정비** (사용량 무관, 월 ~$72)
- PG Flex B2s 컴퓨트 (24/7 가동) — $49/월
- Defender for Cloud 플랜 4종 — $20/월
- ACR Basic 일 정액 — $5/월
- Domain 연정액 (.net ≈ $12/년) — $1/월
- DNS 호스팅 + Log Analytics 최소 보존 — $0.2/월

**변동비** (사용량 비례, 월 ~$25)
- AI Services 토큰 — $8/월 (현 트래픽 기준)
- Container Apps 활성 vCPU·메모리 시간 — $9/월
- PG Storage GB·IOPS — $3/월
- Cosmos RU·저장 — $0.07/월
- Storage 이그레스·트랜잭션 — $0.01/월

**결론**: 총비용 중 **약 75%가 고정비**. 트래픽이 0이 되어도 월 $72는 발생.

---

## 4. 비용 모델 & 단가 참조

| 리소스 | 공식 단가 페이지 | 핵심 단가 (KR Central / East US 2) |
|--------|------------------|-----------------------------------|
| Container Apps | https://azure.microsoft.com/pricing/details/container-apps/ | vCPU·sec $0.000024 / 메모리 GiB·sec $0.000003 / 요청 100만 $0.40 |
| PostgreSQL Flex | https://azure.microsoft.com/pricing/details/postgresql/flexible-server/ | B2s 시간당 $0.0832 (≈$60/월), P4 32GB $3.6/월 |
| Cosmos Serverless | https://azure.microsoft.com/pricing/details/cosmos-db/serverless/ | 100만 RU $0.25 / 저장 GB·월 $0.25 |
| Azure OpenAI | https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/ | 모델별 — gpt-5.4 시리즈, o3, o4-mini, embedding 등 입출력 토큰당 |
| Container Registry | https://azure.microsoft.com/pricing/details/container-registry/ | Basic 일 $0.167 |
| Storage (Hot LRS) | https://azure.microsoft.com/pricing/details/storage/blobs/ | GB·월 $0.018 / 쓰기 1만 $0.055 |
| Static Web Apps | https://azure.microsoft.com/pricing/details/app-service/static/ | Free 100GB/월 한도 — 초과 시 GB당 $0.20 |
| Log Analytics | https://azure.microsoft.com/pricing/details/monitor/ | 수집 GB $2.30 (Pay-as-you-go) |
| Azure DNS | https://azure.microsoft.com/pricing/details/dns/ | 호스팅 zone 월 $0.50 / 100만 쿼리 $0.40 |
| Defender for Cloud | https://azure.microsoft.com/pricing/details/defender-for-cloud/ | 플랜·리소스 종류별 — Storage·CSPM·AI 등 개별 과금 |

> 단가는 시점·환율·리전별로 변동. 본 표는 2026-04 기준 USD 표시가. 정확한 청구는 6장 동적 조회 매뉴얼로 확인.

---

## 5. 예산 수립 가이드

### 5.1 권장 월별 예산

| 시나리오 | 가정 | 월 예산 | 비고 |
|---------|------|--------:|------|
| **현상 유지** | 현재 트래픽 + Defender 그대로 | $115 | 실측 $97 + 안전마진 20% |
| **Defender 다운그레이드** | Defender Free 전환 | $90 | 실측 $77 + 안전마진 20% |
| **트래픽 5배 Burst** | AI 토큰·CA·Cosmos만 비례 증가 | $190 | 변동비 $25 → $125, 고정비 $65 그대로 |
| **PG 야간 정지** | 18시간/일만 가동 | $80 | PG 컴퓨트 $49 → $37 절감 |

### 5.2 Azure Budget 알람 설정

**현황**: 구독 전체에 `FDPOAzureBudget` $1500/월 설정됨 (학생 다수 공유 → SOHOBI 점유율 추적 불가).

**SOHOBI RG 단위 신규 알람 생성**:

```bash
# RG scope 예산 (RG 한정 청구액 추적)
az consumption budget create \
  --budget-name sohobi-rg-monthly \
  --amount 115 \
  --time-grain Monthly \
  --start-date 2026-05-01 \
  --end-date 2027-04-30 \
  --resource-group rg-ejp-9638 \
  --notifications-enabled true \
  --notification-key "warning_80pct" \
  --notification-threshold 80 \
  --notification-operator GreaterThan \
  --notification-contact-emails erik.j.park@gmail.com
```

> `--resource-group` 옵션이 ME 교육 구독에서 거부되면 5.3 우회책 사용.

### 5.3 RG 단위 예산이 거부될 경우 우회책

**원인**: ME-M365EDU 구독은 학생 공유 정책으로 RG-scope budget 생성 권한이 제한될 수 있음.

**우회책** — 태그 기반 추적:

```bash
# 모든 SOHOBI 리소스에 project=sohobi 태그 일괄 부여
for rid in $(az resource list -g rg-ejp-9638 --query "[].id" -o tsv); do
  az tag update --resource-id "$rid" --operation merge --tags project=sohobi
done

# Cost Analysis에서 태그 필터로 SOHOBI 비용만 추출
az rest --method post \
  --url "https://management.azure.com/subscriptions/$AZ_SUBSCRIPTION_ID/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
  --body '{"type":"ActualCost","timeframe":"MonthToDate","dataset":{"granularity":"None","aggregation":{"totalCost":{"name":"Cost","function":"Sum"}},"filter":{"tags":{"name":"project","operator":"In","values":["sohobi"]}}}}'
```

---

## 6. 동적 비용 조회 매뉴얼

> 모든 명령어는 macOS/Linux zsh 기준. 환경변수 `AZ_SUBSCRIPTION_ID=5919b1b2-b639-42e1-8678-c28553b1661b` 사전 설정 권장.

### 6.1 RG 전체 30일 비용

```bash
az rest --method post \
  --url "https://management.azure.com/subscriptions/$AZ_SUBSCRIPTION_ID/resourceGroups/rg-ejp-9638/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
  --body '{"type":"ActualCost","timeframe":"Custom","timePeriod":{"from":"'$(date -v-30d +%Y-%m-%d)'T00:00:00Z","to":"'$(date +%Y-%m-%d)'T23:59:59Z"},"dataset":{"granularity":"None","aggregation":{"totalCost":{"name":"Cost","function":"Sum"}},"grouping":[{"type":"Dimension","name":"ResourceId"}]}}'
```
> **언제**: 월말 정산 / **무엇**: 리소스별 30일 누적 USD

### 6.2 서비스 카테고리별 분포

```bash
az rest --method post \
  --url "https://management.azure.com/subscriptions/$AZ_SUBSCRIPTION_ID/resourceGroups/rg-ejp-9638/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
  --body '{"type":"ActualCost","timeframe":"MonthToDate","dataset":{"granularity":"None","aggregation":{"totalCost":{"name":"Cost","function":"Sum"}},"grouping":[{"type":"Dimension","name":"MeterCategory"},{"type":"Dimension","name":"MeterSubCategory"}]}}'
```
> **언제**: 비용 급증 원인 분석 / **무엇**: 어떤 서비스가 얼마인지

### 6.3 리소스 SKU 스냅샷

```bash
az containerapp show -n sohobi-backend -g rg-ejp-9638 \
  --query "properties.template.{cpu:containers[0].resources.cpu, mem:containers[0].resources.memory, min:scale.minReplicas, max:scale.maxReplicas}"

az postgres flexible-server show -n sohobi-db-prod -g rg-ejp-9638 \
  --query "{sku:sku, storage:storage, ha:highAvailability.mode}"

az cognitiveservices account deployment list -n ejp-9638-resource -g rg-ejp-9638 -o table

az cosmosdb show -n sohobi-ejp-9638 -g rg-ejp-9638 \
  --query "{kind:kind, capabilities:capabilities, locations:locations[].locationName}"
```
> **언제**: 스케일 변경 후 비용 영향 추정 / **무엇**: 현재 SKU·스케일 구성

### 6.4 예산 현황 / Defender 플랜 확인

```bash
# 현 구독 예산 목록
az consumption budget list -o table

# Defender 플랜별 활성 여부 (가장 비싸므로 정기 점검)
az security pricing list -o table
```
> **언제**: 분기별 점검 / **무엇**: 의도하지 않은 Defender 자동 활성 적발

---

## 7. 비용 절감 액션 아이템

체크리스트 — 우선순위 순. 각 항목별 **추정 절감액**은 30일 실측 기반.

- [ ] **Defender for Cloud 플랜 검토** (~$20/월 절감 가능)
  - 학습/개발 환경에서는 Free 티어로 충분. `az security pricing create -n StorageAccounts -t Free` 등으로 개별 비활성
  - CSPM·Storage·AI Services·Cosmos 4개 플랜이 켜져 있음
- [ ] **PG Flex 야간 자동 stop** (~$15/월 절감)
  - 개발 시간 외 (예: 23:00-08:00) 정지 → Burstable 시간당 청구 9시간/일 제거
  - `az postgres flexible-server stop -n sohobi-db-prod -g rg-ejp-9638` (cron + GitHub Actions)
- [ ] **미사용 OpenAI deployment 제거** (~$0~$5/월)
  - `Kimi-K2.5` 사용 빈도 확인 후 미사용 시 `az cognitiveservices account deployment delete`로 제거 (자체 과금은 없으나 Defender for AI Services 단가에 영향 가능)
- [ ] **Container Apps minReplicas 0 검토** (~$5/월 절감)
  - Cold start 허용 시 트래픽 없을 때 0으로 스케일 가능
  - 단, OAuth 콜백 등 P95 레이턴시 민감 경로 영향 검증 필요
- [ ] **Storage Hot → Cool 티어 라이프사이클** (~$0.005/월, 무시 가능)
  - 로그 30일 이후 Cool 티어로 자동 전환. 현재 비용 미미하므로 **우선순위 낮음**
- [ ] **Log Analytics 보존기간 단축** (~$0.05/월, 무시 가능)
  - 현재 비용 매우 낮음. 우선순위 낮음

**주요 인사이트**: PG Flex와 Defender 두 항목만 처리하면 **월 $35 절감 (약 36%)** 가능.

---

## 8. 외부 의존: Azure AI Search (CHOI 소유) 협의 사항

**현황**:
- SOHOBI 백엔드는 `AZURE_SEARCH_ENDPOINT=choiasearchhh` 엔드포인트를 사용 (법령 RAG)
- 본 구독(`ME-M365EDU102388-joowonjeong-1`)에는 해당 리소스가 없음 → CHOI 개인 구독 또는 별도 RG로 추정
- 본 문서 작성 시점에 권한 부족으로 비용 조회 불가

**필요 액션**:
1. CHOI에게 월별 청구액 + Search 인스턴스 SKU 확인 요청
2. SOHOBI 전용 AI Search 인스턴스로 마이그레이션 검토
   - Basic 티어 ≈ $75/월 (15GB / 3 replica)
   - 인덱스 마이그레이션 비용·다운타임 평가 필요
3. 마이그레이션 완료 시 본 문서 2.3절 인벤토리에 편입

**임시 처리**: 본 문서 비용 합계는 SOHOBI 자체 구독분만 반영. AI Search 비용은 별도로 가산해야 함.

---

## 9. 변경 이력

| 일자 | 변경 | 작성자 |
|------|------|--------|
| 2026-04-20 | 최초 작성 (30일 실측 데이터 기반) | PARK |
