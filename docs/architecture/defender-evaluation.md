# Microsoft Defender for Cloud — SOHOBI 효용 평가

> **데이터 스냅샷**: 2026-04-20 / 알림 측정 구간 2026-03-26 ~ 2026-04-14 (30일)
> **출처**: `az security alert list`, `az security pricing list`
> **관련 문서**: [cost-architecture.md](cost-architecture.md) §7 비용 절감 액션

---

## 1. 결론 (TL;DR)

| 플랜 | 30일 알림 | 30일 비용 | 의사결정 | 근거 |
|------|----------:|----------:|----------|------|
| **for AI Services** | **8건** (Jailbreak 4 / Tool anomaly 4) | $4.58 | **유지** | Prompt Shield가 실제 공격 차단 |
| **for Storage** | 0건 | $8.27 | **비활성** | 로그 전용 버킷, 외부 업로드 경로 없음 |
| **CSPM** | 0건 (권장사항만) | $7.65 | **비활성** | 분기 수동 점검으로 대체 가능 |
| for Cosmos DB | 0건 | $0.01 | 유지 | 비용 미미 |
| for PG (OpenSourceRDB) | 0건 | $0.00 | 유지 | 비용 0, 자격증명 탈취 시 가치 |
| for ARM / Containers / KeyVaults / VM 등 | 0건 (SOHOBI는 미해당) | $0.00 | — | 사용 안 하는 리소스 |

**예상 절감**: 월 **$15.92** (Storage $8.27 + CSPM $7.65), AI Services는 유지.

```bash
az security pricing create -n StorageAccounts -t Free
az security pricing create -n CloudPosture -t Free
```

---

## 2. 실측 알림 이력 (2026-03-26 ~ 2026-04-14)

`az security alert list` 결과 중 SOHOBI(`rg-ejp-9638`) 관련만 추출:

| 일자(UTC) | 심각도 | 알림명 | 대상 deployment | 출처 플랜 |
|-----------|--------|--------|-----------------|----------|
| 2026-04-13 08:20 | Medium | Jailbreak attempt blocked by Prompt Shields | gpt-5.4-mini | for AI Services |
| 2026-04-09 08:47 | Low | Anomaly in AI application tool invocation | gpt-5.4-mini | for AI Services |
| 2026-04-08 17:13 | Low | Anomaly in AI application tool invocation | gpt-5.4-mini | for AI Services |
| 2026-04-02 02:37 | Low | Anomaly in AI application tool invocation | gpt-4.1-mini | for AI Services |
| 2026-04-01 02:23 | Medium | Jailbreak attempt blocked by Prompt Shields | gpt-4.1-mini | for AI Services |
| 2026-03-30 06:44 | Medium | Jailbreak attempt blocked by Prompt Shields | gpt-4.1-mini | for AI Services |
| 2026-03-27 05:53 | Low | Anomaly in AI application tool invocation | gpt-4.1-mini | for AI Services |
| 2026-03-26 07:00 | Medium | Jailbreak attempt blocked by Prompt Shields | gpt-4.1-mini | for AI Services |

> **8건 전부 Defender for AI Services 발생.** Storage·CSPM·Cosmos·ARM·VM 등 다른 플랜은 30일간 단 1건도 SOHOBI 알림을 만들지 못함.

> 같은 구독 내 다른 RG(`rg-elv-dev`)에 Cosmos 비정상 위치 액세스 1건이 있으나 SOHOBI 비용과 무관.

---

## 3. 플랜별 효용 분석

### 3.1 for AI Services — 유지 ✅

- **Prompt Shield**가 Jailbreak 시도 4회를 차단 단계에서 막음 → 비활성화 시 차단 자체가 사라지고 모델로 그대로 도달
- 도구 오용 이상탐지 4회 — 정상 사용자 패턴과 다른 tool calling 시도를 식별
- "기존 보안 조치(인증·CORS·Rate Limit·OAuth 쿠키 하드닝 등)는 **HTTP 레이어** 방어"로 **프롬프트 레이어 공격(UPIA)** 은 막지 못함
- 두 모델(gpt-4.1-mini, gpt-5.4-mini) 모두 표적이 됨 → 트래픽 규모 작아도 공격 표면 존재 입증
- 월 $4.58은 **정량적으로 입증된 효용**

### 3.2 for Storage — 비활성 권장 🔻

- 30일 알림 0건
- `sohobi9638logs`는 **백엔드 서버 로그 적재 전용**, 외부 업로드 경로 없음
- 멀웨어 스캔 대상이 사실상 0이고 비정상 액세스도 발생하지 않음
- 공격 표면 ≈ 0인데 월 $8.27 지불 중 (전체 비용의 8.6%)
- **재활성 트리거**: 사용자 파일 업로드 기능 도입 시 즉시 재활성

### 3.3 CSPM — 비활성 권장 🔻

- 알림이 아닌 보안 권장사항(assessment) 생성용
- Azure Portal Security Recommendations / 컴플라이언스 대시보드(PCI·ISO·SOC2) 사용 안 하면 가치 거의 없음
- agentless 취약점 스캔, attack path 분석 손실
- 월 $7.65 (전체 비용의 8.0%)
- **재활성 트리거**: B2B 진입·외부 감사·SOC2 진행 시 재활성

### 3.4 기타 플랜 — 현상 유지

- for Cosmos DB / for PG / for ARM: 비용 미미하거나 0이고 자격증명 탈취 등 시나리오 대비 가치
- for VM / KeyVaults / Containers: SOHOBI는 해당 리소스 미사용 또는 별도 RG, 직접 영향 없음

---

## 4. Free 티어 전환 시 일반적 리스크 (참고)

플랜별 손실 기능과 운영 리스크:

| 플랜 | Free 전환 시 손실 | 사고 시나리오 | 탐지 지연 |
|------|---------------------|----------------|----------|
| AI Services | Prompt Shield 차단, Risk & Safety eval, 도구 오용 이상탐지 | 시스템 프롬프트 유출, 응답 검열 우회 | 사후 LLM 출력 분석 (수일) |
| Storage | 멀웨어 스캔, 민감 데이터 노출 탐지, 비정상 액세스 알림 | SAS 키 유출 후 데이터 추출 | 사용자 신고 또는 청구서 |
| OpenSourceRDB (PG) | brute-force 알림, SQLi 패턴, 비정상 IP | 자격증명 탈취 후 데이터 유출 | 정기 감사 (수일~수주) |
| Cosmos DB | 비정상 위치 액세스, key 유출, 비정상 RU 패턴 | 키 유출 후 무단 조회 | 청구 RU 급증 (24h+) |
| CSPM | Secure Score, 컴플라이언스 대시보드, attack path | 신규 리소스 public access 오픈 | 정기 점검 |
| ARM | 비정상 RBAC 변경, 의심 SP 활동 | 권한 탈취 후 권한 상승 | 다음 감사 |
| Containers | 컨테이너 런타임 위협, K8s admission 이상 | 컨테이너 이스케이프, 악성 이미지 | 비정상 동작 발견 시 |

### 4.1 컴플라이언스·감사 측면

- **개인정보보호법 / 신용정보법 / 금융보안원 가이드라인**: 한국 SMB 대상 서비스 특성상 사업자번호·매출 등 준식별정보 처리 → 주기적 보안진단 의무 대상이 될 수 있음. CSPM 비활성화 시 자체 점검 부담 증가
- **외부 감사 / 투자 실사**: Defender 활성 여부는 SOC2/ISO27001 통제 항목 다수와 직결. B2B 진입 시 재활성화 필요
- **GDPR / DSR**: Storage Defender의 민감 데이터 노출 탐지가 없으면 PII 누출 통보 의무 위반 가능성

### 4.2 SOHOBI 현 단계의 현실적 판단

| 요소 | 평가 |
|------|------|
| 사용자 트래픽 규모 | 소규모 (월 $97 인프라) — 표적 공격 가치 낮음 |
| 처리 데이터 민감도 | 사업자번호·매출·위치정보 — **중간** |
| 외부 노출 면 | API endpoint 1개, 인증·CORS·Rate Limit 적용 |
| AI 공격 실측 | 30일간 **Jailbreak 4회 시도** = 표적 존재 입증 |

→ AI Services는 **공격이 실제로 발생** 중이므로 유지, Storage·CSPM은 효용 미입증으로 비활성

---

## 5. 동적 알림 조회 매뉴얼

```bash
# 전체 활성 Defender 알림 (구독 기준)
az security alert list -o json > /tmp/defender-alerts.json

# SOHOBI RG 알림만 필터 (Python)
python3 -c "
import json
d = json.load(open('/tmp/defender-alerts.json'))
sohobi = [a for a in d if 'ejp-9638' in str(a.get('resourceIdentifiers',[]))]
for a in sohobi:
    print(f\"[{a['severity']}] {a['timeGeneratedUtc'][:19]} {a['alertDisplayName']}\")
"

# Defender 플랜 활성 현황
az security pricing list -o table

# 특정 플랜 비활성
az security pricing create -n <PlanName> -t Free
# 사용 가능한 PlanName: VirtualMachines, SqlServers, AppServices, StorageAccounts,
#   SqlServerVirtualMachines, KeyVaults, Arm, OpenSourceRelationalDatabases,
#   CosmosDbs, Containers, CloudPosture, AI

# 특정 플랜 재활성 (Standard로 복귀)
az security pricing create -n <PlanName> -t Standard
```

---

## 6. 변경 이력

| 일자 | 변경 | 작성자 |
|------|------|--------|
| 2026-04-20 | 최초 작성 (30일 실측 알림 8건 분석) | PARK |
