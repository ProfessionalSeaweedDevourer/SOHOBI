# 세션 리포트 — 2026-04-01

## 작업 목표

Oracle DB 연결 정보(`10.1.92.119:1521/xe`, 사용자 `shobi`)를 이용해
`integrated_PARK/db/finance_db.py` 및 관련 에이전트/플러그인의 DB 연동이 정상 작동하는지 검증 및 수정.

---

## 진단 결과 — 두 가지 문제 발견

### 문제 1: finance_db.py 코드 버그

`_get_connection()`이 존재하지 않는 환경변수 `DB_DSN`을 참조하고,
`oracledb.connect(dsn)` 호출 시 user/password를 누락하는 API 오류.

| 항목 | 내용 |
|------|------|
| 파일 | `integrated_PARK/db/finance_db.py` |
| 증상 | DB 접근 시 항상 예외 → fallback 값 `[17000000]` 반환 |
| 원인 | `DB_DSN` 환경변수 미정의 + `connect()` 인자 누락 |

**수정 내용** (`_get_connection()` 메서드):

```python
# 수정 전
def _get_connection(self):
    dsn = os.getenv("DB_DSN")
    return connect(dsn)

# 수정 후 — repository.py의 ORACLE_* 패턴과 통일
def _get_connection(self):
    return connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        host=os.getenv("ORACLE_HOST"),
        port=int(os.getenv("ORACLE_PORT", "1521")),
        sid=os.getenv("ORACLE_SID"),
    )
```

`.env`의 `ORACLE_*` 변수는 이미 올바르게 설정되어 있었음 — 코드만 수정.

---

### 문제 2: 네트워크 미도달 (Wi-Fi ↔ 유선 LAN 격리)

| 항목 | 내용 |
|------|------|
| 증상 | `10.1.92.119:1521` timeout — `nc`, `ping` 모두 실패 |
| 원인 | 개발 PC(Mac)는 무선, DB 서버는 유선 LAN 전용 망 |
| 추가 원인 | 해당 공유기가 무선 접속 불가 상태 |

---

## 네트워크 문제 해결 과정

### 시도 1: 팀원 PC에 직접 SSH 터널 (실패)

팀원 PC(`10.1.92.110`)에 OpenSSH Server를 활성화하고 포트 포워딩 시도.
Mac에서 `ping 10.1.92.110` → **100% packet loss** (서로 다른 망, 라우팅 불가).

### 시도 2: Tailscale VPN 설치 — Homebrew 버전 (실패)

```bash
brew install tailscale
sudo tailscale up
# → failed to connect to local Tailscale service
```

`brew services list`에서 `error` 상태 확인.
Homebrew 버전은 macOS 시스템 권한 처리 불완전.

### 시도 3: Tailscale App Store 버전 (성공)

Homebrew 버전 제거 후 **Mac App Store**에서 Tailscale 재설치.
팀원 PC(Windows 10)와 Mac 양쪽에서 같은 계정으로 로그인.

```bash
ping -c 3 100.107.219.31   # 팀원 PC Tailscale IP
# → 응답 성공 (평균 383ms)
```

### 시도 4: SSH 빈 암호 문제 (추가 장애)

팀원 PC `soldesk` 계정에 암호가 없어 SSH 접속 시 `Permission denied`.
Windows OpenSSH 기본 설정은 빈 암호 허용 안 함.

```powershell
# 팀원 PC에서 임시 암호 설정
net user soldesk 1234
```

### 최종 구성 — SSH 로컬 포트 포워딩

```bash
# Mac 터미널 (세션 동안 유지)
ssh -N -L 1521:10.1.92.119:1521 soldesk@100.107.219.31
```

```
Mac(Wi-Fi) → Tailscale → 팀원 PC(10.1.92.110) → 유선 LAN → Oracle DB(10.1.92.119:1521)
```

`.env` 수정:
```
ORACLE_HOST=localhost   # 터널 포워딩
```

---

## DB 연결 검증 결과

```
평균 매출: [1413253753.4998727]   # finance_db.py ✅
repository 연결: 성공              # repository.py ✅
```

---

## 영향 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `integrated_PARK/db/finance_db.py` | `_get_connection()` 수정 — `ORACLE_*` 환경변수 패턴 적용 |
| `integrated_PARK/.env` | `ORACLE_HOST=localhost` (SSH 터널용) |

변경 없는 파일: `db/repository.py`, `agents/location_agent.py`, `plugins/finance_simulation_plugin.py`

---

## 개발 세션 시작 루틴 (이후 매 세션)

```bash
# 1. SSH 터널 열기 (터미널 하나 전용으로 유지)
ssh -N -L 1521:10.1.92.119:1521 soldesk@100.107.219.31
# 비밀번호: 1234

# 2. 터널 확인
nc -z -w 3 localhost 1521 && echo "터널 OK"

# 3. 백엔드 실행
cd integrated_PARK && .venv/bin/python3 api_server.py
```

**전제 조건**: 팀원 PC 전원 ON + Tailscale 실행 중

---

## 주의 사항

- SSH 터널은 세션마다 수동으로 열어야 함 (영구 연결 아님)
- 배포 환경(Azure Container Apps)은 `ORACLE_HOST=10.1.92.119` 직접 사용 — `.env` 커밋 금지
- 팀원 PC 임시 암호(`1234`)는 보안상 추후 SSH 키 인증으로 교체 권장
