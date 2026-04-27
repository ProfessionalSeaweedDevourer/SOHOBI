# Azure 인프라 전략 — 테넌트 이전 + Right-sizing 통합

> 본 문서는 2026-04-26~27 세션 논의의 종합. 단일 시점의 결론이 아닌 **장기 방향성**.
> 관련 산출물:
> - 기획안: [docs/plans/2026-04-26-azure-tenant-migration.md](../2026-04-26-azure-tenant-migration.md)
> - 기획안: [docs/plans/2026-04-26-legal-index-rebuild.md](../2026-04-26-legal-index-rebuild.md)
> - 비용 baseline: [docs/architecture/cost-architecture.md](../../architecture/cost-architecture.md)
> - 사전 백업 런북: [docs/runbooks/azure-migration-prep.md](../../runbooks/azure-migration-prep.md)
> - 사전 백업 PR: #326 / 인덱스 파이프라인 PR: #325

---

## 1. 서비스 정체성 재정의 (전략의 출발점)

이번 세션에서 명확해진 사실:

**SOHOBI 라이브 서비스는 production이 아니라 portfolio·개발 검증 환경이다.**

- 외부 트래픽: 이력서·포트폴리오 링크를 본 채용담당자의 **한국 업무시간(09-19시) 산발 접속**
- 내부 트래픽: PARK 본인의 **개발·테스트 (시간대 제약 없음, 다만 야간·새벽은 적음)**
- SLA 요구: **없음**. cold start 수 초·점검 시간 1~2시간 모두 허용 가능
- 데이터 영속성 요구: 있음 (세션·로그·DB는 손실 금지)

이 정체성에 맞춘 인프라 right-sizing이 본 전략의 핵심 축.

## 2. 현 상태 진단

### 2-1. 빌링 (실측 30일 $95.76, [cost-architecture.md](../../architecture/cost-architecture.md) §3)

| 카테고리 | 30일 | 비중 | 성격 |
|----------|-----:|-----:|------|
| PostgreSQL Flex B2s 컴퓨트 (24/7) | $49.30 | 51.5% | **고정비 — 큰 right-sizing 여지** |
| Defender for Cloud 4종 | $20.51 | 21.4% | **고정비 — portfolio 환경에 과함** |
| Container Apps + ACR | $14.91 | 15.6% | 변동 + 정액 혼합 |
| Azure OpenAI 토큰 | $8.03 | 8.4% | 변동비 — 사용량 비례 |
| 기타 (Cosmos, DNS, Blob, LA) | $0.27 | 0.3% | 사실상 0 |

### 2-2. 구조적 이슈

1. **테넌트·구독 위치**: 현재 `eric.park@miee.dev`(ME-M365EDU 학생 구독). 학생 정책으로 RG-scope budget 거부 등 제약 가능. 장기 운영용으로는 별도 테넌트 분리 필요 (memory `project_rg_ejp_migration.md`, 2026-04-20 결정)
2. **외부 계정 의존**: legal-index가 `choiasearchhh` 외부 계정 호스팅. 이번 세션 백업 시 schema export ERR로 **이미 접근 차단 확인**. 실재한 위험
3. **리전 분산**: Container App·PG·ACR·Storage = koreacentral / Cosmos·OpenAI = east us 2. 빌링 영향은 미미($0.06/30일)지만 사용자 응답 latency 가산
4. **IaC 부재**: Portal·az CLI 수동 관리. 이전·재해복구 비용 큼

### 2-3. Cosmos에 대한 명확한 결론

세션 중 "Cosmos가 과한 성능 구매 아닌가?" 가설 → **사실 아님**. Serverless 모드로 사용량 기반 청구. 30일 $0.07. 데이터 1.78MB, 3,559 docs는 정확히 청구 데이터와 일치. 개선 여지 거의 없음.

## 3. 전략 방향 — 3축

### 축 A. 테넌트·구독 분리 (장기 정체성)

별도 테넌트(Tenant B) + 별도 구독(Subscription B)로 전체 RG 이전. 학생 구독 종속성 제거 + RBAC·budget·정책의 독립성 확보.

상세: [2026-04-26-azure-tenant-migration.md](../2026-04-26-azure-tenant-migration.md)

### 축 B. Right-sizing (즉시 효과)

서비스 정체성(§1)에 맞춰 인프라를 **portfolio-grade**로 축소:

| 컴포넌트 | 현재 | 권장 | 월 절감 |
|----------|------|------|--------:|
| PostgreSQL Flex | B2s 24/7 | **B2s + 야간 정지 (23-08시)** 또는 **on-demand 수동 기동** | $15~30 |
| Container Apps | minReplicas 1 | **minReplicas 0** (cold start 허용) | ~$5 |
| Defender for Storage | 활성 | **Free** (알림 0건) | $8 |
| Defender for CSPM | 활성 | **Free** (알림 0건) | $8 |
| Defender for AI | 활성 | 유지 (Jailbreak 4건 차단 실적) | 0 |
| Defender for Cosmos | 활성 | Free | $0 (이미 거의 0) |
| 미사용 OpenAI deployment (Kimi-K2.5 등) | 8개 배포 | 활성 모델만 유지 | $0~3 |
| Cosmos | Serverless | 유지 | 0 |
| ACR Basic | 일정액 $5 | 유지 (가장 저렴 tier) | 0 |

**합계 월 $35~50 절감 (37~52%)** — 청구액 ~$50/월 수준으로 축소 가능.

야간 정지를 더 공격적으로 가져가서 **on-demand만 기동**(채용 시즌·개발 세션 외 정지)하면 $40 추가 절감 여지. 단 채용담당자 무예고 접속 시 503 응답되므로 trade-off.

### 축 C. AI Search 인덱스 재구축 (의존성 제거)

`choiasearchhh` 외부 의존 끊고 자체 인덱스로 재구축. 본 세션에서 RAG 관점 기획 + 6단계 파이프라인 구현 완료.

상세: [2026-04-26-legal-index-rebuild.md](../2026-04-26-legal-index-rebuild.md), PR #325

## 4. 시퀀싱 — 어느 순서로 할 것인가

축 A·B·C는 독립적이지만 의존이 있음:

```
1. [B 즉시] Defender 다운그레이드, Container Apps minReplicas 0
   → 신규 테넌트 발급 무관. 1주 내 효과
   → 월 $20~25 절감, risk 매우 낮음

2. [B 즉시] PG 야간 정지 자동화 (GitHub Actions cron)
   → Right-sizing 핵심 단일 항목
   → 월 $15~30 절감

3. [C 진행 가능] AI Search 소스 데이터 확보 워크스트림 (팀원 접촉)
   → 가장 큰 미확정 변수. cutover 일정과 분리하여 병렬 진행

4. [A 사전 준비] 사전 백업 (PR #326), Bicep IaC 작성, OIDC 신규 등록
   → 신규 테넌트 발급 전이라도 IaC 코드는 작성 가능

5. [A·B·C 통합 cutover] 신규 테넌트 발급 후 1~2시간 점검 윈도우에 일괄
   → 신규 구독에서는 처음부터 right-sized 구성으로 프로비저닝
   → AI Search v2 인덱스도 신규 환경에서 빌드
```

요점: **신규 테넌트가 없어도 축 B(right-sizing)는 즉시 시작 가능**. 그러면 cutover 일정에 무관하게 즉시 청구액 절반 가능.

## 5. 비용 시뮬레이션

| 시나리오 | 월 청구액 | 비고 |
|---------|----------:|------|
| 현상 유지 | $97 | 실측 baseline |
| 축 B만 (Defender + Container Apps) | $77 | 즉시 시작, 신규 테넌트 무관 |
| 축 B 풀 (위 + PG 야간 정지) | $50~60 | cron 자동화 추가 |
| 축 B 공격 (PG on-demand only) | $30~40 | 채용 시즌만 풀 가동 |
| 축 A·B·C 완료 후 (신규 테넌트, right-sized, koreacentral 통합) | $40~55 | latency·UX 추가 개선 |

목표 **월 $40~50** — 현재 대비 절반.

## 6. 미해결·트래킹

| 항목 | 상태 | 책임/다음 액션 |
|------|------|----------------|
| AI Search 소스 데이터 보유자 | 미확인 | 팀원 접촉 (cutover의 최대 블로커) |
| 신규 테넌트 발급 일정 | 미정 | PARK 결정 |
| OpenAI 모델 koreacentral 가용성 | 미확인 | gpt-5.4-mini의 KR 리전 배포 여부 az CLI 확인 |
| PG 야간 정지 시 OAuth refresh 토큰 만료 영향 | 미확인 | 정지 cron 작성 시 검증 |
| Defender 비활성화 후 보안 회귀 모니터링 | 미수립 | 알림 0건이지만 통상 점검 routine 필요 |

## 6-A. Bicep IaC 권고사항·LOW 유의사항 (PR #328 리뷰 산출)

PR #328(Foundation: Log Analytics + Storage + ACR) 리뷰에서 도출. 모두 blocker 아닌 **후속 PR 백로그**.

| # | 권고 | 우선순위 | 처리 시점 |
| --- | ---- | :------: | --------- |
| 1 | Storage `allowSharedKeyAccess: false` 전환 + Container Apps managed identity → `Storage Blob Data Contributor` 부여. 백엔드 logger.py도 AAD 인증 경로로 마이그레이션 | LOW | 다음 PR(Container App 추가)과 동시 |
| 2 | `.gitignore`의 `infra/bicep/main.json` 라인 제거 (`infra/bicep/**/*.json` 글롭에 흡수됨). 화이트리스트 `!infra/bicep/parameters/*.json` 의도 주석 추가 | LOW | ✅ PR #328 머지 시 동시 처리 (main 머지 충돌 해소 커밋) |
| 3 | `acr.bicep`의 `zoneRedundancy: 'Disabled'` 필드 — Basic SKU에선 무의미. Premium 승격 시점에 의식적으로 추가하는 편이 명확 | LOW | Premium 승격 검토 시 |
| 4 | 자원 이름 길이 가드 — 현재 `sohobiprodlogs`(15자)·`sohobiprodacr`(13자)는 한도 내. 향후 긴 `namePrefix` 사용 가능성 대비 `uniqueString(resourceGroup().id)` 짧은 해시 suffix 패턴 도입 검토 | LOW (보류) | 멀티 환경/팀 확장 시 |

권고 1번은 **다음 PR(Container Apps env + Container App 모듈)과 함께 처리**가 자연스러움 — managed identity 설정과 Storage 권한 부여가 같은 변경 세트에서 묶임.

## 7. 비포함 (의도적 제외)

- **운영 등급 SLA로 회귀**: portfolio 정체성 유지 전제. 향후 실 트래픽 발생 시 본 전략 재검토
- **Multi-region·HA**: portfolio 환경엔 과함
- **Reserved instance / Savings plan**: 1년 commitment 가치 없음 (사용량 변동·이전 예정)
- **Cosmos 컨테이너 설계 재검토**: 현 schema 비용 0이라 우선순위 낮음
- **Static Web Apps tier 변경**: Free 그대로 적정

---

## 변경 이력

| 일자 | 변경 | 출처 |
|------|------|------|
| 2026-04-27 | 최초 작성 — 본 세션의 테넌트 이전·인덱스 재구축·비용 분석 통합 | 이 세션 |
| 2026-04-27 | §6-A Bicep IaC 권고사항·LOW 유의사항 4건 추가 (PR #328 리뷰 산출, LOW#2는 머지 시 동시 처리) | PR #328 리뷰 |
