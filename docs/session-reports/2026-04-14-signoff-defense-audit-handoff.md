# 세션 인수인계 — signoff 프롬프트 방어 코드 감사 (read-only)

## 개요

이전 HIGH 이월 항목인 "F1~F5 로컬 회귀 스위트" 는 프로덕션 모델(gpt-5.4)이 극단값을 자체 생성하지 않는 상황에서 의도적으로 취약한 모델(gpt-4.1-mini)로 내려 방어 프롬프트의 실효성을 증명하려는 구조다. 사용자는 이 전제 자체를 문제 삼았다 — "프롬프트 방어의 존재 가치 자체를 검토해야지, 프로덕션 밖의 환경으로 테스트 케이스를 만드는 건 비합리적."

이에 따라 본 세션은 **backend/signoff/ 가 프로덕션 모델 위에서 실제로 의미 있는 방어를 하는가** 를 Azure 로그 200건(queries) / 147건(rejection 경험) 기준으로 읽기 전용 감사했다. **코드 변경 없음**.

결론 요지:

1. **F1~F5 (finance 극단값) 는 load-bearing** — 프로덕션 gpt-5.4 에서도 finance 18건 중 8~10건에서 실제 발동 중. "프로덕션 모델이 극단값을 안 낸다" 는 가정은 **오류**
2. **severity 필드는 로깅 단계에서 손실됨** — signoff_agent 는 LLM 이 severity 를 빠뜨릴 때 `default="high"` 로 간주해 grade 계산하지만, `logger.py:176,200` 은 `issue.get("severity")` 로 원본 None 을 그대로 저장. **감사·모니터링 목적으로 로그가 신뢰 불가**
3. **재시도 회복률은 23%** — rejection 경험 147건 중 최종 승인 34건, 최종 escalated 113건 (77%). 재시도 루프가 단순 통과/실패 이분법을 대체하는 가치를 부분 제공
4. **SEC1/SEC3 결정론적 방어 실제 발동** — admin 도메인 2건씩. 순수 추가 방어층으로 load-bearing

## 브랜치 & PR

- 브랜치: `main` (clean, 코드 변경 없음)
- PR: 없음 (감사 단독 세션)
- 직전 handoff: `2026-04-13-location-agent-test-repair-handoff.md` (PR #300 MERGED)

## 수집 근거

### 1. 데이터 소스

```bash
source backend/.env
curl -s -H "X-API-Key: $API_SECRET_KEY" \
  "$BACKEND_HOST/api/v1/logs?type=rejections&limit=200" → 147건
curl -s -H "X-API-Key: $API_SECRET_KEY" \
  "$BACKEND_HOST/api/v1/logs?type=queries&limit=200"    → 200건
```

### 2. 도메인별 rejection 발생률 (queries 기준)

| 도메인 | 총 쿼리 | rejection 경험 | 비율 |
|--------|---------|---------------|------|
| chat | 32 | 1 | 3% |
| legal | 18 | 5 | 28% |
| finance | 44 | 18 | 41% |
| location | 84 | 80 | 95% |
| admin | 22 | 43 | 195% (스트림/재기록 중복 추정) |

### 3. 도메인 × code 발동 (attempt 중복 제거, 고유 쿼리당)

| 도메인 | 발동 code | 비고 |
|--------|-----------|------|
| chat | CH1·CH3 각 1 | 샘플 수 불충분 |
| legal | G1·G2·G3 각 2, G4 4, C 계열 산발 | G4(법령 미인용) 실제 발동 |
| finance | **F1·F2·F3 각 8, F4 9, F5 10**, C1~C5 각 8~9 | **극단값 방어 load-bearing** |
| location | S1·S2 각 29, S3·S5 각 28, S4 26, C1~C5 13~15 | 상권 규칙이 거의 모든 쿼리에서 발동 |
| admin | A1 15, A2 14, A3~A5 12~13, **SEC1 2, SEC3 2** | 보안 규칙 + 행정 규칙 |

### 4. 재시도 회복률

| 최종 status | 건수 |
|-------------|------|
| approved (rejection → 재시도 후 승인) | 34 (23%) |
| escalated (max_retries 초과) | 113 (77%) |
| (retry_count=1 approved) | 23 |
| (retry_count=2 approved) | 8 |
| (retry_count=3 approved) | 3 |

### 5. severity 필드 저장 현황

| severity 저장 | 건수 (총 828 issues) |
|---------------|---------------------|
| present=medium | 3 |
| present=high | 1 |
| absent (None) | 824 |

signoff_agent.py:126 `issue.get("severity", "high")` — grade 계산에는 반영. logger.py:176,200 `issue.get("severity")` — **None 그대로 저장 → 로그 기반 감사 불가능**.

## 판정 매트릭스

| 카테고리 | 프롬프트 위치 | 테스트 pin | 실로그 발동 | 판정 |
|----------|---------------|------------|-------------|------|
| SEC1 템플릿 누출 | signoff_agent.py:44-51 (정규식) | test_signoff_sec1_leak | 2건 | **load-bearing (결정론적)** |
| SEC3 | signoff_*/skprompt.txt | - | 2건 | **load-bearing** |
| F1 연수익률/단위혼용 | signoff_finance:103 | - | 8건 | **load-bearing** |
| F2 단위 2배 괴리 | signoff_finance:104 | - | 8건 | **load-bearing** |
| F3 가정 범위 누락 | signoff_finance:105 | - | 8건 | **load-bearing** |
| F4 손실확률 극단 | signoff_finance:106 | - | 9건 | **load-bearing** |
| F5 원금보장 과장 | signoff_finance:107 | - | 10건 | **load-bearing** |
| C1~C5 공통 | signoff_*/skprompt.txt | - | 전 도메인 | **load-bearing** |
| S1~S5 상권 | signoff_location:47-67 | - | 26~29건/80 | **load-bearing (과도 발동 의심)** |
| A1~A5 행정 | signoff_admin:53-61 | - | 12~15건/22 | **load-bearing (과도 발동 의심)** |
| G1~G4 법령 | signoff_legal | test_signoff_legal | 각 2~4건/18 | **load-bearing** |
| CH1~CH5 chat | signoff_chat | - | 1건 | **insufficient-data** |

**redundant 판정 카테고리 없음**. 모든 주요 카테고리가 실로그에서 발동 증거 보유.

## 결론 & 후속 제안

1. **"프로덕션 모델이 방어를 대체한다"는 가설은 반증됨** — F1~F5 finance 극단값이 실제 gpt-5.4 응답에서도 생성됨. 방어 프롬프트 제거 불가
2. **F1~F5 로컬 회귀 스위트(HIGH 이월 5세션) closure 가능** — 프로덕션 로그가 이미 실효성을 입증. gpt-4.1-mini 재현 스위트를 별도 구축할 정당성 소멸. HIGH 에서 **제거** 권고
3. **severity 로깅 버그 수정 필요 (MED, 신규)** — logger.py:176,200 이 `issue.get("severity", "high")` 로 변경되어야 grade 집계·모니터링이 가능. signoff_agent 의 default 와 통일
4. **location 과도 발동 조사 (LOW, 신규)** — 80건 중 S1~S5 가 26~29건 발동. 프롬프트 기준이 너무 엄격하거나 location 에이전트 draft 품질 문제. 본 감사 범위 밖
5. **admin rejection 195% 중복 현상 (LOW)** — rejection 로그가 queries 보다 많음. 스트림 경로 이중 기록 잔존 가능성. PR #296 회귀 모니터링

## 미해결 · 관측

- HIGH F1~F5 로컬 회귀 스위트 — **본 감사로 closure 권고** (프로덕션 로그가 실효성 입증)
- MED (신규) severity 로깅 누락 — logger.py 수정 PR 1건 (~5줄)
- LOW (신규) location 도메인 S1~S5 과도 발동 조사
- LOW ChatAgent content_filter 재시도 Azure 로그 관측 이월
- LOW 자연 트래픽 medium/low severity 배지 실측 (severity 로깅 수정 후에야 의미)
- LOW escalated/is_partial `final_verdict=null` 실측
- LOW "모든 검증 통과" 단문 UX 관찰
- LOW T-CA-INJ-03 prior_history 누적 인젝션 테스트

## 다음 세션 인수 요약

1. severity 로깅 누락 수정 PR (logger.py:176,200)
2. F1~F5 HIGH 항목 handoff 에서 closure 처리
3. location 도메인 S1~S5 과도 발동 조사 (프롬프트 완화 vs 에이전트 draft 품질)
4. admin rejection 중복 기록 원인 확인
5. ChatAgent content_filter Azure 로그 관측

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: none
prev: 2026-04-13-location-agent-test-repair-handoff.md

[unresolved]
- MED backend/logger.py:176,200 severity 필드 None 저장 — signoff_agent default="high" 와 불일치. grade 집계·모니터링 불가. issue.get("severity","high") 로 수정 필요
- LOW location 도메인 S1~S5 80쿼리 중 26~29건 발동 — 프롬프트 기준 과엄격 or draft 품질 조사
- LOW admin rejection 43건 > queries 22건 — 스트림 경로 중복 기록 잔존 가능 (PR #296 이후 회귀 확인)
- LOW ChatAgent content_filter 재시도 Azure 로그 관측 이월
- LOW 자연 트래픽 medium/low severity 배지 실측 — severity 로깅 수정 후에야 의미
- LOW escalated/is_partial final_verdict=null 프로덕션 실측
- LOW "모든 검증 통과" 단문 UX 관찰
- LOW T-CA-INJ-03 prior_history 누적 인젝션 테스트

[decisions]
- HIGH "F1~F5 로컬 회귀 스위트" 는 closure 권고. Azure 로그 147 rejection 샘플에서 finance 18건 중 F1 8 / F2 8 / F3 8 / F4 9 / F5 10건 실발동 확인. 프로덕션 gpt-5.4 가 극단값을 자체 생성하지 않는다는 가정은 오류. 방어 프롬프트는 load-bearing
- 모든 주요 카테고리(F1~F5, S1~S5, A1~A5, G1~G4, C1~C5, SEC1/SEC3) 가 실로그에서 발동 증거 보유. redundant 판정 카테고리 없음
- 재시도 회복률 34/147 = 23% (retry1:23, retry2:8, retry3:3). 단순 통과/실패 이분법 대체 가치 부분 제공

[next]
1. severity 로깅 누락 수정 PR — logger.py:176,200 2줄 수정 (fix/park-logger-severity-default)
2. F1~F5 HIGH closure — handoff 체인에서 제거
3. location S1~S5 과도 발동 조사 (프롬프트 완화 vs draft 품질)
4. admin rejection 중복 기록 원인 확인
5. ChatAgent content_filter Azure 로그 관측

[traps]
- signoff_agent.py:126 은 `issue.get("severity", "high")` 로 default high 부여해 grade 계산. logger.py 는 default 없이 None 저장 → 같은 default 를 양쪽에 복제해야 함. grade 재계산이 아닌 원본 severity 필드 저장 책임을 logger 에 둘지, signoff_agent 가 issue dict 를 정규화한 후 반환할지 설계 판단 필요
- `/api/v1/logs?type=rejections` 는 X-API-Key 헤더 필수 (401). `$API_SECRET_KEY` 사용
- rejection_history[].issues[] 에는 I_NEED_DRAFT_* 라는 이상 prefix 코드가 섞여있음 (finance 1건, draft 미제공시 평가 불가 신호). 집계 시 필터 필요
- admin rejection 43 > queries 22 는 /logs endpoint 가 stream 경로/일반 경로를 중복 기록하거나 limit 200 범위 시점 불일치일 가능성. 정밀 조사 필요
- F1~F5 finance code 는 ~8~10건으로 비슷하지만 finance 쿼리 18건 중 대부분이 동일 기본값 시뮬레이션 ("기본값으로 재무 시뮬레이션") 반복 — F 규칙 모두가 동일 쿼리에서 같이 발동하는 패턴. 실제 독립 발동 여부는 쿼리 다양성 확보 후 재감사 필요
CLAUDE_HANDOFF_END -->
