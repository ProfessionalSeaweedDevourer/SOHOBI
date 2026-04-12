# Signoff severity 스키마 + `_derive_grade` 가중치 반영

## 배경

[signoff_agent.py:113-123](../../integrated_PARK/signoff/signoff_agent.py#L113-L123) `_derive_grade`는 `issues` 1개만 있어도 무조건 **C**로 떨어진다. 핸드오프 MED "F1~F5 루브릭 극단 수치 둔감"과 같은 축으로, issue의 경중이 등급에 반영되지 않는 문제.

## 변경

- `integrated_PARK/signoff/signoff_agent.py`
  - issue 스키마에 optional `severity: "high"|"medium"|"low"` 필드 추가 (기본 "high" — 후방호환)
  - `_derive_grade`: high/medium issue → C, low-only → B, warnings만 → B, 없음 → A
  - SEC1/RJ1은 강제 high (안전장치)
  - `validate_verdict`의 grade 일관성 assertion을 신규 규칙에 맞게 갱신
- `integrated_PARK/tests/test_signoff_severity.py` (신규)
  - severity별 grade 결정 케이스
  - SEC1 override 유지 케이스
  - 기본값(severity 미지정) 후방호환 케이스

## 검증

- `.venv/bin/python3 -m pytest integrated_PARK/tests/test_signoff_severity.py -v`
- 기존 `test_signoff_sec1_leak.py` 회귀 확인

## 세션 외

- 4개 도메인 `prompts/signoff_*/evaluate/skprompt.txt`에 severity 출력 지시 추가 → 세션 A-2
- F1~F5 루브릭 극단값 처리 → 프롬프트 개편에 귀속
- domain_router 오분류 6건 픽스쳐 편입 → 정리 세션
