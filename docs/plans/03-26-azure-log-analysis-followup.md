# Context

세션 리포트(2026-03-26)를 바탕으로 후속 조치를 제시한다. 핵심 요구사항: **Azure Blob Storage에서 최신 queries.jsonl을 직접 내려받아**, 가장 최근 25개 쿼리 로그를 분석하고 개선 항목을 도출한다. 로컬 `logs/queries.jsonl`은 Railway 로그와 이전 Azure 로그를 머지한 구버전이므로 사용하지 않는다.

---

## Step 1 — Azure Blob에서 최신 쿼리 로그 다운로드

```bash
az storage blob download \
  --account-name sohobi9638logs \
  --container-name sohobi-logs \
  --name queries.jsonl \
  --file /tmp/azure_queries_latest.jsonl \
  --auth-mode login \
  --overwrite
```

- 인증: `az account show` 확인 완료 (tenant `62ae463a`)
- Azure CLI 로그인 상태 정상

---

## Step 2 — 최근 25개 항목 추출 및 분석

```python
import json

with open('/tmp/azure_queries_latest.jsonl') as f:
    entries = [json.loads(l) for l in f if l.strip()]

# ts 기준 정렬 후 최근 25개
entries.sort(key=lambda x: x.get('ts', ''))
recent = entries[-25:]

for i, d in enumerate(recent, 1):
    q       = d.get('question', '')
    domain  = d.get('domain', '')
    status  = d.get('status', '')
    grade   = d.get('grade', '')
    retries = d.get('retry_count', 0)
    latency = d.get('latency_ms', 0)
    ts      = d.get('ts', '')[:19]
    rh      = d.get('rejection_history', [])

    print(f"{i:2}. [{ts}] [{domain:10}] [{status:10}] G:{grade} R:{retries} {latency:6.0f}ms")
    print(f"     Q: {q}")
    for r in rh:
        print(f"     REJECT attempt={r.get('attempt')} grade={r.get('grade')} "
              f"issues={r.get('issues')} warnings={r.get('warnings')}")
    print()
```

분석 항목:
- **도메인 분류 정확도** (question 내용 vs domain 값)
- **signoff 통과율** (approved vs escalated 비율)
- **grade 분포** (A/B/C)
- **retry_count** — 3회 실패 후 escalate 패턴
- **rejection_history** — 어떤 signoff 코드(C1–C5, A1–A5 등)에서 막히는지
- **latency** — 도메인별 응답 속도 이상치

---

## Step 3 — 에러 로그 병행 확인

```bash
az storage blob download \
  --account-name sohobi9638logs \
  --container-name sohobi-logs \
  --name errors.jsonl \
  --file /tmp/azure_errors_latest.jsonl \
  --auth-mode login \
  --overwrite
```

같은 기간(최근 25개 쿼리 기간)의 에러와 쿼리 실패를 교차 분석한다.

---

## Step 4 — 분석 결과 기반 후속 조치 도출

분석 후 아래 항목을 평가하여 우선순위 후속 조치 목록을 작성한다:

| 항목 | 확인 방법 |
|------|---------|
| 상권 에이전트 — 광역 구 단위 처리 부재 | E-1(마포구) 로그의 status/grade 확인 |
| 임베딩 모델 동작 여부 | location domain 에러 로그 패턴 |
| signoff 인젝션 패치 효과 | 최근 날짜 기준 rejection_history 변화 |
| finance 파라미터 부족 처리 (E-3) | grade C + 특정 rejection 코드 |
| 서울 외 지역 fallback (E-4, 부산) | location escalated + issues 내용 |

---

## Verification

1. `/tmp/azure_queries_latest.jsonl` 다운로드 성공 확인 (파일 크기 > 0)
2. Python 스크립트 출력에서 25개 항목 전체 표시 확인
3. 분석 결과를 `docs/session-reports/session-report-2026-03-26.md`의 "미해결 사항" 섹션과 교차 검토
