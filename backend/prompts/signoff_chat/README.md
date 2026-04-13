# signoff_chat 루브릭 동기화 절차

chat 도메인 signoff 루브릭(CH1~CH5)은 [ChatAgent.SYSTEM_PROMPT](../../agents/chat_agent.py)와 동기화되어야 한다. SYSTEM_PROMPT는 사실상 SOHOBI 서비스 기능 명세(README 성격)이며, 루브릭이 이와 어긋나면 "잘못된 안내" 검증이 실효를 잃는다.

## 동기화가 필요한 시점

- 에이전트 추가/제거
- 에이전트 역할·입력값 명세 변경
- 서비스 범위(지원 지역·분기) 변경
- [응답 원칙] 섹션 수정

## 체크리스트 (SYSTEM_PROMPT 변경 시)

1. `backend/agents/chat_agent.py` SYSTEM_PROMPT diff 확인
2. `evaluate/skprompt.txt`의 **CH1 안내 정확성** 섹션에서 기능·입력값 목록 갱신
3. **CH3 서비스 범위 경계**의 지역·분기 정보 갱신
4. **CH2 전문 에이전트 리디렉션**에서 변경된 도메인명 반영
5. `backend/tests/test_signoff_chat.py` 샘플 draft 업데이트
6. 로컬 pytest + curl 회귀 (TC-14/15 기준)

## 운영 권장

- 주간 1회 SYSTEM_PROMPT ↔ skprompt.txt diff 점검
- SYSTEM_PROMPT 수정 PR에는 skprompt.txt 동시 수정 강제 (리뷰어 체크)
