# 백엔드 로그 조회 가이드

현재 배포 백엔드: **Azure Container Apps**
URL 및 시크릿은 `backend/.env`의 `BACKEND_HOST`, `API_SECRET_KEY`, `EXPORT_SECRET` 참조.

> `/api/v1/logs/export` (파일 다운로드)는 Blob Storage 구성으로 인해 사용 불가.
> `/api/v1/logs` 읽기 API를 사용한다.

## 인증

`/api/v1/logs*` 는 `verify_api_key` 게이트 적용 (SEC-001 / PR #309). `API_SECRET_KEY` 를 Bearer 토큰 또는 `X-API-Key` 헤더로 전달한다. 로컬 개발 환경에서 `API_SECRET_KEY` 가 비어 있으면 인증은 통과(skip)된다.

## 기본 조회

```bash
source backend/.env

# 최근 N개 쿼리 조회 (type: queries | rejections | errors)
curl -s \
  -H "Authorization: Bearer $API_SECRET_KEY" \
  "$BACKEND_HOST/api/v1/logs?type=queries&limit=50" | python3 -m json.tool

# 대체: X-API-Key 헤더
# curl -s -H "X-API-Key: $API_SECRET_KEY" "$BACKEND_HOST/api/v1/logs?type=queries&limit=50"
```

## 시간대 필터링

```bash
curl -s \
  -H "Authorization: Bearer $API_SECRET_KEY" \
  "$BACKEND_HOST/api/v1/logs?type=queries&limit=200" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for e in data['entries']:
    if '2026-03-26T07:' <= e['ts'] <= '2026-03-26T09:':
        print(e['ts'], e.get('grade'), e.get('retry_count'), e.get('question','')[:60])
"
```

## 401 응답 시

- `source backend/.env` 를 선행 실행했는지 확인
- `[ -n "$API_SECRET_KEY" ] && echo set` 로 환경변수 주입 여부 확인 (값은 출력 금지)
- 값 오타·공백 포함 시 `hmac.compare_digest` 실패 — `backend/.env` 원본과 Azure Container Apps 의 `API_SECRET_KEY` 값이 일치하는지 대조

## 참고 스크립트

- `scripts/pull_logs.py` — `BACKEND_HOST` 환경변수 기반 다운로드 스크립트
