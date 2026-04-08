# Oracle DB 연결 문제 해결 플랜

## Context

팀원 작업 환경은 유선 LAN, 개발 컴퓨터는 무선 Wi-Fi이므로 `<ORACLE_HOST>:1521`에 직접 도달 불가. 추가로 `finance_db.py`에 코드 버그도 있어 연결 가능 환경에서도 오작동. 두 가지를 동시에 수정한다.

---

## 문제 1: 네트워크 미도달 — SSH 터널로 해결

### 전제 조건
- 팀원 PC IP와 SSH 사용자명 확보됨 (점프 호스트)

### 해결 방법: SSH 로컬 포트 포워딩

```bash
# 터미널 1 — 터널 유지 (개발 세션 동안 켜두기)
ssh -N -L 1521:<ORACLE_HOST>:1521 <팀원_USER>@<팀원_PC_IP>
```

터널이 열리면 본인 맥북의 `localhost:1521` → 팀원 PC 경유 → `<ORACLE_HOST>:1521` 로 연결됨.

터널이 열리면 `localhost:1521` → `<ORACLE_HOST>:1521` 로 투명하게 연결됨.

### .env 수정 (터널 사용 시)

```env
ORACLE_HOST=localhost   # 터널 포워딩 주소
ORACLE_PORT=1521
```

터널 없이 LAN에 직접 접속할 때는 다시 `<ORACLE_HOST>`로 복원.

---

## 문제 2: finance_db.py 코드 버그 수정

### 현황 (버그)

| 파일 | 문제 |
|------|------|
| `db/finance_db.py:9` | `DB_DSN` 환경변수 사용 — `.env`에 없음 |
| `db/finance_db.py:10` | `connect(dsn)` — user/password 누락, oracledb API 오류 |

### 수정 내용

**`integrated_PARK/db/finance_db.py`** — `_get_connection()` 수정

```python
def _get_connection(self):
    return connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        host=os.getenv("ORACLE_HOST"),
        port=int(os.getenv("ORACLE_PORT", "1521")),
        sid=os.getenv("ORACLE_SID"),
    )
```

> `repository.py`에서 이미 사용 중인 `ORACLE_*` 변수 패턴과 통일. `.env`에 이미 값 존재.

---

## 영향 받는 파일

| 파일 | 수정 여부 | 내용 |
|------|-----------|------|
| `integrated_PARK/db/finance_db.py` | **수정** | `_get_connection()` 코드 수정 |
| `integrated_PARK/.env` | **수정** | SSH 터널 사용 시 `ORACLE_HOST=localhost`로 전환 |
| `integrated_PARK/db/repository.py` | 수정 없음 | 이미 올바른 패턴 사용 중 |
| `integrated_PARK/plugins/finance_simulation_plugin.py` | 수정 없음 | DB 연결 자체는 finance_db에 위임 |
| `integrated_PARK/agents/location_agent.py` | 수정 없음 | repository.py 사용, 직접 DB 연결 없음 |

---

## 검증 방법

### Step 1: SSH 터널 확인
```bash
nc -z -w 3 localhost 1521 && echo "터널 OK"
```

### Step 2: finance_db.py 연결 테스트
```bash
cd integrated_PARK
.venv/bin/python3 -c "
from db.finance_db import DBWork
db = DBWork()
print('평균 매출:', db.get_average_sales())
print('지역 매출:', db.get_sales(None, None))
"
```

### Step 3: repository.py 연결 테스트
```bash
.venv/bin/python3 -c "
from db.repository import CommercialRepository
repo = CommercialRepository()
print(repo.get_sales('서울특별시 강남구', None, None))
"
```

---

## 주의 사항

- SSH 터널은 개발 세션마다 다시 열어야 함 (영구 연결이 아님)
- 터널 없이 배포 환경(Azure Container Apps)에서 실행될 때는 `ORACLE_HOST=<ORACLE_HOST>` 유지
- `.env`는 절대 커밋 금지
