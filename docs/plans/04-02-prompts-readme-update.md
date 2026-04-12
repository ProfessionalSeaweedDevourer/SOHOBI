# 플랜: integrated_PARK/prompts/README.md 최신화

> 작성일: 2026-04-02
> 담당: PARK
> 대상 파일: `integrated_PARK/prompts/README.md`

## Context

보안 테스트 이후 모든 `skprompt.txt`에 L3 보안 루브릭(SEC1~SEC3), L4 거부 응답 루브릭(RJ1~RJ3), `[사전 판정]` 블록, 출력 JSON 스키마 변경(`grade`, `warnings`, `confidence_note` 추가), `{{$draft}}` 구분자 강화(`<<<DRAFT_START>>>` / `<<<DRAFT_END>>>`)가 대거 추가되었다. 기존 README.md는 이 내용을 전혀 반영하지 않아, 팀원이 루브릭을 수정할 때 참고 문서와 실제 파일이 불일치한 상태였다.

---

## 변경 범위 요약 (skprompt.txt 실측 근거)

| 항목 | 기존 README | 현재 skprompt.txt |
|------|------------|-------------------|
| 루브릭 레이어 수 | L1 공통 + L2 도메인 (2개) | L1~L4 (4개) |
| 평가 코드 수 | 10~9개 | 15~16개 |
| JSON 출력 필드 | approved, passed, issues, retry_prompt | + grade, warnings, confidence_note |
| 사전 판정 블록 | 없음 | 있음 (최우선 적용) |
| draft 구분자 | `{{$draft}}` | `<<<DRAFT_START>>>`, `<<<DRAFT_END>>>` 명시 |
| REQUIRED_CODES 예시 | SEC/RJ 미포함 | SEC1~SEC3, RJ1~RJ3 포함 필요 |

---

## 수정 내용 요약

### 섹션 1 — 폴더 구조
- 각 `skprompt.txt` 주석에 "L1~L4 루브릭 포함" 명시
- 담당자 테이블에 PARK의 L3·L4 관리 명시, CHOI의 location 담당 추가

### 섹션 2 — 루브릭이란 무엇인가
- 4개 레이어(L1 공통·L2 도메인·L3 보안·L4 거부) 테이블 추가
- L3·L4가 보안 테스트 이후 추가된 레이어임을 명시

### 섹션 3 — 루브릭 파일 읽는 법
- skprompt 구조 예시에 `[사전 판정]` 블록 및 L3·L4 섹션 추가
- JSON 출력 형식: `grade`, `warnings`, `confidence_note` 추가
- 등급 기준(A/B/C) 테이블 추가
- draft 구분자 강화 배경 설명 추가

### 섹션 4 — 항목별 평가 기준
- 상권분석 도메인(S1~S5) 테이블 추가 (기존 누락)
- **L3 보안 루브릭 소섹션** 신규: SEC1~SEC3 상세 기준 및 SEC1 판단 예시
- **L4 거부 응답 루브릭 소섹션** 신규: RJ1~RJ3 상세 기준 및 RJ3 주의 사항
- **[사전 판정] 블록이란** 소항목 신규: 적용 기준 및 거부 판정 시 처리 흐름

### 섹션 5 — 루브릭 수정 방법
- `REQUIRED_CODES` 예시에 SEC1~SEC3, RJ1~RJ3 추가 (전 도메인)
- location 도메인 행 추가

### 섹션 6 — 실제 개선 사례
- **사례 7** 추가: SEC1 오판 패턴 및 판단 핵심 기준 명확화
- **사례 8** 추가: RJ3 도입 배경 — 거부 응답에 도메인 루브릭 오적용 문제

### 섹션 7 — 테스트 실행 방법
- 방법 B 응답 예시: `grade`, `warnings`, `confidence_note`, SEC/RJ passed 항목 반영

### 섹션 8 — 자주 하는 실수
- **실수 6** 추가: SEC1 오판 — 창업 정보 설명을 시스템 지시 노출로 오해
- **실수 7** 추가: 거부 응답에 도메인 루브릭 탈락 기준 잘못 적용

### 말미 요약 테이블
- 컬럼 추가: 보안 L3 / 거부 L4
- 합계 수정: 16/16/15/16
- location 행 추가
