# Azure 무료 티어 만료(2027-05-27) 대응 전략

> 본 문서는 2026-08-07 세션의 요금 구조 실측 조사에서 도출된 **장기 방향성**. 단일 시점의 조치가 아니다.
> 선행 문서: [azure-cost-and-tenant-strategy.md](azure-cost-and-tenant-strategy.md) — 서비스 정체성(portfolio-grade, SLA 없음) 정의는 그 문서 §1이 정본이며 본 문서의 전제다.
> 관련 워크플로: [.github/workflows/pg-nightly-stop.yml](../../../.github/workflows/pg-nightly-stop.yml), [.github/workflows/azure-bicep-deploy.yml](../../../.github/workflows/azure-bicep-deploy.yml), [.github/workflows/build-backend-new.yml](../../../.github/workflows/build-backend-new.yml)

---

## 1. 핵심 결론 요약

현재 SOHOBI의 Azure 월 청구액은 약 **₩7,480**이며 이는 월 예산 ₩20,000의 37%다. 문제는 이 수치가 무료 티어 프로모션에 의해 만들어진 일시적 상태라는 것이다.

구독 `sohobi-prod`에는 `freetier` 프로모션이 **2027-05-27T03:27:33Z** 까지 걸려 있다. 그날 이후 **코드를 한 줄도 바꾸지 않아도 월 청구액이 약 4.5배가 된다.**

| 구성 | 현재 (~2027-05-27) | 만료 후 |
|---|---:|---:|
| 현행 유지 (야간 정지 + ACR) | ₩7,480 | **₩33,703** |
| 야간 정지 폐기 시 | ₩7,480 | ₩43,598 |
| 최선 조합 (야간 정지 + GHCR) | ₩7,480 | **₩26,223** |
| 월 예산 ₩20,000 대비 | 37% | **131~218%** |

**만료 후에는 현재 알려진 어떤 조합으로도 월 예산 ₩20,000을 맞출 수 없다.** 최선 조합조차 ₩26,223이다. 따라서 만료 전에 (a) ACR 고정비 제거와 (b) 예산 상향 또는 추가 구조 변경 결정이 모두 필요하다.

---

## 2. 실측 근거

### 2-1. 단가 (Azure Retail Prices API, koreacentral, 2026-08-07 조회)

| 항목 | 단가 |
|---|---:|
| PostgreSQL Flexible Server B1MS 컴퓨트 | ₩39.90 / 시간 |
| PostgreSQL Flexible Server Storage | ₩201.03 / GB / 월 |
| Container Registry Basic | ₩241.30 / 일 |

### 2-2. 실제 청구 (Cost Management API)

| 서비스 | 2026-06 | 2026-07 | 2026-08 (8/1~8/6) |
|---|---:|---:|---:|
| Container Registry (Basic) | ₩7,502 | ₩7,926 | ₩1,407 |
| Azure Container Apps | ₩60,094 | ₩0 | ₩0 |
| PostgreSQL / Cosmos / Storage / Log Analytics | ₩0 | ₩0 | ₩0 |
| Foundry Models | ₩65 | ₩0 | ₩0 |
| **합계** | **₩67,661** | **₩7,926** | **₩1,407** |

6월의 ₩60,094는 좀비 리비전 사건(PR #373, #374에서 근본원인 해결)이며 이후 재발 없음. 현재 리비전은 `sohobi-backend--0000010` 단일 active, `ScaledToZero`, replicas 0.

### 2-3. 무료 티어 적용 확인 (Consumption usageDetails API)

과금 미터가 무료 SKU로 찍히는 것을 직접 확인했다.

| 미터명 | 제품 | 단가 | 비고 |
|---|---|---:|---|
| `B1MS Compute - Free` | Azure Database for PostgreSQL Flexible Server - Free | 0 | 2026-08-06 사용량 19시간 |
| `Storage Data Stored - Free` | Az DB for PostgreSQL Flexible Server | 0 | 일별 수량 1.0323 = 32 ÷ 31 |

무료 컴퓨트 한도는 월 750시간이다. 31일 달은 744시간이므로 **24/7 가동해도 무료 한도 안에 들어온다.** 즉 무료 기간 중 야간 정지의 절감액은 ₩0이다.

스토리지 일별 수량 1.0323 GB/Month는 프로비저닝 32GB의 일할 계산(32 ÷ 31)이며, 실사용량(1GB 미만)이 아니라 **프로비저닝 크기 기준 과금**임을 뜻한다.

### 2-4. 축소 불가능한 하한

- **PG 스토리지 32GB는 Flexible Server의 최소 단위다.** 실사용은 1GB 미만이지만 더 줄일 수 없고, Flexible Server 스토리지는 축소 자체가 불가능하다(증가만 가능). 만료 후 ₩6,433/월은 고정비로 확정이다.
- **ACR Basic 밑에 SKU가 없다.** 현재 348MB / 10GB(3.4%)를 쓰면서 10GB 정액을 낸다. 이미지를 정리해도 정액제라 요금이 줄지 않는다. 레지스트리 자체를 없애는 것 외에 레버가 없다.

---

## 3. 결정 로그 — 야간 정지 워크플로 유지

2026-08-06 스케줄 실행(run `31120705945`)이 실패했다. 원인은 GitHub-hosted 러너 획득 실패(`The job was not acquired by Runner of type hosted even after multiple attempts`)로, 스텝이 하나도 실행되지 않았다. 워크플로 YAML, Azure OIDC, `az` 명령과 무관한 GitHub 인프라 측 일회성 사건이다. 최근 60회 실행 중 실패 1회.

이를 계기로 **야간 정지 워크플로를 폐기하는 안**을 검토했으나 **기각**한다.

| 폐기 찬성 논거 | 검토 결과 |
|---|---|
| 무료 기간 중 절감액이 0이므로 순수 오버헤드 | 사실이나, 유지 비용도 사실상 0(코드 변경 없음, 60회당 1회 알림) |
| start 누락 시 Bicep deploy가 Stopped PG를 update하여 InternalServerError | **이미 해결됨.** [azure-bicep-deploy.yml](../../../.github/workflows/azure-bicep-deploy.yml)의 `PG state guard (start if Stopped)` 스텝이 배포 전 상태를 확인하고 필요 시 기동 후 Ready까지 대기한다. 어젯밤 stop이 통째로 실패했으나 아무 영향 없었던 것이 실증 |
| cron 지연 실측 1시간 41분으로 설계 전제(5-15분) 이탈 | 사실이나 stop 지연은 무해하고, start는 이미 30분 간격 3중 보장 |

**기각 사유(결정적)**: 이 워크플로는 2027-05-28부터 **월 ₩9,895, 연 ₩118,740**의 가치를 갖는다. ACR 절감액(연 ₩89,760)보다 크다. 지금 폐기하면 만료 시점에 재구축해야 하며, 재활성화 리마인더가 한 번이라도 새면 그 금액을 그대로 잃는다. 유지 비용이 0에 가까운 자산을 이득 0을 근거로 폐기할 이유가 없다.

**따라서 2026-08-06 실패는 조치 없이 종결한다.**

---

## 4. 3단계 — ACR 제거, GHCR public 패키지로 이관

### 4-1. 왜 하는가

ACR Basic은 **이 프로젝트에서 유일하게 무료 티어와 무관한 실비용**이다. PG는 2027-05-27까지 무료지만 ACR은 지금도, 그 이후에도 영구히 청구된다. 연 ₩89,760이 새는 유일한 구멍이며, 사용률 3.4%에 최적화 여지가 구조적으로 0이다.

### 4-2. public 패키지가 가능한 근거

당초 GHCR 이관 시 관리 ID 기반 무자격증명 인증을 잃고 GitHub PAT를 Container App secret에 두어야 한다고 판단했다. PAT는 만료되므로 회전 실패 시 배포가 죽는다 — JWT_SECRET 누락으로 좀비 리비전이 발생했던 것과 같은 사고 유형이다. 그러나 두 사실을 확인하면서 전제가 바뀌었다.

1. **리포가 이미 public이다** (`ProfessionalSeaweedDevourer/SOHOBI`, visibility PUBLIC). 이미지에 담기는 소스는 이미 공개되어 있다.
2. **이미지에 비밀정보가 없다.** [backend/.dockerignore](../../../backend/.dockerignore)가 `.env`, `.env.*`를 제외하고, 모든 키는 Container App 환경변수로 런타임 주입된다.

따라서 GHCR 패키지를 public으로 두면 **pull 인증이 아예 불필요**해진다.

| | ACR (현재) | GHCR public |
|---|---|---|
| 저장 요금 | ₩7,480 / 월 | ₩0 (public 패키지 무제한 무료) |
| 데이터 전송 | 포함 | ₩0 (public은 쿼터 미적용) |
| pull 인증 | System-assigned MI + AcrPull 역할 | **인증 없음** (`registries` 블록 자체 불필요) |
| push 인증 | Azure OIDC 페더레이션 | `GITHUB_TOKEN` + `packages: write` (자동 발급, 만료·회전 없음) |

자격증명 개수가 현재보다 **줄어드는** 절감안이다. 리포가 private였다면 GitHub Free 플랜의 패키지 저장 쿼터에 348MB 이미지가 걸렸겠지만 public이라 해당 없다.

### 4-3. 변경 대상

| 파일 | 변경 내용 |
|---|---|
| [build-backend-new.yml](../../../.github/workflows/build-backend-new.yml) L41 | `ACR_NAME: sohobiprodacr` → GHCR 네임스페이스 |
| 〃 L61-64 | `az acr login` → `docker login ghcr.io` (`GITHUB_TOKEN`) |
| 〃 L70-97 | `IMAGE_BASE` 및 push 태그 경로 전환 |
| 〃 L103-114 | **push 검증 재작성 필요.** 현재 `az acr repository show-tags`에 의존하며 GHCR 대응 명령이 없다. `docker manifest inspect` 또는 GitHub Packages API로 교체 |
| [deploy-backend.yml](../../../.github/workflows/deploy-backend.yml) L32-63 | `secrets.ACR_NAME` 사용처 전부 |
| [infra/bicep/main.bicep](../../../infra/bicep/main.bicep) L59-63, L104-108, L232-233 | acr 모듈 호출 및 출력 제거 |
| [infra/bicep/modules/acr.bicep](../../../infra/bicep/modules/acr.bicep) | 삭제 |
| [infra/bicep/modules/container-app.bicep](../../../infra/bicep/modules/container-app.bicep) | `registries` 블록, AcrPull 역할 할당 제거 |
| GitHub 저장소 설정 | `ACR_NAME` 시크릿 정리 |

### 4-4. 가장 위험한 지점

`main.bicep`의 `useBackendAcrImage` 플래그가 **이미지 출처**와 **실서비스 설정 여부**를 한 덩어리로 묶고 있다.

```bicep
image:             useBackendAcrImage ? '${acr.outputs.loginServer}/${backendImage}' : 'mcr.microsoft.com/k8se/quickstart:latest'
targetPort:        useBackendAcrImage ? 8000 : 80
livenessProbePath: useBackendAcrImage ? '/health' : ''
jwtSecret:         useBackendAcrImage ? jwtSecret : ''
```

`false`로 두면 public 이미지를 쓰지만 동시에 포트 80, 프로브 없음, **JWT_SECRET 미주입**이라는 quickstart 플레이스홀더 설정으로 떨어진다. 따라서 플래그를 그대로 뒤집을 수 없고, '공개 이미지인가'와 '실서비스 설정인가'를 분리해야 한다.

**이 분리 작업이 JWT_SECRET 주입 경로를 지난다. 2026-06 좀비 리비전 사고와 동일한 코드 영역이다.** 반드시 별도 PR로 격리하고, 배포 후 리비전 상태와 `/health` 응답을 실측 검증한다.

### 4-5. 실행 순서

ACR을 지우면 과거 SHA 태그 이력이 함께 사라져 롤백 대상이 없어진다. 따라서 병행 기간이 필수다.

1. **GHCR push 추가** — ACR push는 유지한 채 양쪽 동시 발행. 되돌리기 쉬운 단계
2. **패키지 visibility를 public으로 전환** — 첫 push 후 기본값은 private이므로 수동 1회 전환 필요
3. **`useBackendAcrImage` 플래그 분리** — 별도 PR. JWT_SECRET 경로 회귀 검증 포함
4. **Container App을 GHCR 이미지로 전환** — `registries` 블록 제거. 정상 동작 2주 관찰
5. **ACR push 중단** — 그 사이 쌓인 GHCR 태그가 롤백 자산이 된 이후
6. **Bicep에서 ACR 제거 후 배포 → 리소스 삭제** — 절감은 이 단계에서 실현

**주의: ACR은 Bicep이 생성한다.** `az acr delete`만 실행하면 다음 Bicep 배포에서 부활한다. 반드시 IaC에서 걷어낸 뒤 삭제한다.

### 4-6. 착수 시점

절감액은 연 ₩89,760으로 고정이며 지금 하든 2027년 초에 하든 총액 차이는 착수 지연분(월 ₩7,480)뿐이다. 다만 만료 시점에는 이 작업과 5장의 결정을 동시에 처리해야 하므로, **프로덕션 압박이 없는 시기에 미리 끝내두는 편이 안전하다.**

현재 예산 소진율이 37%로 여유가 있어 재무적 시급성은 없다. 착수 판단은 세션 여력에 따른다.

---

## 5. 4단계 — 2027-05-27 절벽 대응 결정

### 5-1. 결정 시한

**2027년 3월경**에 결정한다. 만료(2027-05-27)까지 약 2개월의 실행 여유를 남기는 시점이다.

### 5-2. 만료 후 요금 구조

| 항목 | 야간 정지 유지 (약 496h/월) | 24/7 (744h/월) |
|---|---:|---:|
| PG 컴퓨트 | ₩19,790 | ₩29,685 |
| PG 스토리지 32GB (축소 불가) | ₩6,433 | ₩6,433 |
| ACR Basic (3단계 완료 시 ₩0) | ₩7,480 | ₩7,480 |
| **합계 (ACR 유지)** | ₩33,703 | ₩43,598 |
| **합계 (ACR 제거)** | **₩26,223** | ₩36,118 |

### 5-3. 선택지

3단계를 완료해도 최소 ₩26,223으로 예산 ₩20,000을 넘는다. 아래 중 하나 이상이 필요하다.

**(a) 예산 상향 — ₩30,000대**

- 장점: 구조 변경 없음. 리스크 0
- 단점: 절감 노력의 포기. 다만 portfolio 환경의 실제 가치 대비 월 ₩30,000이 타당한지는 별도 판단 사안

**(b) 정지 시간대 확대**

- 선행 문서 §1이 정의한 서비스 정체성(portfolio·개발 검증, SLA 없음, 외부 트래픽은 한국 업무시간 09-19시 산발 접속)에 비추면 현재 8시간 정지는 보수적이다
- 예: KST 09:00-19:00만 가동(약 310h/월)이면 컴퓨트 ₩12,369 + 스토리지 ₩6,433 = **₩18,802**로 예산 내 진입
- 단점: 업무시간 외 데모 접속 시 DB 미가동. cold start가 아니라 **실패**로 보인다. 포트폴리오 링크를 여는 채용담당자가 야간에 접속할 가능성을 어떻게 볼 것인가가 판단 기준
- 완화책: 프론트엔드에서 DB 미가동 시간대를 안내하거나, 접속 시 자동 기동 트리거를 두는 방안 검토 가능(기동에 수 분 소요)

**(c) PG 자체를 이전**

- 외부 무료 티어(Neon, Supabase 등) 또는 Cosmos 단일화
- 장점: 컴퓨트·스토리지 고정비 소멸 가능
- 단점: 가장 큰 구조 변경. 데이터 이전, 연결 문자열, pgvector 의존성(legal RAG) 재검증 필요. 외부 서비스의 무료 티어 정책 변경 리스크를 새로 떠안음
- 참고: [self-hosted-rag-and-db-cost-optimization.md](self-hosted-rag-and-db-cost-optimization.md)에 관련 검토 이력 존재

### 5-4. 결정 시 확인할 것

2027년 3월 시점에 아래를 **재실측**한 뒤 판단한다. 본 문서의 수치를 그대로 인용하지 않는다.

```bash
# 프로모션 만료일 재확인
az rest --method get --url "https://management.azure.com/subscriptions/<sub-id>?api-version=2022-12-01" \
  --query "promotions" -o json

# 단가 재조회 (환율·가격 개정 반영)
curl -s -G "https://prices.azure.com/api/retail/prices" \
  --data-urlencode "currencyCode=KRW" \
  --data-urlencode "\$filter=serviceName eq 'Azure Database for PostgreSQL' and armRegionName eq 'koreacentral'"

# 실제 가동 시간 실측 (cron 지연으로 이론값과 다름 — 2026-08 실측 일 16~19시간)
az rest --method get --url "https://management.azure.com/subscriptions/<sub-id>/providers/Microsoft.Consumption/usageDetails?api-version=2023-05-01"
```

특히 **가동 시간은 이론값(16h)과 실측값(16~19h)이 다르다.** cron 지연 때문이며, 절감액 추정 시 실측을 쓴다.

---

## 6. 타임라인 요약

| 시점 | 항목 | 상태 |
|---|---|---|
| 2026-08-07 | 2026-08-06 워크플로 실패 종결 (조치 없음) | 완료 |
| 2026-08-07 | 야간 정지 워크플로 유지 결정 | 완료 (§3) |
| 미정 (2027-03 이전 권장) | 3단계 — ACR 제거, GHCR 이관 | 대기 (§4) |
| 2027-03 경 | 4단계 — 절벽 대응 결정 | 대기 (§5) |
| **2027-05-27** | **무료 티어 프로모션 만료** | — |
