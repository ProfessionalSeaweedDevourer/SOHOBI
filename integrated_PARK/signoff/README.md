# integrated_PARK/signoff

하위 에이전트가 생성한 응답(draft)의 품질을 자동 판정하는 **Sign-off 검증 에이전트**.

---

## 핵심 동작

```
에이전트 draft → Sign-off Agent → grade 판정 → 통과 or 재시도
```

1. 도메인별 루브릭 프롬프트(`prompts/signoff_<domain>/evaluate/skprompt.txt`)를 로드
2. LLM에 draft + 루브릭을 전달하여 각 코드(C1~C5, 도메인별 코드, SEC1~3, RJ1~3) 평가
3. 결과에서 grade를 도출

## Grade 체계

| Grade | 조건 | 동작 |
|-------|------|------|
| **A** | issues·warnings 모두 없음 | 즉시 통과 |
| **B** | issues 없음, warnings 1개+ | 경고 포함 통과 |
| **C** | issues 1개+ (blocking) | `retry_prompt` 생성 → 에이전트 재호출 (최대 3회) |

## 도메인별 필수 코드

| 도메인 | 공통 코드 | 도메인 코드 | 보안·거부 |
|--------|-----------|-------------|-----------|
| admin | C1~C5 | A1~A5 | SEC1~3, RJ1~3 |
| finance | C1~C5 | F1~F5 | SEC1~3, RJ1~3 |
| legal | C1~C5 | G1~G4 | SEC1~3, RJ1~3 |
| location | C1~C5 | S1~S5 | SEC1~3, RJ1~3 |

> `chat` 도메인은 Sign-off를 바이패스한다 (즉시 반환).

## 파일

| 파일 | 설명 |
|------|------|
| `signoff_agent.py` | Sign-off 에이전트 본체 — `run_signoff()` 함수 |

## 보안

- draft 내 `<<<DRAFT_START>>>` / `<<<DRAFT_END>>>` 구분자를 이스케이프하여 프롬프트 인젝션 방지

## 관련 문서

- 루브릭 상세: [`../prompts/README.md`](../prompts/README.md)
- 아키텍처 다이어그램: [`../../docs/architecture/`](../../docs/architecture/)
