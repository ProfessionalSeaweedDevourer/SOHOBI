# 효과음 훅 진단 플랜

## Context

사용자는 두 가지 효과음을 설정했다:
- **작업 완료** (`Stop` 훅) → `Glass.aiff` ✅ 정상 작동
- **사용자 확인 요청** (`Notification` 훅) → `Ping.aiff` ❌ 작동 안 함

`Ping.aiff` 파일은 `/System/Library/Sounds/Ping.aiff`에 **실제로 존재**하므로 파일 부재가 원인이 아니다.

## 진짜 원인: Notification 훅의 발화 조건 불일치

`Notification` 훅은 Claude Code가 **OS 레벨 데스크탑 알림(macOS 알림 센터)** 을 보낼 때만 발화한다.

- 이는 주로 앱이 **백그라운드**에 있을 때, Claude가 입력을 기다리는 상황에서 발생
- **IDE/터미널에서 직접 보이는 도구 권한 승인 프롬프트**(tool permission prompt)는 Notification이 아닌 인라인 UI 요소이므로 이 훅을 발화시키지 않음
- 따라서 사용자가 화면을 보고 있는 동안은 `Notification` 훅이 거의 발화하지 않음

## 해결 방안

### 방안 A (권장): Notification 훅 유지 + 기대치 조정

`Notification` 훅은 사실상 "자리 비운 사이 Claude가 멈춤" 알림이다.
현재 설정 자체는 올바르며, **Claude Code 창이 포커스를 잃은 상태**에서만 `Ping.aiff`가 울린다.

추가 조치 없음. 동작 방식을 이해하면 충분.

### 방안 B: PreToolUse 훅으로 도구 실행 전 효과음

도구 실행마다(승인 여부 무관) 소리를 내고 싶다면:

```json
"PreToolUse": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "/usr/bin/afplay /System/Library/Sounds/Ping.aiff"
      }
    ]
  }
]
```

단점: 승인된 도구 포함 **모든 도구 호출**마다 울림 → 빈도가 높아 오히려 방해가 될 수 있음.

### 방안 C: UserPromptSubmit 훅으로 사용자 입력 시 효과음

사용자가 프롬프트를 제출할 때 소리:

```json
"UserPromptSubmit": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "/usr/bin/afplay /System/Library/Sounds/Ping.aiff"
      }
    ]
  }
]
```

## 수정 대상 파일

- `/Users/eric.j.park/Documents/GitHub/SOHOBI/.claude/settings.json`

## 검증

방안 B 또는 C 적용 후:
1. Claude Code에서 작업 요청
2. 도구 실행 직전 / 프롬프트 제출 시 `Ping.aiff` 소리 확인
