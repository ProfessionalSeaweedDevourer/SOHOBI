# Sign-off Agent 테스트 플랜

## Context

gpt-5.4-pro(추론 모델) → gpt-4.1-mini(classic 엔드포인트)로 전환함.
기존 254초 hang → 현재 9초대 signoff_ms 확인. 이 플랜은 속도 개선을 수치로 확인하고,
품질·재시도 동작에 문제가 없는지 체계적으로 검증하기 위한 것.

---

## 측정 지표

각 테스트에서 SSE 이벤트에서 다음 값을 기록:
- `agent_ms` — 도메인 에이전트 초안 생성 시간
- `signoff_ms` — 검증 LLM 호출 시간
- `grade` — A / B / C
- `approved` — true / false
- `retry_count` — 최종 complete 이벤트의 값
- `status` — `approved` / `escalated`

---

## 테스트 케이스

### 1. 도메인별 정상 경로 (Happy Path)

목표: 각 도메인에서 Grade A 또는 B 획득, signoff_ms ≤ 15,000ms

| # | 질문 | 예상 도메인 | 예상 Grade | 예상 status |
|---|------|------------|-----------|------------|
| T1 | "서울 마포구에서 카페를 열고 싶습니다" | location | B 이상 | approved |
| T2 | "강남구 헬스장 창업 시 예상 매출은?" | location | B 이상 | approved |
| T3 | "소규모 법인 설립 절차와 비용을 알려주세요" | legal | B 이상 | approved |
| T4 | "음식점 임대차 계약 시 주의사항은?" | legal | B 이상 | approved |
| T5 | "초기 투자금 5천만원으로 손익분기점 언제?" | finance | B 이상 | approved |
| T6 | "카페 운영 고정비·변동비 구조 분석" | finance | B 이상 | approved |
| T7 | "소상공인 지원금 신청 방법은?" | admin | B 이상 | approved |

**검증 방법:**
```bash
curl -s -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "<질문>"}'
```
`event: complete` 라인에서 `grade`, `status`, `signoff_ms` 추출.

---

### 2. 속도 벤치마크

목표: signoff_ms 기준값 확립 (이후 모델 변경 회귀 기준으로 사용)

T1 질문을 **3회 반복** 실행, signoff_ms 평균·최대값 기록.

예상 범위:
- gpt-5.4-pro (구): ~180,000–254,000ms
- gpt-4.1-mini (현): **목표 ≤ 15,000ms**

---

### 3. 재시도 트리거 케이스

목표: 의도적으로 부실한 응답을 유발해 signoff 거부 → 재시도 → 최종 승인 흐름 확인

| # | 질문 | 의도 | 예상 동작 |
|---|------|------|----------|
| T8 | "마포구 카페" (한 단어 수준의 짧은 질문) | location 에이전트가 데이터 부족으로 짧은 응답 | 1회 이상 거부 후 retry_prompt 포함 signoff_result, 재시도 후 escalated 또는 approved |
| T9 | "세금" (도메인 경계 불명확) | legal 또는 finance 라우팅, 초안 내용 불충분 가능성 | retry_count ≥ 1, grade B 이상으로 최종 승인 |

**확인 포인트:**
- `signoff_result` 이벤트에 `retry_prompt` 필드 존재
- 다음 `agent_start` attempt 번호가 +1 증가
- 최종 `complete`의 `rejection_history` 배열 길이 = retry_count

---

### 4. 에스컬레이션 케이스

목표: 3회 재시도 후 `status: escalated` 정상 반환 확인

현재 DB에 데이터 없는 지역으로 location 에이전트 강제 실패:
```bash
curl -s -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "제주도 서귀포시 카페 상권 분석"}'
```

예상 결과:
- `retry_count: 3`
- `status: escalated`
- `rejection_history` 배열 길이 1 (attempt 1만 기록, attempt 2~4는 agent_ms=0)
- `draft`에 "데이터를 찾을 수 없습니다" 계열 문자열

---

### 5. signoff 단독 엔드포인트 테스트

`/api/v1/signoff` 직접 호출 (orchestrator 우회):

```bash
curl -s -X POST http://localhost:8000/api/v1/signoff \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "location",
    "draft": "마포구 카페는 월평균 매출 3,200만원(2024 Q4 기준)이며 점포 수는 142개입니다. 기회 요인: 홍대 유동인구 집중. 리스크: 높은 임대료. 본 정보는 참고용입니다.",
    "question": "서울 마포구에서 카페를 열고 싶습니다"
  }'
```

예상: `approved: true`, `grade: "A"` 또는 `"B"`, signoff_ms 기록.

---

## 예상 문제 및 대응

| 예상 문제 | 가능성 | 확인 방법 | 대응 |
|----------|--------|----------|------|
| location DB 데이터 없음 → 모든 location 질문 escalated | 높음 (현재 확인됨) | T1 escalated 시 DB 쿼리 로그 확인 | 상권 에이전트 DB 연동은 별도 브랜치 작업으로 보류 |
| signoff_ms > 15,000ms | 낮음 | 벤치마크 결과 | api-version 또는 모델 파라미터 조정 |
| grade C → escalated 반복 (재시도 무의미) | 중간 | rejection_history 내 retry_prompt 내용 확인 | retry_prompt 품질 점검 (signoff 프롬프트 수정) |
| coverage 루프로 signoff 내부 재시도 발생 | 낮음 | signoff_ms가 비정상적으로 길어질 때 | signoff_agent.py max_retries 파라미터 확인 |

---

## 검증 완료 기준

- [ ] T1–T7 중 DB 데이터 있는 도메인(legal, finance, admin)에서 ≥ 1건 `status: approved`, `grade: B` 이상
- [ ] signoff_ms 평균 ≤ 15,000ms (3회 평균)
- [ ] 에스컬레이션 케이스에서 `retry_count: 3`, `status: escalated` 정상 반환
- [ ] `/api/v1/signoff` 단독 호출에서 양질의 draft → `approved: true`

---

## 비고

- location 에이전트 DB 미연동 상태이므로 location 도메인은 속도/에스컬레이션 확인에만 사용
- PR #42는 위 검증 완료 후 업데이트하여 머지
