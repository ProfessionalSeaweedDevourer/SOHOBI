# Plan: variable_extractor.py sign_off 서비스 ID 버그 수정

## Context

**발생 경위:**
- `a14895c` (2026-03-16): `variable_extractor.py` 신규 생성. 당시 `kernel_setup.py`는 서비스 ID `"sign_off"` 하나만 등록했고, `variable_extractor.py`는 이를 참조.
- `a6a6896` (2026-04-02, 어제): 리팩토링 커밋 "에이전트별 독립 모델 서비스 ID 분리" — `"sign_off"` 단일 서비스를 `admin/finance/legal/location/chat/router` 6개로 교체. **`variable_extractor.py`는 이 커밋에서 누락됨.**
- 결과: `extract_financial_vars()` 호출 시마다 `KernelServiceNotFoundError: Service with service_id 'sign_off'...` 예외 발생. `except`로 잡히므로 크래시는 없지만 세션 변수 추출 기능이 어제부터 **완전히 무력화**된 상태.

**영향:** 재무 에이전트에서 이전 대화의 재무 변수(월매출·원가 등)를 세션에 누적하는 "Path B" 기능이 동작하지 않음. 매번 새 질문에서 변수를 처음부터 추출해야 함.

## 수정 대상

| 파일 | 변경 내용 |
|------|----------|
| `integrated_PARK/variable_extractor.py:57` | `"sign_off"` → `"finance"` |
| `integrated_PARK/agents/chat_agent.py:4` | 주석 `기존 "sign_off" ... 서비스 재사용` → `"chat"` 으로 수정 (stale 주석) |

## 수정 내용

### 1. variable_extractor.py (핵심 버그)

```python
# 변경 전 (line 57)
service: AzureChatCompletion = kernel.get_service("sign_off")

# 변경 후
service: AzureChatCompletion = kernel.get_service("finance")
```

`"finance"` 선택 근거: 재무 변수 추출 목적에 가장 적합하고, `finance_agent.py`와 동일한 엔드포인트·모델을 공유.

### 2. chat_agent.py (stale 주석)

```python
# 변경 전 (line 4)
- 플러그인 없음, 기존 "sign_off" AzureChatCompletion 서비스 재사용

# 변경 후
- 플러그인 없음, "chat" AzureChatCompletion 서비스 사용
```

## 검증 방법

배포 후 재무 질문 2회 연속 전송:
1. 1차: "홍대 카페, 월매출 2000만, 임대료 200만으로 수익 분석해줘"
2. 2차: "원가도 600만으로 추가하면 어떻게 돼?"

2차 질문에서 1차의 월매출·임대료가 세션에 유지되어 시뮬레이션에 반영되면 정상.

로그에서 `"재무 변수 추출 실패 (무시)"` 경고가 사라지면 확인 완료.
