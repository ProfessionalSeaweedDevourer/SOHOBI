# 현상유지 모드 저비용 운영 기획

> 작성: 2026-10-11 (Azure 비용, CI/CD, 리소스 실측과 웹 리서치 기반)
> 전제: SOHOBI는 이제 기능 개발 없이 **현상유지만 하는 포트폴리오 서비스**다. 서비스 정체성(portfolio-grade, SLA 없음)의 정본은 [azure-cost-and-tenant-strategy.md](azure-cost-and-tenant-strategy.md) §1이다.
> 연계 문서: [azure-freetier-cliff-2027.md](azure-freetier-cliff-2027.md) (무료 티어 만료 대응). 본 문서는 그 문서를 대체하지 않고, 이후 실측으로 바뀐 사실과 새 선택지를 더해 **현상유지 운영 전체의 단일 실행 계획**으로 묶는다. 두 문서가 어긋나면 날짜가 늦은 본 문서를 따른다.

---

## 0. 결론 요약

현상유지 프로젝트의 운영 목표는 세 가지다.

1. **돈**: 무료 티어 만료(2027-05-27) 뒤에도 월 예산 ₩20,000 안에 머문다. 가능하면 ₩0 근처까지 내린다.
2. **손**: 사람이 주기적으로 들여다보지 않아도 돌아간다. 사람이 해야 하는 일은 연 몇 회의 정해진 점검뿐이다.
3. **감지**: 조용히 고장 나 있는 상태가 몇 달씩 방치되지 않는다.

이번 실측에서 세 번째 목표가 이미 깨져 있음이 드러났다. **운영 백엔드의 PostgreSQL 연결이 2026-06-25 이후 약 3.5개월째 전부 실패하고 있다** (§1-3). 헬스 체크와 CI는 모두 정상으로 보였기 때문에 아무도 알아채지 못했다.

권고 순서:

| 순서 | 권고 | 시점 | 비용 효과 |
|---|---|---|---|
| 1 | PG 비밀번호를 Bicep으로 영구 주입해 상권, 지도, 재무 기능 복구 (R1) | 즉시 | 없음 (기능 복구) |
| 2 | 야간 정지 작업을 무료 기간 동안 일시 중지 (R2) | R1과 같은 PR | 없음 (무료 기간 절감액 ₩0) |
| 3 | 조용한 고장 감지 장치 추가: PG 경유 정기 점검, 모델 퇴역 알림 (R3) | 즉시 | ₩0 |
| 4 | sohobi.net 도메인 만료(2027-03-29) 대응 결정 (R4) | 2027-02 이전 | 연 ₩1~2만 수준 |
| 5 | ACR을 GHCR로 이관 (R5, 기존 문서 §4 그대로) | 2027-03 이전 | 월 약 ₩7,500 절감 |
| 6 | PG를 이미지 내장 SQLite로 대체 (R6, 신규 선택지) | 2027-03 결정, 05 이전 완료 | 만료 후 월 약 ₩26,000 회피 |
| 7 | keepalive, 모델 퇴역 등 정기 점검 일정 고정 (R7) | 일정표대로 | ₩0 |

R5와 R6을 모두 마치면 만료 후 월 청구액은 **Cosmos 서버리스와 OpenAI 사용량만 남아 사실상 ₩0 근처**가 된다. 같은 시점에 PG 서버, 야간 정지 워크플로, 그 워크플로를 살려 두는 keepalive가 모두 필요 없어져 관리 대상도 함께 줄어든다.

---

## 1. 현재 상태 실측 (2026-10-11)

### 1-1. 비용

인보이스 (MCA billing account, 전부 자동결제 완료):

| 대상 월 | 세전 | 부가세 | 총액 | 결제 |
|---|---:|---:|---:|---|
| 2026-06 | ₩67,629 (크레딧 차감 전) | ₩2,256 | ₩24,814 | 2026-07-14 |
| 2026-07 | ₩7,918 | ₩792 | ₩8,710 | 2026-08-09 |
| 2026-08 | ₩7,467 | ₩747 | ₩8,214 | 2026-09-09 |
| 2026-09 | ₩6,888 | ₩689 | ₩7,577 | 2026-10-09, visa |

Cost Management 사용량:

| 서비스 | 2026-09 | 2026-10 (1~10일) |
|---|---:|---:|
| Container Registry (Basic) | ₩6,900 | ₩2,274 |
| Cosmos DB, PostgreSQL, Log Analytics, Storage | ₩0 | ₩0 |
| Container Apps, Foundry Models | 행 없음 (무료 범위) | 행 없음 |

- 일별 값은 ACR 일 ₩227~230으로 **평탄**하다. 신규 리소스, 스파이크, 좀비 리비전 징후는 없다.
- 10월 예상 착지액은 ₩227.4 × 31일 × 1.1(부가세)로 **약 ₩7,750**이다.
- 과금 리소스는 여전히 ACR 하나뿐이다. 기존 문서의 ACR 단가(₩241.30/일)보다 조금 낮게 찍히는데, 환율 차이로 본다.

### 1-2. CI/CD

| 항목 | 상태 |
|---|---|
| 일정 워크플로 (PG 야간 정지, SWA 정리) | keepalive(PR #376) 머지 이후 10월 실행이 모두 성공했다. 최근 200회 중 마지막 실패는 2026-08-06 러너 획득 실패 1건이다. |
| keepalive 실효성 | enable API 호출이 60일 무활동 타이머를 다시 시작한다는 내용은 GitHub 공식 문서에 없고, 커뮤니티 관행이다. 마지막 커밋이 10/06이므로 **2026-12-06 이후에도 워크플로가 active로 남는지**를 봐야 판정할 수 있다. |
| Node 20 제거 (2026-09-23) | 제거 이후에도 `azure/login@v2` 워크플로가 성공했다. `static-web-apps-deploy`는 Docker 액션이라 영향이 없다. |
| 배포 워크플로 | 백엔드 배포는 6/11, Bicep 배포는 6/25, 프론트 배포는 5/28 이후 실행된 적이 없다. 다음 배포가 Node 24 환경에서의 첫 실행이다. |
| 서비스 응답 | 백엔드 `/health` 200, `sohobi.net` 200 |

### 1-3. 발견된 결함

**(A) 운영 PG 연결이 상시 실패 (심각도 높음)**

- 현재 리비전 `sohobi-backend--0000010`(2026-06-25 생성)의 환경변수에 `PG_PASSWORD`가 없다. Container App secret도 `jwt-secret` 하나뿐이다.
- 리비전 0000008에는 있었고 0000009부터 사라졌다. CLI로 넣은 secret과 env를 Bicep 배포가 덮어쓰는 drift가 원인이며, 6월 컷오버 인수인계에서 이미 높음으로 표시된 위험이다. PR #373은 같은 문제를 `JWT_SECRET`에 대해서만 고쳤다.
- 운영 로그에 `[MapInfoDAO] 인덱스 생성 실패 (무시): 'PG_PASSWORD'`가 찍힌다. `backend/db/dao/baseDAO.py`의 `os.environ["PG_PASSWORD"]`에서 KeyError가 난다. 컨테이너 안에서 직접 접속해도 `fe_sendauth: no password supplied`로 실패한다.
- 영향: 상권 분석(location), 재무 시뮬레이션의 상권 데이터, 지도, 실거래가 API 전부.
- `/health`는 PG를 건드리지 않고, 스모크 테스트도 인증만 확인해서 둘 다 통과한다. 이것이 3.5개월 동안 감지되지 않은 이유다.

**(B) PG 야간 정지 cron이 2.5~5.6시간 지연 (A를 고치면 드러남)**

- 정지 cron(KST 00:00)이 실제로는 KST 04:12~05:37에 돌았다. 기동 cron(08:00, 08:30, 09:00)의 첫 실행은 10:31~11:02였다. 로그상 그 시점 서버 상태는 Stopped였다.
- 따라서 A를 고치면 **매일 08시부터 약 11시까지 PG 기능이 다시 꺼진다.** 방문이 몰리는 업무시간 초입이다.
- 무료 기간 중 야간 정지의 절감액은 ₩0이므로(기존 문서 §2-3), 지금은 손해만 있다.
- GitHub 공식 문서는 정각을 부하 구간으로 보고 분 단위를 옮기라고 권한다. 지연 자체를 없앨 방법은 없다.

**(C) 감지 장치 부재**

A가 3.5개월 방치된 것 자체가 결함이다. 현상유지 프로젝트에서는 사람이 들여다보지 않으므로, 핵심 경로를 직접 두드리는 자동 점검이 없으면 같은 일이 반복된다.

### 1-4. 외부 기한

| 기한 | 항목 | 성격 |
|---|---|---|
| 2026-12-06 경 | keepalive 실효성 판정 가능 시점 | 점검 |
| **2027-03-29** | **sohobi.net 도메인 등록 만료** (Wild West Domains, Azure App Service Domain, 구 구독 소재) | 놓치면 사이트 주소 상실 |
| 2027-05-27 | PG Flexible Server 무료 티어 프로모션 만료 | 놓치면 월 청구액 약 4.5배 |
| 2027-09-21 | `gpt-5.4-mini` (2026-03-17판) 퇴역 | 자동 업그레이드되어 중단은 아니지만 동작이 달라질 수 있음 |
| 2028-02-09 | `text-embedding-3-small`, `-large` 퇴역 | 운영은 `RAG_BACKEND=disabled`라 영향 작음 |

도메인 만료가 PG 만료보다 두 달 빠르다. 기존 문서에는 이 항목이 없다. 2026-06 실측 시점 autoRenew는 false였고, 도메인과 DNS zone은 현재 `sohobi-prod` 구독에서 보이지 않는 구 구독에 있다.

---

## 2. 리서치 결과

| 주제 | 사실 | 판단 |
|---|---|---|
| Container Apps 무료 할당 | 구독당 매월 180,000 vCPU초, 360,000 GiB초, 요청 200만 건이 **상시 무료**다. 12개월 프로모션이 아니다. | scale-to-zero 백엔드는 만료 뒤에도 ₩0이다. 이미지가 커져도 과금은 늘지 않는다. |
| PG Flexible Server 무료 | 첫 12개월만 B1MS 750시간, 스토리지 32GB, 백업 32GB가 무료다. 상시 무료 목록에는 없다. 정지한 서버는 7일 뒤 자동 재기동된다. | 만료 후 비용 추정(기존 문서 §5-2)은 유효하다. |
| Azure Automation | 매월 작업 실행 500분이 무료다. 관리 ID로 PG 시작과 정지 runbook을 돌릴 수 있다. | 정지와 기동을 하루 두 번 해도 월 100분 안팎이다. GitHub cron 지연과 keepalive 의존이 함께 사라진다. |
| GitHub Actions cron | 공식 문서상 고부하 시간대에는 지연되거나 실행이 빠질 수 있다. 공개 리포는 60일 무활동이면 일정 워크플로가 비활성화된다. | 시각이 중요한 작업(DB 기동)에는 맞지 않는다. 지연에 둔감한 주간 점검 정도에만 쓴다. |
| Foundry 모델 수명 | GA 모델은 출시 18개월 뒤 퇴역한다. 최소 60일 전에 메일과 Service Health로 통지된다. GlobalStandard 배포에 `OnceNewDefaultVersionAvailable`이 걸려 있으면 자동 업그레이드되고, 퇴역 모델 호출은 410을 반환한다. | 현 배포는 자동 업그레이드 설정이라 중단 위험은 없다. 위험은 Sign-off 채점 동작이 바뀌는 것이다. |
| Neon 무료 | 프로젝트당 0.5GB, 월 100 CU시간, 5분 무활동이면 정지, pgvector 지원 | 데이터가 약 1.16GB(§3 R6)라 용량이 맞지 않는다. |
| Supabase 무료 | 500MB, **7일 무활동이면 프로젝트 일시정지**, 재개는 수동 | 사람이 안 보는 프로젝트와 정면으로 충돌한다. 제외한다. |

출처는 §7에 모았다.

---

## 3. 권고안

### R1. PG 비밀번호를 Bicep으로 영구 주입 (즉시)

**무엇을**: PR #373이 `JWT_SECRET`에 쓴 방식을 그대로 따른다.
- `infra/bicep/modules/container-app.bicep`의 `secrets` 배열에 `pg-password`를 추가한다.
- `infra/bicep/main.bicep`의 env 목록에 `{ name: 'PG_PASSWORD', secretRef: 'pg-password' }`를 추가한다.
- 값은 이미 Bicep에 들어가는 `pgAdministratorLoginPassword`(워크플로 secret `PG_ADMIN_PASSWORD`)를 재사용한다. PG 사용자도 `postgres.outputs.administratorLogin`이므로 짝이 맞는다.

**왜 CLI가 아니라 Bicep인가**: CLI로 secret을 넣으면 다음 Bicep 배포가 다시 지운다. 이번 결함의 원인이 정확히 그것이다.

**검증**: 배포 후 운영 로그에서 `'PG_PASSWORD'` 오류가 사라지는지, 실거래가 또는 상권 API가 데이터를 돌려주는지 확인한다.

**주의**: 이 배포가 Bicep 배포 워크플로의 Node 24 환경 첫 실행이 된다. 배포 실패도 함께 확인 대상이다.

### R2. 야간 정지 작업을 무료 기간 동안 일시 중지 (R1과 같은 PR)

**무엇을**: `.github/workflows/pg-nightly-stop.yml`의 `stop` job 일정 실행만 저장소 변수 하나로 끈다. `start` job은 서버가 Stopped일 때만 동작하는 가드가 있어 정지가 없으면 아무 일도 하지 않으므로 그대로 둔다. 워크플로 파일과 수동 실행 입력도 유지한다.

```yaml
jobs:
  stop:
    # 무료 기간(~2027-05-27)에는 절감액 ₩0이고 cron 지연으로 아침 장애만 생기므로 일정 정지를 끈다.
    if: (github.event.schedule == '0 15 * * *' && vars.PG_NIGHTLY_ENABLED == 'true') || (github.event_name == 'workflow_dispatch' && github.event.inputs.action == 'stop')
```

**왜 지우지 않는가**: 기존 문서 §3의 유지 결정(자산 보존)과 충돌하지 않게, 되살리는 비용을 변수 하나로 묶는다.

**되살릴 조건**: R6에서 PG를 유지하기로 결정했을 때만 되살린다. 그때는 GitHub cron이 아니라 Azure Automation 일정으로 옮겨서 되살린다(R6의 (b′)안).

**부수 효과**: 일정 워크플로가 job을 건너뛰어도 실행 기록은 남으므로 keepalive 대상 목록은 그대로 둔다.

### R3. 조용한 고장 감지 장치 (즉시)

현상유지 프로젝트에서 감지는 비용이 아니라 생존 조건이다. 모두 무료 범위에서 만든다.

| 장치 | 내용 | 비용 |
|---|---|---|
| 주간 심층 점검 | 일정 워크플로가 주 1회 PG를 거치는 API(예: 실거래가 조회)를 API 키로 호출하고, 빈 응답이면 실패 처리한다. 실패 메일은 GitHub가 저장소 소유자에게 보낸다. 지연에 둔감하므로 GitHub cron으로 충분하다. | ₩0 |
| Service Health 알림 | Azure OpenAI 서비스의 Health advisory와 Retirement를 메일로 받는다. | ₩0 |
| 예산 알림 | 이미 있다(`sohobi-prod-monthly`, ₩20,000). 유지한다. | ₩0 |

주간 점검 워크플로는 keepalive 대상 목록에 추가해야 한다.

### R4. sohobi.net 도메인 만료 대응 (2027-02 이전 결정)

선택지:
- (가) 구 구독에서 App Service Domain 자동 갱신을 켠다. 구 구독 접근이 계속 가능하다는 전제가 필요하다.
- (나) 외부 등록기관으로 이전(transfer-out)한다. EPP 코드 발급부터 5~7일이 걸린다. 이전하면 갱신이 1년 연장되므로 만료 직전에 몰지 않는다.

**판단 기준**: 구 구독(교육용 M365 테넌트)이 2027년에도 살아 있을지가 핵심이다. 불확실하면 (나)가 안전하다. 어느 쪽이든 DNS zone 위치도 함께 정해야 한다. 현재는 구 구독의 Azure DNS다.

**먼저 확인할 것**: 구 구독 접근 가능 여부, 현재 autoRenew 값, 도메인 잠금 상태.

### R5. ACR을 GHCR로 이관 (2027-03 이전, 기존 문서 §4 그대로)

변경 없음. 지금도 매달 나가는 유일한 비용(월 약 ₩7,000~7,500)을 없앤다. 가장 위험한 지점은 기존 문서 §4-4에 정리된 `useBackendAcrImage` 플래그 분리다. R1이 같은 Bicep 경로를 먼저 건드리므로 **R1을 먼저 머지하고 R5를 그 위에 쌓는다.** R6의 SQLite안을 택하면 이미지가 약 1GB 커지는데, 공개 GHCR 패키지는 저장과 전송이 무료라 R5가 R6의 선행 조건이 된다.

### R6. PG 대체 결정 (2027-03 결정, 05-27 이전 완료)

기존 문서 §5-3의 선택지에 두 가지를 더한다. 만료 후 월 청구액은 2026-08 단가 기준이다.

| 안 | 내용 | 만료 후 월액 (R5 완료 기준) | 관리 부담 |
|---|---|---:|---|
| (a) 예산 상향 | 구조 변경 없음, 24/7 가동 | ₩36,118 | 낮음 |
| (b) 야간 정지 확대 (GitHub cron) | 기존 문서안 | ₩18,802 (이론값) | **실현 불가**: 2~5시간 지연이면 업무시간을 통째로 놓친다 |
| **(b′) 업무시간 가동 (Azure Automation)** | (b)를 Automation 일정으로 구현, KST 09~19시 | ₩18,802 | 중간: PG 서버, runbook, 7일 자동 재기동 규칙이 남는다 |
| (c) 외부 무료 PG | Neon, Supabase | ₩0 | Neon은 용량 부족, Supabase는 7일 정지로 부적합 |
| **(d) 이미지 내장 SQLite (권고)** | 정적 참조 데이터를 읽기 전용 SQLite 파일로 만들어 컨테이너 이미지에 넣는다 | **약 ₩0** | **가장 낮음**: DB 서버, 야간 정지, 방화벽, 비밀번호가 모두 사라진다 |

**(d)를 권고하는 이유**

1. **데이터가 정적이다.** 운영 PG를 쓰는 곳은 `backend/db/repository.py`와 `backend/db/dao/`의 DAO 9개(seoulRtms, mapInfo, sangkwon, sangkwonStore, dongMapping, landValue, landmark, molitRtms, 공통 baseDAO)뿐이다. 모두 상권, 실거래가, 지가 같은 참조 데이터를 읽는다. 사용자 데이터는 Cosmos에 있다.
2. **크기가 감당할 만하다.** 2026-06 컷오버 때 이전한 데이터는 11개 테이블, 313만 행, 약 1.16GB다. 현재 `storage_used` 지표 최대값 5.32GB는 WAL과 로그를 포함한 상한이다. 기존 문서 §2-4의 1GB 미만 기술은 이 값으로 고친다.
3. **이전 검토의 기각 사유가 해당하지 않는다.** [self-hosted-rag-and-db-cost-optimization.md](self-hosted-rag-and-db-cost-optimization.md)가 SQLite를 밀어낸 이유는 쓰기 가능한 벡터 저장소를 Container App의 휘발성 디스크에 두는 문제였다. 이미지에 넣은 읽기 전용 파일은 모든 레플리카가 같은 사본을 가지므로 영속성, 일관성 문제가 없다.
4. **현상유지와 맞는다.** 데이터를 갱신할 계획이 없으므로 이미지에 고정해도 잃는 것이 없다.

**(d)의 비용**

- DAO 9개의 SQL 문법 이전이 1회 필요하다. 바뀌는 것은 `%s` 자리표시자, `ILIKE`, 형 변환, 시작 시 인덱스 생성(빌드 시점으로 옮김) 등이다.
- 이미지가 약 1GB 커져 cold start가 길어진다. 측정해서 수용 가능 여부를 본다.
- 덤프에서 SQLite 파일을 만드는 빌드 스크립트 1개가 필요하다. 데이터가 바뀌지 않으므로 한 번 만들어 GHCR 이미지에 고정한다.

**결정 전에 확인할 것 (게이트)**

1. R1로 PG가 복구된 상태에서 테이블별 실제 크기와 행 수를 잰다. 2026-06의 1.16GB가 지금도 맞는지 확인한다.
2. 운영 코드에 PG 쓰기 경로가 없는지 확인한다. 시작 시 인덱스 생성 외에 INSERT나 UPDATE가 있으면 (d)의 전제가 깨진다.
3. pgvector 테이블이 운영에서 쓰이지 않는지 확인한다(`RAG_BACKEND=disabled`).
4. 1GB 파일을 넣은 이미지의 cold start 시간을 잰다.

게이트 1, 2, 3 중 하나라도 실패하면 (b′)로 간다.

### R7. 정기 점검 일정 고정

| 시점 | 점검 | 실패 시 |
|---|---|---|
| 2026-11-01 이후 | keepalive 첫 일정 실행 성공 여부 | 수동 실행 후 원인 조사 |
| 2026-12-06 이후 | 일정 워크플로가 여전히 active인가 (keepalive 실효성) | 비활성화되면 R6 완료 시점까지 월 1회 빈 커밋 등 대체 수단 |
| 2027-02 | 도메인 결정 실행 (R4) | 최후 기한 2027-03-22 (이전 소요 7일) |
| 2027-03 | R6 결정, 기존 문서 §5-4의 재실측 명령 실행 | |
| 2027-07 경 | 모델 퇴역 60일 전 통지 수신 확인 | 통지가 없으면 Models API로 직접 조회 |
| 2027-09-21 이후 | 자동 업그레이드된 모델로 도메인별 질의 몇 건을 돌려 Sign-off 등급 확인 | 등급이 무너지면 프롬프트 보정 또는 버전 고정 |

---

## 4. 결론 지도 (게이트별 분기)

| 게이트 | 시점 | 통과 | 실패 |
|---|---|---|---|
| G1. R1과 R2를 승인하는가 | 즉시 | 같은 PR로 반영, 배포 후 PG 기능 복구 확인 | PG 기능 중단 상태를 받아들이고 R6 (d)로 바로 간다. 이 경우 R6 게이트 1은 2026-06 수치로 대신한다. |
| G2. R1 배포가 Node 24 환경에서 성공하는가 | R1 배포 시 | 다음 단계 진행 | 액션 버전 갱신이 먼저다 |
| G3. keepalive가 실효적인가 | 2026-12-06 이후 | 유지 | 대체 수단 적용 (R7) |
| G4. 구 구독에 접근할 수 있는가 | 2027-02 이전 | R4 (가) 또는 (나) | R4 (나) 강제. 접근도 이전도 안 되면 새 도메인을 검토한다 |
| G5. R6 게이트 1~4 | 2027-03 | (d) SQLite 실행 | (b′) Automation 업무시간 가동, 또는 (a) 예산 상향 |
| G6. 모델 업그레이드 뒤 Sign-off 등급 | 2027-09-21 이후 | 유지 | 프롬프트 보정 |

---

## 5. 작업 표

| ID | 작업 | 선행 | 규모 | 시점 |
|---|---|---|---|---|
| T1 | Bicep에 `pg-password` secret과 `PG_PASSWORD` env 추가 (R1) | 없음 | 작음 | 즉시 |
| T2 | 야간 정지 일정 실행을 저장소 변수로 끔 (R2) | 없음 | 작음 | T1과 같은 PR |
| T3 | Bicep 배포 실행, PG 기능 복구 확인 | T1 | 작음 | T1 머지 직후 |
| T4 | 주간 심층 점검 워크플로 추가, keepalive 대상에 등록 (R3) | T3 | 작음 | T3 직후 |
| T5 | Service Health 알림 생성 (R3) | 없음 | 작음 | 즉시 |
| T6 | 실제 DB 크기, 쓰기 경로, pgvector 사용 실측 (R6 게이트 1~3) | T3 | 작음 | T3 직후 |
| T7 | 구 구독 접근과 도메인 상태 확인 (R4) | 없음 | 작음 | 2026-12 이전 |
| T8 | ACR을 GHCR로 이관 (R5) | T1 | 중간 | 2027-03 이전 |
| T9 | SQLite 빌드 스크립트, DAO 9개 이전, cold start 측정 (R6 (d)) | T6, T8 | 중간 | 2027-03~04 |
| T10 | PG 서버, 야간 정지 워크플로, keepalive 대상 정리 | T9 | 작음 | 2027-05-27 이전 |

---

## 6. 기존 문서와의 관계

[azure-freetier-cliff-2027.md](azure-freetier-cliff-2027.md)에서 바뀌는 내용:

| 절 | 바뀌는 점 |
|---|---|
| §2-4 | PG 실사용량 1GB 미만은 근거가 약하다. 이전 데이터 1.16GB, 저장소 지표 최대 5.32GB(WAL 포함 상한)로 고친다. |
| §3 | 야간 정지 유지 결정은 그대로다. 단, 무료 기간에는 일정 실행을 끈다(R2). |
| §5-3 (b) | GitHub cron으로는 실현할 수 없다. (b′) Azure Automation안으로 대체한다. |
| §5-3 | (d) 이미지 내장 SQLite안을 더하고 권고안으로 둔다. |
| §6 | 도메인 만료(2027-03-29), 모델 퇴역(2027-09-21), keepalive 판정(2026-12-06)을 일정에 더한다. |

---

## 7. 출처

- [Azure Container Apps pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/)
- [Use an Azure free account to try Azure Database for PostgreSQL flexible server](https://learn.microsoft.com/en-ie/azure/postgresql/flexible-server/how-to-deploy-on-azure-free-account)
- [Cost optimization in Azure Database for PostgreSQL flexible server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/how-to-cost-optimization)
- [Azure Automation pricing](https://azure.microsoft.com/en-us/pricing/details/automation/)
- [Automation runbook로 PG Flexible Server 시작, 정지 (Microsoft Q&A)](https://learn.microsoft.com/en-us/answers/a/1321970)
- [Foundry Models lifecycle and support policy](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/model-retirements)
- [Deprecation of Node 20 on GitHub Actions runners](https://github.blog/changelog/2026-09-23-deprecation-of-node-20-on-github-actions-runners/)
- [Scheduled recurring tasks와 GitHub cron 지연 (Flutter 인프라 문서)](https://flutter.googlesource.com/mirrors/flutter/+/refs/heads/main/docs/infra/Scheduled-Recurring-Tasks.md)
- [How to prevent GitHub from suspending your cronjob based triggers](https://dev.to/gautamkrishnar/how-to-prevent-github-from-suspending-your-cronjob-based-triggers-knf)
- [Neon pricing](https://neon.com/pricing)
- [Supabase free tier limits 2026](https://automationatlas.io/answers/supabase-free-tier-limits-2026/)
