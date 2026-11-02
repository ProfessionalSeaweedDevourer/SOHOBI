# sohobi.net 장애 원인과 복구 기획

> 작성: 2026-11-02 (실측 시각 10:30~10:45 KST)
> 상태: 기획, Eric 결정 대기 (§7)
> 선행 문서: [maintenance-mode-low-cost-ops.md](strategic/maintenance-mode-low-cost-ops.md)(화면 백엔드 전환 R8, 도메인 만료 대응 R4), [2026-10-11-bicep-secrets-manual-actions.md](2026-10-11-bicep-secrets-manual-actions.md)

---

## 0. 요약

- **sohobi.net은 DNS 단계에서 죽어 있다.** 도메인 등록과 DNS zone은 살아 있지만, 루트 A 레코드가 빈 값을 돌려준다. 화면을 서빙하던 Static Web App(SWA)과 옛 백엔드가 구 구독에서 사라졌기 때문이다.
- **직접 원인은 구 교육용 테넌트(miee.dev, 구독 ME-M365EDU102388)의 정리다.** 2026-10-22 11:14 KST와 10-23 11:19 KST 사이에 이 테넌트에서 GitHub Actions 서비스 주체가 삭제됐고, 지금은 `miee.dev` 도메인 자체가 어느 Entra 테넌트에도 연결되어 있지 않으며 `eric.park@miee.dev` 계정은 존재하지 않는다고 응답한다.
- **장애 기간은 2주가 아니라 최대 11일이다** (10-22 11:14 KST 이후 시작, 11-02 실측 시점까지). 그 사이 아무도 몰랐다. 매일 실패한 정리 워크플로 10회가 유일한 신호였다.
- **근본 원인은 서비스의 얼굴(도메인, DNS, 화면)이 Eric이 통제하지 못하는 테넌트에 남아 있었다는 점이다.** 백엔드와 데이터는 6월에 새 구독으로 옮겼지만 화면 전환(R8)과 도메인 이전(R4)이 남아 있었고, 그 사이에 집주인이 집을 비웠다.
- **새 구독 쪽은 대부분 살아 있다.** 새 백엔드 `/health` 200, API 키 인증 작동(무키 401), PG 데이터 응답. 다만 질의 파이프라인(`/api/v1/query`)이 OpenAI 404로 전부 실패한다. 원인은 Bicep이 `AZURE_SIGNOFF_DEPLOYMENT`를 넣지 않은 것이고, 한 줄로 고친다(§2-4).
- **가장 큰 위험은 도메인 상실이다.** sohobi.net 등록은 구 구독의 Azure App Service Domain이고 만료가 2027-03-29, 자동 갱신은 꺼져 있다(6월 실측). 구 구독 접근을 되찾지 못하면 도메인은 만료일에 떨어진다.

---

## 1. 실측 기록

### 1-1. 지금 상태 (2026-11-02)

| 대상 | 측정 | 결과 |
|---|---|---|
| `sohobi.net` A (권한 서버 ns1-01.azure-dns.com 직접) | `dig A sohobi.net @ns1-01.azure-dns.com` | 응답 없음(NODATA). TXT 2개(SWA 도메인 검증 토큰, Google 사이트 검증)는 그대로 |
| `www.sohobi.net` | 같은 서버 | NXDOMAIN |
| 등록 | whois | Wild West Domains(Reseller: Azure), 만료 2027-03-29, NS는 Azure DNS 그대로, 상태 ACTIVE |
| 옛 SWA `delightful-rock-0de6c000f.6.azurestaticapps.net` | curl | 404 (사이트 없음) |
| 옛 백엔드 `sohobi-backend.livelybay-7bc24b2f...` | DNS | 이름 풀이 실패 (Container Apps 환경 소멸) |
| 새 백엔드 `sohobi-backend.politefield-1cd9d809...` | `/health`, 무키 호출, 키 호출 | 200(콜드 스타트 55초), 401, 200(분기 목록 응답) |
| 새 백엔드 질의 | `POST /api/v1/query` | 실패. 로그: `domain=unknown`, `Error code: 404 Resource not found` (§2-4) |
| 새 백엔드 Google 로그인 | `/auth/google` | 501 (Google 비밀값 미등록, 예상대로) |
| 구 테넌트 `62ae463a-...` | OpenID 설정 | 테넌트는 존재 |
| 구 계정 `eric.park@miee.dev` | GetCredentialType, getuserrealm | 존재하지 않음(IfExistsResult=1), 네임스페이스 Unknown |
| `miee.dev` 도메인의 테넌트 | `login.microsoftonline.com/miee.dev/...` | `AADSTS90002: Tenant 'miee.dev' not found` |
| 구 구독 CLI | `az group list` | 토큰 만료(마지막 발급 2026-06-11). 재로그인 수단 없음(계정 소멸) |

### 1-2. 시점

| 시각 (KST) | 사건 | 근거 |
|---|---|---|
| 2026-10-11 | 새 백엔드, 옛 백엔드, sohobi.net 모두 200 | 운영 기획 §3 서비스 응답 실측 |
| 2026-10-22 11:14 | 구 테넌트 서비스 주체로 로그인 성공, 옛 SWA 조회 성공 ("No staging environments") | 정리 워크플로 run 39710237848 |
| 2026-10-23 11:19 | 같은 서비스 주체 로그인 실패: `AADSTS700016: Application ... was not found in the directory '62ae463a-...'` | run 39888976839 |
| 10-23 ~ 11-01 | 정리 워크플로 10일 연속 실패, 아무도 대응하지 않음 | `gh run list` |
| 2026-11-02 | 장애 확인 | §1-1 |

SWA가 사라진 정확한 시각은 구 구독 활동 로그(90일 보존)가 있어야 안다. 서비스 주체 삭제와 같은 정리 작업으로 보는 것이 가장 단순한 설명이지만 확인한 사실은 아니다.

---

## 2. 원인

### 2-1. 직접 원인

구 교육용 테넌트에서 디렉터리 수준 정리가 일어났다. 확인한 것은 세 가지다: 서비스 주체 삭제(10-22~23), `miee.dev` 도메인의 테넌트 연결 해제, `eric.park@miee.dev` 계정 소멸. 그 결과 SWA와 옛 Container Apps 환경이 사라졌고, SWA를 가리키던 Azure DNS 별칭 A 레코드가 빈 값이 됐다(Azure DNS 별칭은 대상 자원이 사라지면 빈 레코드가 되도록 설계되어 있어 하위 도메인 탈취 위험은 없다).

DNS zone은 여전히 권한 응답을 하므로 구 구독 또는 zone 자원은 남아 있다. 구독이 비활성인지, 자원 일부만 삭제됐는지는 로그인 없이 구분할 수 없다.

### 2-2. 근본 원인

2026-04 테넌트 이전 기획 이후 백엔드와 데이터는 새 구독(`rg-sohobi-prod`)으로 옮겼지만, 사용자가 실제로 닿는 세 가지가 구 테넌트에 남았다.

| 남은 것 | 그대로 둔 이유 | 기획상 처리 |
|---|---|---|
| 화면(SWA)과 옛 백엔드 | 화면 전환(R8)이 비밀값 주입 뒤로 미뤄짐 | R8, Eric 결정 대기 |
| DNS zone | 도메인과 같이 움직여야 함 | R4 |
| 도메인 등록(App Service Domain) | 테넌트 간 이동 불가, 외부 이전만 가능 | R4, 기한 2027-02 |

운영 기획(10-11)은 이 의존을 알고 있었지만 위험을 '도메인 만료 2027-03-29'라는 날짜로만 봤다. 구 테넌트가 그 전에 정리될 수 있다는 경우는 다루지 않았다. 교육용 테넌트는 Eric이 관리자가 아니고, 언제든 관리자 판단으로 정리될 수 있는 남의 집이었다.

### 2-3. 탐지 실패

- 외부에서 sohobi.net을 주기적으로 확인하는 장치가 없다. `smoke-test.yml`은 push에만 돈다.
- 유일한 신호는 정리 워크플로의 매일 실패였다. 실패 알림 메일은 갔겠지만 대응으로 이어지지 않았다.

### 2-4. 새 백엔드 질의 실패 (화면 복구의 선행 조건)

**원인: 새 컨테이너에 `AZURE_SIGNOFF_DEPLOYMENT`가 없다.** 라우터와 에이전트 초안 생성(약 8.6초)은 정상이고, 그다음 최종 검증(Sign-off) 호출이 실패한다. 로그의 `domain=unknown`은 예외 처리기가 `req.domain or "unknown"`을 기록한 값일 뿐이다(`backend/api_server.py:440`).

- `backend/signoff/signoff_agent.py:153`의 `os.getenv("AZURE_SIGNOFF_DEPLOYMENT")`에는 대체값이 없어 `model=None`이 된다.
- `infra/bicep/main.bicep:163-164`는 `AZURE_DEPLOYMENT_NAME`, `AZURE_OPENAI_CHAT_DEPLOYMENT`만 넣는다. 옛 백엔드와 로컬 `backend/.env`에는 이 값이 있어서 지금까지 드러나지 않았다.
- 재현(openai 2.30.0): `model=None`이면 요청 주소에서 배포명 경로가 빠져 `POST .../openai/chat/completions?api-version=2024-08-01-preview`가 `404 Resource not found`로 실패한다. 운영 오류 문자열과 같다. `model="gpt-5.4-mini"`이면 정상 응답한다.
- 배제한 후보: api-version(세 판 모두 정상), 엔드포인트, 관리 ID 권한(권한 문제면 401), 하드코딩된 옛 엔드포인트(없음).

**수정**: `main.bicep` env 배열에 `{ name: 'AZURE_SIGNOFF_DEPLOYMENT', value: openai.outputs.chatDeploymentName }` 한 줄을 넣고 Bicep 배포를 돌린다. infra만 바뀐다. `signoff_agent.py`에 `AZURE_DEPLOYMENT_NAME` 대체값을 두는 보강도 같은 PR에 넣을 수 있다(§2-5대로 `backend/**` push는 이제 사용자 경로에 닿지 않는다).

### 2-5. 장애가 무효로 만든 기존 계획

| 기존 계획 | 무효 이유 | 대체 |
|---|---|---|
| 선택 비밀값 5개를 옛 백엔드에서 옮기는 스크립트 (수동 조치 문서 §4-3) | 옛 백엔드가 없다 | 원천 콘솔(VWorld, Kakao Developers, 공공데이터포털, Google Cloud Console)에서 다시 받는다. `KTO_GW_INFO_KEY`는 로컬 `backend/.env`에 있다 |
| `backend/**` push 금지 (옛 백엔드로 배포되므로) | `deploy-backend.yml`의 대상이 사라졌다. 이제 push하면 그 워크플로가 실패할 뿐이다 | `deploy-backend.yml`을 지우고 `build-backend-new.yml`을 주 배포 경로로 삼는다 |
| 화면 전환은 Eric이 시점을 고른다 (R8) | 옛 화면이 없다. 전환이 곧 복구다 | §4 단계 1 |
| 도메인 결정은 2027-02까지 (R4) | 접근 수단 자체가 사라졌다 | §4 단계 2, 지금 시작 |

### 2-6. 아마 잃은 것 (확인 불가)

옛 백엔드가 6-11 이후 구 구독의 PG와 Cosmos에 썼다면, 6-11부터 10-22까지의 가입자, 대화 세션, 질의 로그는 구 구독에만 있다. 새 구독 데이터는 6-11 사전 적재분이다. 구 구독 접근을 되찾으면 가장 먼저 이 데이터를 뺀다(§4 갈래 A).

---

## 3. 목표

**진짜 목표**: sohobi.net이 다시 열리고, Eric이 통제하지 못하는 곳에 서비스의 어떤 부분도 남지 않으며, 다음 장애는 11일이 아니라 30분 안에 Eric이 안다.

글자 그대로의 요청(장애 조사, 원인, 조치 기획)과의 차이: 복구만이 아니라 같은 종류의 장애가 다시 일어날 수 없게 만드는 것과, 일어나더라도 바로 알게 만드는 것까지를 목표로 잡는다.

| 단계 | 내용 | 판정 |
|---|---|---|
| 1. 서비스 재개 | 새 구독에 SWA를 만들고 새 백엔드를 붙여 `*.azurestaticapps.net`에서 화면을 연다 | 외부 curl 200, 화면에서 질의 1건이 등급 A 또는 B로 돌아옴 |
| 2. 주소 되찾기 | sohobi.net을 Eric 명의 등록기관으로 옮기고 DNS를 Eric 통제 아래 둔다 | whois 등록기관 변경, 만료일 1년 연장, sohobi.net 200 |
| 3. 재발 차단 | 남의 테넌트, 개인 계정 의존을 0으로 만들고 외부 가동 감시를 둔다 | 의존 목록 0건, 감시가 실제 장애를 30분 안에 알림으로 올림(모의 장애로 시험) |

---

## 4. 복구 경로

### 단계 1. 서비스 재개 (Eric 승인 후 당일, 구 테넌트와 무관)

1. 새 백엔드 질의 실패를 고친다(§2-4).
2. 새 구독 `rg-sohobi-prod`에 SWA(Free, 비용 0)를 만든다. Bicep에 넣어 이후 배포가 지우지 않게 한다.
3. 프론트엔드 배포 워크플로를 새 SWA로 바꾼다. 새 배포 토큰을 GitHub secret으로 등록하고, `VITE_API_URL`, `VITE_MAP_URL`, `VITE_REALESTATE_URL`을 새 백엔드 주소로 바꾼다. 미리보기 정원 검사와 정리 워크플로는 구 테넌트 자격증명(`AZURE_CREDENTIALS`)을 쓰므로 새 테넌트 자격증명(`*_B`)으로 옮긴다.
4. 새 백엔드에 `CORS_EXTRA_ORIGINS`로 새 SWA 주소를 넣는다(env라 `backend/**` 변경 없음).
5. 지도 키(Kakao JS, VWorld)의 허용 도메인에 새 SWA 주소를 더한다(Eric, 각 콘솔).
6. 선택 비밀값 5개를 원천 콘솔에서 받아 GitHub secret으로 등록하고 Bicep 배포를 다시 돌린다. Google 콘솔에 새 redirect URI를 더한다(Eric).

판정: 외부 curl 200, Playwright로 첫 화면, 질의 1건(등급 A/B), 지도 화면, 로그인 302를 확인한다. 4~6이 늦어지면 지도와 로그인 없이 먼저 연다.

### 단계 2. 주소 되찾기 (갈래가 구 테넌트 접근 여부로 갈린다)

**먼저 할 일 (Eric, 10분)**: 구 테넌트 관리자에게 연락한다. 구독 이름의 `joowonjeong`과 교육 과정 운영 측이 후보다. 물을 것은 셋이다. (1) 테넌트를 언제 왜 정리했는가, (2) 구독 `5919b1b2-b639-42e1-8678-c28553b1661b`과 그 안의 DNS zone, App Service Domain이 아직 있는가, (3) Eric 계정을 임시로 되살리거나, 관리자가 대신 도메인 이전 인증 코드를 발급해 줄 수 있는가.

**갈래 A. 접근을 되찾은 경우**

1. 구 구독 PG, Cosmos가 남아 있으면 6-11 이후 데이터부터 뺀다(§2-6).
2. App Service Domain에서 도메인 잠금을 풀고 이전 인증 코드를 받는다.
3. Eric 명의 등록기관으로 이전한다. 후보는 Cloudflare Registrar(원가 갱신, 루트 도메인 CNAME 평탄화로 SWA를 바로 가리킬 수 있음)다. 이전에 5~7일 걸리고 만료일이 1년 늘어난다.
4. 이전이 끝나기 전이라도, 접근이 살아 있으면 구 DNS zone에 `www` CNAME을 새 SWA로 넣어 www부터 연다.
5. 끝나면 구 테넌트 의존을 모두 끊는다(§4 단계 3).

**갈래 B. 접근을 되찾지 못한 경우**

- 도메인은 2027-03-29에 만료된다. 만료 뒤 유예와 반환 기간을 거쳐 일반 등록으로 풀리면(대개 만료 후 수십 일) 다시 등록한다. 그 사이 제3자가 먼저 잡을 위험이 있다.
- Microsoft 지원(Azure App Service Domain)과 Wild West Domains(GoDaddy 계열)에 소유 입증으로 이전을 요청할 수 있는지 문의한다. 결제 기록(구독 청구서)이 소유 근거다. 성사 가능성은 확인하지 못했다.
- 그동안 쓸 대체 주소를 정한다: 새 SWA 기본 주소로 버티거나, 새 도메인을 산다(§7 결정 3).

### 단계 3. 재발 차단

1. **외부 가동 감시.** GitHub Actions 일정 워크플로가 30분마다 sohobi.net(또는 그 시점의 화면 주소), 새 백엔드 `/health`, 키를 붙인 가벼운 API 1건을 호출한다. 실패하면 이슈를 열거나 갱신해 Eric에게 메일과 모바일 알림이 가게 한다. 성공으로 돌아오면 이슈를 닫는다. keepalive(PR #376) 대상에 넣는다. 비용 0.
2. **죽은 경로 정리.** `deploy-backend.yml`, 구 SWA 워크플로와 정리 워크플로, 구 테넌트 secret(`AZURE_CREDENTIALS`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_SWA_NAME`, `AZURE_STATIC_WEB_APPS_API_TOKEN_DELIGHTFUL_ROCK_0DE6C000F`, `RESOURCE_GROUP`, `CONTAINER_APP_NAME`, `ACR_NAME`)을 지운다. 매일 실패하는 워크플로가 남아 있으면 진짜 실패가 묻힌다.
3. **남의 집 의존 목록.** 서비스가 기대는 외부 계정을 전부 적고 소유자를 표시한다. 지금 아는 것: 도메인과 DNS(구 테넌트), 법률 검색 `choi-search`(DNS 응답 없음, 이미 죽었음. 새 백엔드는 `RAG_BACKEND=disabled`), `choi-foundry2`(아직 응답), 지도 키 3종과 Google OAuth(소유 계정 확인 필요). 목표는 Eric 소유가 아닌 것 0건.
4. 운영 기획(`maintenance-mode-low-cost-ops.md`)의 R4, R8을 이 문서로 대체하고, 메모리의 '화면은 옛 백엔드를 부른다' 줄을 갱신한다.

---

## 5. 판단 밖 검증 (실행 전 고정)

| 무엇 | 통과 기준 | 지금 값 |
|---|---|---|
| 화면 재개 | 사내망 밖에서 화면 주소 `curl` 200, Playwright 첫 화면 스냅샷에 입력창 존재 | DNS 실패 |
| 질의 | 화면 경로로 보낸 질의 3건(법률, 상권, 재무)이 등급 A 또는 B | 전부 실패(OpenAI 404) |
| 도메인 | whois 등록기관이 Eric 명의 계정, 만료 2028-03 이후, `https://sohobi.net` 200 | 구 테넌트, 2027-03-29, 실패 |
| 감시 | 감시 대상을 일부러 틀린 주소로 바꾼 모의 장애에서 30분 안에 이슈가 열림 | 장치 없음, 실제 탐지 11일 |
| 의존 | 남의 집 의존 목록 0건 | 최소 3건 |
| Eric 쪽 지표 | 다음 장애를 Eric이 감시 알림으로 먼저 안다(사용자 제보나 우연한 확인이 아니라) | 이번 장애는 우연한 확인 |

결과 확인: 2026-11-16 (감시 워크플로 2주 기록에 놓친 장애가 없는지, 이슈 알림이 실제로 Eric에게 닿았는지)

---

## 6. 반박 (기획의 전제를 깨 보기)

| 전제 | 깨질 수 있는 방식 | 확인 방법 |
|---|---|---|
| 구 테넌트 정리가 원인이다 | 구독 비활성(크레딧 소진, 교육 기간 종료)이 먼저였고 디렉터리 정리는 나중일 수 있다 | 관리자 답변 또는 활동 로그. 결론(접근 회복 필요)은 어느 쪽이든 같다 |
| 새 구독 데이터로 서비스가 성립한다 | 6-11 이후 데이터가 없어 기존 사용자 로그인과 대화 기록이 비어 보인다 | 단계 1 판정 때 PG 사용자 수, Cosmos 최신 문서 날짜를 잰다 |
| Cloudflare로 이전하면 루트 도메인이 SWA를 가리킬 수 있다 | SWA 사용자 지정 도메인 검증이 CNAME 평탄화에서 실패할 수 있다 | 이전 전에 다른 도메인으로 시험하거나, 실패 시 루트는 www로 리디렉션 |
| 감시는 GitHub Actions로 충분하다 | GitHub 일정 실행은 지연, 누락이 있고 60일 무활동이면 꺼진다 | keepalive 대상에 넣고, 2주 기록에서 실행 간격 최대값을 잰다 |

---

## 7. Eric 결정 사항

1. **단계 1(새 구독 SWA로 화면 재개)을 지금 진행하는가.** 구 테넌트와 무관하고 되돌리기 쉽다. 추천: 진행.
2. **구 테넌트 관리자 연락.** Eric만 할 수 있다. 누구에게 연락할지(구독 이름의 `joowonjeong`, 교육 과정 운영 측).
3. **갈래 B일 때 대체 주소.** 새 SWA 기본 주소로 버틸지, 새 도메인을 살지.
4. **도메인 이전 대상 등록기관.** 추천: Cloudflare Registrar.

---

## 8. 과업

| ID | 과업 | 하는 사람 | 선행 | 크기 |
|---|---|---|---|---|
| T1 | 새 백엔드 질의 404 수정: Bicep에 `AZURE_SIGNOFF_DEPLOYMENT` 추가, 배포, 질의 3건 확인 (§2-4) | Claude | 없음 | 작음 |
| T2 | 새 구독 SWA 생성(Bicep), 프론트 배포 워크플로 전환, VITE 주소 3종 교체, CORS env | Claude (secret 값 교체는 Claude가 `gh secret set`) | T1 | 중간 |
| T3 | 지도 키 허용 도메인, Google redirect URI, 선택 비밀값 5개 원천 콘솔에서 재발급 또는 확인 | Eric | T2 주소 확정 | 작음 |
| T4 | 화면 재개 판정 (§5 첫 두 줄) | Claude | T2 | 작음 |
| T5 | 구 테넌트 관리자 연락 | Eric | 없음 | 작음 |
| T6 | 갈래 A: 데이터 추출, 도메인 이전 / 갈래 B: 지원 문의, 대체 주소 | Eric + Claude | T5 | 중간 |
| T7 | 외부 가동 감시 워크플로, 모의 장애 시험 | Claude | T2 | 작음 |
| T8 | 죽은 워크플로와 구 테넌트 secret 정리, 남의 집 의존 목록 | Claude | T2 | 작음 |
| T9 | 운영 기획 R4, R8 대체 표시, 메모리 갱신 | Claude | T4 | 작음 |
