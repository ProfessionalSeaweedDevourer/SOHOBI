# IP 화이트리스트 운영 가이드

> 작성일: 2026-05-27
> 마지막 변경: PostgreSQL 방화벽에 `222.120.67.185` (개발자 PC) 영구 룰 추가
> 관련 문서: [03-30-backend-security-hardening.md](../plans/03-30-backend-security-hardening.md), [azure-migration-prep.md](azure-migration-prep.md)

이 문서는 SOHOBI 프로젝트에서 "IP 화이트리스트"가 **어디에** 존재하고, **어떻게** 운영되며, **어떻게 추가/삭제**하는지를 한 곳에 정리한다. 신규 개발자가 로컬에서 운영 DB 에 붙어야 하거나, 보안 사고 대응 중 화이트리스트 점검이 필요할 때 첫 번째로 펼치는 문서다.

---

## 1. 한눈에 보기 — 3 계층 화이트리스트

| 계층 | 위치 | 강제 대상 | 현재 상태 (2026-05-27) |
|------|------|----------|----------------------|
| **A. Azure PostgreSQL Flexible** firewall-rule | `sohobi-db-prod` / `rg-ejp-9638` | DB 직접 접속 (psql, pg_dump 등) | **활성** — 30+ 룰 운영 중 |
| **B. 백엔드 FastAPI** `_IPFilterMiddleware` | [backend/api_server.py:150-174](../../backend/api_server.py#L150-L174), env `ALLOWED_IPS` | Container App `/api/*` 요청 | **비활성** — Container App env 미설정 |
| **C. 그 외 Azure 리소스** (Cosmos, Storage, OpenAI, AI Search) | 각 리소스의 `networkAcls.ipRules` | 해당 리소스 직접 호출 | **무제한** — `defaultAction: Allow`, key auth 만 동작 |

운영에서 실제로 강제되는 IP 제어는 사실상 **A 한 곳**이다. B 는 코드는 있으나 환경변수 미설정으로 비활성. C 는 IP 제한 자체를 두지 않고 키 인증으로만 보호하고 있다.

---

## 2. 계층 A — PostgreSQL Flexible Server 방화벽

### 2-1. 역할

PG Flexible Server 는 IP allowlist 방식으로만 접근을 받는다. 화이트리스트에 없는 IP 는 TCP 5432 가 아예 닿지 않는다.

### 2-2. 룰 구조

| 카테고리 | 이름 패턴 | 의미 |
|---------|---------|------|
| Azure 내부 트래픽 | `AllowAllAzureServicesAndResourcesWithinAzureIps*` (start/end = `0.0.0.0`) | Container App → DB 경로. 정의는 [infra/bicep/modules/postgres.bicep:82-89](../../infra/bicep/modules/postgres.bicep#L82-L89) |
| Container App outbound | `backend1` ~ `backend20` (20.196.x.x, 20.214.x.x) | Container App 의 동적 outbound IP. 변동 가능성 있으므로 주기적 갱신 필요 |
| 개발자 로컬 PC | `allow-my-pc`, `my-public-ip`, `allow-pc-<ip>` 또는 `ClientIPAddress_<날짜>` | 마이그레이션·디버깅 목적 |
| 임시 작업 | `tmp-<ip>-<날짜>`, `local-pg-dump-<날짜>` | 작업 후 즉시 삭제하는 룰 (runbook 패턴) |

### 2-3. 추가 — 영구 룰 (개발자 PC)

```bash
az account set --subscription "ME-M365EDU102388-joowonjeong-1"
az postgres flexible-server firewall-rule create \
  --resource-group rg-ejp-9638 \
  --name sohobi-db-prod \
  --rule-name "allow-pc-<IP를 하이픈으로>" \
  --start-ip-address "<IP>" \
  --end-ip-address "<IP>"
```

예시 (실제 2026-05-27 작업):

```bash
az postgres flexible-server firewall-rule create \
  --resource-group rg-ejp-9638 \
  --name sohobi-db-prod \
  --rule-name "allow-pc-222-120-67-185" \
  --start-ip-address "222.120.67.185" \
  --end-ip-address "222.120.67.185"
```

### 2-4. 추가 — 임시 룰 (pg_dump 등)

상세 절차는 [azure-migration-prep.md §6-2 / §6-4](azure-migration-prep.md) 참고. 핵심:

```bash
MY_IP=$(curl -s https://api.ipify.org)
az postgres flexible-server firewall-rule create \
  --resource-group rg-ejp-9638 --name sohobi-db-prod \
  --rule-name "tmp-${MY_IP}-$(date +%Y%m%d)" \
  --start-ip-address "$MY_IP" --end-ip-address "$MY_IP"

# 작업 종료 직후 반드시 삭제
az postgres flexible-server firewall-rule delete \
  --resource-group rg-ejp-9638 --name sohobi-db-prod \
  --rule-name "tmp-${MY_IP}-$(date +%Y%m%d)" --yes
```

### 2-5. 확인 / 삭제

```bash
# 전체 룰 조회
az postgres flexible-server firewall-rule list \
  -g rg-ejp-9638 -n sohobi-db-prod -o table

# 특정 룰 조회
az postgres flexible-server firewall-rule list \
  -g rg-ejp-9638 -n sohobi-db-prod \
  --query "[?name=='allow-pc-222-120-67-185']" -o table

# 삭제
az postgres flexible-server firewall-rule delete \
  -g rg-ejp-9638 -n sohobi-db-prod \
  --rule-name "allow-pc-222-120-67-185" --yes
```

### 2-6. 주의

- **공인 IP 인지 확인**: 사설망 IP(10.x, 172.16-31.x, 192.168.x)를 등록하면 의미 없다. `curl -s https://api.ipify.org` 로 본인 공인 IP 확인.
- **CGNAT 환경**: 공유기·캐리어 NAT 환경에서는 동일 IP 를 여러 사용자가 공유한다. 같은 ISP·지역의 다른 사용자도 통과할 수 있음을 인지.
- **IPv6 미지원 케이스**: Azure PG Flexible 방화벽은 IPv4 만 받는다. IPv6 환경에서는 IPv4 dual-stack 경로 확인 필요.
- **Bicep 과의 불일치**: 현재 운영 룰은 portal/CLI 로 직접 추가된 것이며 [postgres.bicep](../../infra/bicep/modules/postgres.bicep) 에는 `AllowAzureServices` 룰만 정의되어 있다. Bicep redeploy 가 기존 룰을 지우는 동작은 아니지만, 인프라 코드와 실제 상태의 갭이 누적되어 있음에 유의.

---

## 3. 계층 B — 백엔드 `_IPFilterMiddleware`

### 3-1. 원래 의도 (security-hardening 계획서 기준)

[03-30-backend-security-hardening.md §4](../plans/03-30-backend-security-hardening.md#L90-L104) 가 정의한 동작:

- 미들웨어는 `ALLOWED_IPS` 환경변수에 등록된 IP 만 통과시키고 나머지는 `403 접근이 제한된 IP입니다.` 로 즉시 차단한다.
- `ALLOWED_IPS` 가 비어 있으면 미들웨어 자체가 추가되지 않아 (`_allowed_ips_raw=""` → `_allowed_ips=set()` → `if _allowed_ips:` false) **개발 모드**로 동작한다.
- **프로덕션에 등록해야 하는 값은 SWA(Static Web Apps) 아웃바운드 IP 목록**이다. 즉 SWA 프록시(`sohobi.net/api/*` → Container App) 진입점만 허용하고, Container App URL 을 직접 때리는 호출은 차단하는 것이 설계 의도.
- 추가 권장: 동일한 SWA 아웃바운드 IP 를 Azure Portal → Container Apps → Ingress → IP Security Restrictions 에도 등록해 인프라 레벨 1차 차단.

### 3-2. 현재 운영 상태 (2026-05-27)

- `sohobi-backend` Container App env 에 `ALLOWED_IPS` **미설정** → 미들웨어 비활성.
- 따라서 백엔드 API 의 외부 호출 방어선은 **`API_SECRET_KEY` 단독**이다. SWA 우회 직접 호출은 IP 레벨에서 차단되지 않는다.
- 의도와 운영 사이의 갭은 별도 PR 로 보완할 후속 과제다. SWA outbound IP 가 변동되는 특성상 동적 갱신 전략(automation 또는 CIDR 광범위 허용)이 같이 결정되어야 한다.

### 3-3. 활성화 절차 (참고)

활성화가 필요하다고 결정되면 다음 순서로 진행한다.

```bash
# 1) SWA 아웃바운드 IP 확인
az staticwebapp show -n sohobi-frontend -g rg-ejp-9638 \
  --query "outboundIpAddresses" -o tsv

# 2) Container App env 등록 (콤마 구분)
az containerapp update -n sohobi-backend -g rg-ejp-9638 \
  --set-env-vars "ALLOWED_IPS=<ip1>,<ip2>,<ip3>"
```

`RATE_LIMIT_EXEMPT_IPS` 에 등록된 IP 는 [backend/api_server.py:169-174](../../backend/api_server.py#L169-L174) 에서 `ALLOWED_IPS` 에 자동 합집합되므로 별도 등록 불필요.

---

## 4. 계층 C — 기타 Azure 리소스

| 리소스 | 현재 설정 | 비고 |
|--------|----------|------|
| Cosmos DB (`sohobi-ejp-9638`) | `publicNetwork: Enabled`, `ipRules: []` | key auth + TLS 만. IP 제한 시 `az cosmosdb network-rule add` 사용 |
| Storage (`sohobi9638logs`) | `defaultAction: Allow`, `ipRules: []` | 백엔드 logger 가 access key 로 append. 정의는 [storage.bicep](../../infra/bicep/modules/storage.bicep) |
| OpenAI (`ejp-9638-resource`) | `defaultAction: Allow`, `ipRules: []` | key auth + 키 회전으로만 보호 |
| AI Search | networkRuleSet 비어있음 | key auth 만 |

이 계층들은 현재 IP 제한을 두지 않고 **키 기반 인증**으로만 보호한다. 컴플라이언스 요구가 생기면 각 리소스의 networkAcls/ipRules 에 SWA + Container App outbound + 개발자 IP 를 등록하는 추가 작업이 필요하다.

---

## 5. 2026-05-27 변경 기록

| 항목 | 내용 |
|------|------|
| 추가된 룰 | PostgreSQL `sohobi-db-prod` 방화벽에 `allow-pc-222-120-67-185` (start=end=`222.120.67.185`) |
| 종류 | 영구 (개발자 PC) |
| 검증 | `az postgres flexible-server firewall-rule list` 에서 룰 존재 확인 완료 |
| 부수 효과 | 없음. 기존 30+ 룰에 1건 추가일 뿐, 기존 트래픽 영향 없음 |
| 후속 권장 | (1) 백엔드 `ALLOWED_IPS` 미적용 갭 정리. (2) Bicep `postgres.bicep` 에 운영 룰 일부(영구성 높은 개발자/팀 IP) 반영해 IaC 와 실제 상태 동기화 검토 |

---

## 6. FAQ

**Q. 내 IP 만 추가하면 DB 에 바로 붙는가?**
A. PG Flexible 은 IP 통과 후에도 **`administratorLogin` + 비밀번호** 가 필요하다. 자격증명은 backend `.env` 의 `POSTGRES_*` 변수 또는 Cosmos secret store 에서 확인.

**Q. 룰을 추가했는데 여전히 timeout 인다.**
A. 다음 순서로 확인: (1) `curl -s https://api.ipify.org` 로 현재 공인 IP 가 등록한 IP 와 일치하는가, (2) 사내망/VPN 으로 IP 가 바뀌지 않았는가, (3) 5432 outbound 가 사내 방화벽에서 막혀 있지 않은가.

**Q. 룰이 너무 많아 보인다. 정리해도 되는가?**
A. `backend1` ~ `backend20` 은 Container App outbound 이므로 함부로 지우면 안 된다. 개발자 PC 룰(`my-public-ip`, `allow-my-pc`, `ClientIPAddress_*`)은 소유자 확인 후 정리 가능. 정리 작업은 별도 PR 로 진행하고 본 문서에 변경 이력을 남긴다.

**Q. 백엔드 API 까지 IP 로 막고 싶다면?**
A. §3-3 의 활성화 절차를 따른다. 단 SWA outbound IP 변동성을 어떻게 다룰지(자동 갱신 vs 수동 vs CIDR 광범위 허용) 먼저 결정해야 한다.
