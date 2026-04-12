# 백엔드 로그 조회 가이드

현재 배포 백엔드: **Azure Container Apps**
URL 및 시크릿은 `backend/.env`의 `BACKEND_HOST`, `EXPORT_SECRET` 참조.

> `/api/v1/logs/export` (파일 다운로드)는 Blob Storage 구성으로 인해 사용 불가.
> `/api/v1/logs` 읽기 API를 사용한다.

## 기본 조회

```bash
source backend/.env

# 최근 N개 쿼리 조회 (type: queries | rejections | errors)
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=50" | python3 -m json.tool
```

## 시간대 필터링

```bash
curl -s "$BACKEND_HOST/api/v1/logs?type=queries&limit=200" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for e in data['entries']:
    if '2026-03-26T07:' <= e['ts'] <= '2026-03-26T09:':
        print(e['ts'], e.get('grade'), e.get('retry_count'), e.get('question','')[:60])
"
```

## 참고 스크립트

- `scripts/pull_logs.py` — `BACKEND_HOST` 환경변수 기반 다운로드 스크립트
