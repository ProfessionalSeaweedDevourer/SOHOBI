# 운영 비밀값 주입과 야간 정지 중지: 수동 조치

> 작성: 2026-10-11
> 브랜치: `fix/park-bicep-secrets-nightly-pause`
> 근거: [maintenance-mode-low-cost-ops.md](strategic/maintenance-mode-low-cost-ops.md)의 비밀값 주입(R1), 야간 정지 중지(R2), 화면 백엔드 전환(R8)

---

## 0. 요약

- **머지 전에 할 일은 없다.** 필수 비밀값 3개(PG 비밀번호, JWT, API 키)는 GitHub secret이 이미 있다. 머지하면 Bicep 배포가 바로 새 구독 백엔드의 API 키 인증과 PG 연결을 되살린다.
- **지도 키 3개와 Google OAuth 2개는 선택이다.** 지금 없으면 해당 env 없이 배포된다. 나중에 등록하고 배포를 한 번 더 돌리면 붙는다.
- **이 PR만으로는 사용자 화면이 바뀌지 않는다.** sohobi.net은 아직 구 구독의 옛 백엔드를 부른다. 사용자 경로 복구는 화면 백엔드 전환(R8)을 결정한 뒤의 일이다.

| 순서 | 할 일 | 하는 사람 | 시점 |
|---|---|---|---|
| 1 | PR 머지 (Bicep 배포가 자동 실행됨) | Eric | 지금 |
| 2 | 배포 결과와 새 백엔드 확인 (§3) | Claude | 머지 직후 |
| 3 | 야간 정지가 꺼졌는지 확인 (§6) | Claude | 머지 다음 날 오전 |
| 4 | 구 구독 재로그인, 선택 비밀값 5개 등록, 배포 재실행 (§4) | Eric (등록), Claude (재실행과 확인) | 화면 전환 전 |
| 5 | Google 콘솔에 새 redirect URI 추가 (§5) | Eric | 화면 전환 전 |
| 6 | 화면 백엔드 전환 여부와 시점 결정 (§7) | Eric | 4, 5 뒤 |

---

## 1. 이 PR이 바꾸는 것

### 1-1. 비밀값

새 구독 백엔드(`rg-sohobi-prod`의 `sohobi-backend`)에 들어가는 값이다. 값은 GitHub secret에서 워크플로 env, `prod.bicepparam`의 `readEnvironmentVariable`, Container App secret 순서로 흘러가고, 컨테이너는 secretRef로만 읽는다.

| 컨테이너 env | Container App secret | GitHub secret | 구분 | GitHub 등록 |
|---|---|---|---|---|
| `JWT_SECRET` | `jwt-secret` | `JWT_SECRET` | 필수 | 있음 (2026-06-25, 변경 없음) |
| `PG_PASSWORD` | `pg-password` | `PG_ADMIN_PASSWORD` (재사용) | 필수 | 있음 (2026-04-27) |
| `API_SECRET_KEY` | `api-secret-key` | `API_SECRET_KEY` | 필수 | 있음 (2026-04-07) |
| `VWORLD_API_KEY` | `vworld-api-key` | `VWORLD_API_KEY` | 선택 | 없음 |
| `KAKAO_REST_KEY` | `kakao-rest-key` | `KAKAO_REST_KEY` | 선택 | 없음 |
| `KTO_GW_INFO_KEY` | `kto-gw-info-key` | `KTO_GW_INFO_KEY` | 선택 | 없음 |
| `GOOGLE_CLIENT_ID` | `google-client-id` | `GOOGLE_CLIENT_ID` | 선택 | 없음 |
| `GOOGLE_CLIENT_SECRET` | `google-client-secret` | `GOOGLE_CLIENT_SECRET` | 선택 | 없음 |

- **필수**: env를 `main.bicep`에 무조건 넣는다. 값이 빠지면 배포가 성공하지 않는다.
- **선택**: 모듈이 값이 있을 때만 secret과 env를 한 쌍으로 만든다.
- PG 비밀번호는 Bicep이 같은 배포에서 서버 관리자 비밀번호로도 적용하는 값이라, 앱과 서버가 항상 일치한다.

### 1-2. 배포 전 검사 (`.github/workflows/azure-bicep-deploy.yml`)

| 상황 | what-if (PR) | deploy (main) |
|---|---|---|
| 필수가 비어 있음 | PR 코멘트 첫 줄에 경고 | 이름을 밝히고 배포 전에 멈춤 |
| 선택이 비어 있음 | PR 코멘트 첫 줄에 참고 | 경고만 하고 배포 |

검사는 이름만 출력하고 값은 출력하지 않는다. what-if 코멘트도 secret을 값이 아닌 템플릿 식으로만 보여 준다(PR #373 코멘트로 확인).

### 1-3. 그 밖의 env

- `FRONTEND_URL` = `https://sohobi.net`
- `BACKEND_HOST` = `https://sohobi-backend.<환경 기본 도메인>` (지금은 `https://sohobi-backend.politefield-1cd9d809.koreacentral.azurecontainerapps.io`)

둘 다 Google 로그인 주소용이다(`backend/auth_router.py`). 비우면 기본값 localhost로 돌아간다.

### 1-4. 야간 정지 (`.github/workflows/pg-nightly-stop.yml`)

일정 실행의 정지 job이 저장소 변수 `PG_NIGHTLY_ENABLED`가 `'true'`일 때만 돈다. 변수가 없는 지금 상태가 꺼짐이다. 기동 job, 수동 실행, keepalive 대상은 그대로다.

### 1-5. 이번 PR에서 뺀 것

| 항목 | 이유 | 언제 |
|---|---|---|
| `PG_SSL_MODE`와 `PG_SSLMODE` 이름 정리 | `backend/db/dao/baseDAO.py`를 고치면 `backend/**` push가 되어 `deploy-backend.yml`이 옛 백엔드(사용자 경로)로 배포한다. 두 이름 모두 기본값 `require`라 지금은 무해하다. | `deploy-backend.yml` 정리 뒤, 또는 SQLite 이전 때 |
| Blob 질의 로그 설정 | 코드는 `BLOB_LOGS_ACCOUNT`, `BLOB_LOGS_CONTAINER`를 읽는데, Bicep은 아무 코드도 읽지 않는 `AZURE_STORAGE_CONTAINER`만 넣는다. 그래서 새 백엔드의 질의 로그는 Blob에 남지 않는다. 비밀값이 아니고, 저장소 권한 부여도 함께 확인해야 한다. | 화면 전환 전 별도 PR |

---

## 2. 머지와 배포 (Eric)

1. PR의 Bicep what-if 코멘트에서 첫 줄을 본다.
   - `참고: 미등록 선택 GitHub secret ...`은 정상이다.
   - `경고: 미등록 필수 ...`가 있으면 머지하지 않는다.
2. 머지한다. `infra/bicep/**`가 바뀌었으므로 Bicep 배포가 자동으로 돈다.
3. 이번 실행은 이 워크플로가 Node 24 환경에서 도는 첫 실행이다. 액션 버전 때문에 실패하면 액션 갱신이 먼저다.

배포는 새 구독의 자원 전체에 다시 적용된다. 6/25 이후 Bicep 밖에서 바꾼 설정이 있었다면 되돌아간다. 알려진 것은 없다.

---

## 3. 배포 후 확인 (Claude가 실행, 결과는 PR 코멘트)

새 백엔드 주소로 확인한다. 로컬 `backend/.env`의 `BACKEND_HOST`는 **옛 백엔드**이므로 쓰지 않는다.

```zsh
cd /Users/eric.j.park/Documents/GitHub/SOHOBI
NEW=https://sohobi-backend.politefield-1cd9d809.koreacentral.azurecontainerapps.io
# 0) 새 리비전이 Healthy, Running 인지. 이 리비전이 6/25 이후 처음 PG 에 닿으므로 시작 시 인덱스 확인
#    (CREATE INDEX IF NOT EXISTS)이 돈다. 인덱스가 이미 있으면 즉시 끝나고, 없으면 startup probe 한도(150초)를 볼 것
az containerapp revision list -n sohobi-backend -g rg-sohobi-prod \
  --query "[?properties.active].{name:name, health:properties.healthState, state:properties.runningState}" -o table
# 1) 키 없는 호출: 401 이어야 한다 (배포 전 실측 200)
curl -s -o /dev/null -w '%{http_code}\n' "$NEW/realestate/sangkwon-quarters"
# 2) 로컬 키 호출: 200 이고 latest 에 분기 값이 있어야 한다 (배포 전 실측 latest=null)
( set -a; source backend/.env; set +a
  curl -s -H "X-API-Key: $API_SECRET_KEY" "$NEW/realestate/sangkwon-quarters" | head -c 200; echo )
# 3) secret 이름 3개 (jwt-secret, pg-password, api-secret-key). 값은 나오지 않는다
az containerapp secret list -n sohobi-backend -g rg-sohobi-prod --query "[].name" -o tsv
# 4) Google: 선택 비밀값을 등록하기 전에는 501, 등록한 뒤에는 Google 로 302
curl -s -o /dev/null -w '%{http_code}\n' "$NEW/auth/google"
```

2번이 401이면 GitHub의 `API_SECRET_KEY`가 프론트엔드 키와 다르다는 뜻이다. 2026-10-11 실측으로 로컬 `backend/.env`의 키는 프론트엔드의 `VITE_API_KEY`와 같고, 옛 백엔드도 이 키를 받는다. 이때는 로컬 값으로 다시 등록하고 배포를 재실행한다.

```zsh
( set -a; source backend/.env; set +a
  printf '%s' "$API_SECRET_KEY" | gh secret set API_SECRET_KEY )
gh workflow run azure-bicep-deploy.yml --ref main
```

이 secret은 옛 백엔드용 `deploy-backend.yml`도 쓴다. 옛 백엔드가 이미 받는 값과 같으므로 그쪽에 영향은 없다.

---

## 4. 선택 비밀값 등록 (Eric, 화면 전환 전)

### 4-1. 값의 출처

| GitHub secret | 쓰는 API | 출처 |
|---|---|---|
| `VWORLD_API_KEY` | `/map/pnu-by-coord`, `/map/land-use` | 옛 백엔드. 로컬 `frontend/.env.local`의 `VITE_VWORLD_API_KEY`가 같은 키일 수 있으나 확인하지 않았다 |
| `KAKAO_REST_KEY` | `/map/dong-centroids` | 옛 백엔드. `frontend/.env.local`의 `VITE_KAKAO_API_KEY`가 REST 키인지는 Kakao Developers에서 확인해야 한다 |
| `KTO_GW_INFO_KEY` | `/map/festivals` | 옛 백엔드. 로컬 `backend/.env`에도 있다 |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | `/auth/google` | 옛 백엔드, 또는 Google Cloud Console |

옛 백엔드가 기준이다. 2026-06에 새 백엔드에 넣었던 값도 옛 백엔드에서 읽어 온 것이다.

### 4-2. 구 구독 재로그인

2026-10-11 기준 구 구독의 CLI 로그인은 90일 무활동으로 만료됐다. 구 구독에 az 명령을 보내면 만료 오류와 함께 재로그인 명령(`az login --tenant ...`)이 그대로 출력되니, 그 명령을 실행해 구 계정으로 로그인한다. 그다음 `az account list -o table`에서 구 구독의 id를 확인한다.

### 4-3. 옛 백엔드에서 옮기기

SOHOBI 폴더에서 zsh로 실행한다. 값은 화면에 나오지 않고 표준입력으로 `gh secret set`에 넘어간다.

```zsh
cd /Users/eric.j.park/Documents/GitHub/SOHOBI
OLD_SUB=<구 구독 id>
oldapp() { az containerapp "$@" --subscription "$OLD_SUB" -n sohobi-backend -g rg-ejp-9638; }

# 1) 옛 백엔드 env 이름과 secretRef 이름 (값은 나오지 않는다)
oldapp show --query "properties.template.containers[0].env[].join(' -> ', [name, secretRef || 'plain'])" -o tsv

# 2) 선택 비밀값 5개를 GitHub secret 으로 옮긴다
for k in VWORLD_API_KEY KAKAO_REST_KEY KTO_GW_INFO_KEY GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET; do
  ref=$(oldapp show --query "properties.template.containers[0].env[?name=='$k'] | [0].secretRef || ''" -o tsv)
  if [ -n "$ref" ]; then
    val=$(oldapp secret show --secret-name "$ref" --query value -o tsv)
  else
    val=$(oldapp show --query "properties.template.containers[0].env[?name=='$k'] | [0].value || ''" -o tsv)
  fi
  if [ -n "$val" ]; then
    printf '%s' "$val" | gh secret set "$k" && echo "$k: 등록함"
  else
    echo "$k: 옛 백엔드에 없음"
  fi
  unset val
done

# 3) 확인 (이름과 갱신일만 나온다)
gh secret list
```

이 스크립트는 실행해 보지 못했다(작성 시점에 구 구독 로그인이 만료 상태였다). 쿼리 식은 가짜 JSON으로 확인했다. secretRef로 들어간 값, 평문 env 값, 값이 없는 경우를 각각 시험했다.

### 4-4. 옛 백엔드에 없을 때

- `KTO_GW_INFO_KEY`는 로컬 `backend/.env`에서 옮긴다.

  ```zsh
  ( set -a; source backend/.env; set +a
    printf '%s' "$KTO_GW_INFO_KEY" | gh secret set KTO_GW_INFO_KEY )
  ```

- 나머지는 `gh secret set <이름>`을 실행하고 프롬프트에 붙여넣는다. 입력은 화면에 보이지 않는다.

### 4-5. 배포 재실행과 확인

등록이 끝나면 Claude에게 배포 재실행을 요청하거나 직접 실행한다.

```zsh
gh workflow run azure-bicep-deploy.yml --ref main
```

Claude가 확인할 것:
- `/map/festivals`, `/map/pnu-by-coord`, `/map/dong-centroids`가 데이터를 돌려준다.
- `/auth/google`이 Google로 302 응답하고, redirect_uri가 `BACKEND_HOST/auth/google/callback`이다.

---

## 5. Google 콘솔 redirect URI (Eric, 화면 전환 전)

Google Cloud Console에서 API 및 서비스, 사용자 인증 정보로 가 `GOOGLE_CLIENT_ID`의 OAuth 클라이언트를 연다. 승인된 리디렉션 URI에 다음을 추가한다.

```text
https://sohobi-backend.politefield-1cd9d809.koreacentral.azurecontainerapps.io/auth/google/callback
```

옛 백엔드의 URI는 화면 전환이 끝날 때까지 지우지 않는다.

---

## 6. 야간 정지 (할 일 없음)

- 변수가 없으면 일정 정지가 꺼진 상태다. 머지 다음 날 오전에 Claude가 실행 기록에서 정지 job이 건너뛰어졌는지 확인한다.
- 수동 정지와 기동은 그대로 쓸 수 있다: `gh workflow run pg-nightly-stop.yml -f action=stop` (또는 `start`)
- 점검이나 긴급 시 일정 정지를 임시로 켜고 끄기:

  ```zsh
  gh variable set PG_NIGHTLY_ENABLED --body true   # 켜기
  gh variable delete PG_NIGHTLY_ENABLED            # 끄기 (기본 상태)
  ```

- 야간 정지를 되살리는 것은 PG를 유지하기로 결정했을 때뿐이다. 그때는 이 변수가 아니라 Azure Automation 일정으로 옮긴다(기획 문서 R6 (b′)).

---

## 7. 결정: 화면 백엔드 전환 (R8)

**현재**
- sohobi.net의 JS 번들은 구 구독의 옛 백엔드를 부른다(2026-10-11 번들 확인).
- 옛 백엔드도 PG를 거치는 API가 빈 결과를 돌려준다. 원인은 구 구독 로그인 만료로 확인하지 못했다.
- 구 구독 비용은 측정하지 않았다.

**전환 방법**
1. GitHub secret `VITE_API_URL`을 새 백엔드 주소로 바꾼다.
2. 프론트엔드 배포 워크플로를 다시 돌린다.

`VITE_API_KEY`는 그대로 둔다. SWA와 도메인은 구 구독에 남는다.

**선행**: 3절의 확인, 4절, 5절.

**영향**
- 새 백엔드의 JWT 서명 키가 옛 백엔드와 다르면 사용자가 다시 로그인해야 한다.
- 2026-06-11 데이터 이전 이후 옛 Cosmos에 쌓인 대화 기록은 새 Cosmos에 없다.

**전환 뒤**
- 옛 백엔드를 끈다.
- `deploy-backend.yml`을 정리한다.
- 구 구독 비용을 실측한다.

상세: 기획 문서 R8.

---

## 8. 이 PR 밖의 Eric 조치 (기획 문서 일정대로)

| 항목 | 시점 | 비고 |
|---|---|---|
| Azure OpenAI 서비스 상태 알림 생성 (기획 문서 T5) | 즉시 | 운영 자원 변경이라 승인하면 Claude가 만든다 |
| 구 구독 접근과 sohobi.net 도메인 상태 확인 (기획 문서 T7) | 2026-12 이전 | 4-2의 재로그인과 함께 하면 한 번에 끝난다 |
| 구 구독 비용 실측 | 재로그인 직후 | 옛 백엔드, SWA, 남은 자원 확인 |
