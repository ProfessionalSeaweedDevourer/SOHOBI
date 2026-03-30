# Azure 백엔드 ↔ 로컬 DB 서버 연결 검토

## Context
Azure Container Apps에 배포된 백엔드(integrated_PARK)가 로컬 서버(10.1.92.119)의 Oracle DB에 연결해야 함.
현재 `.env`에 `ORACLE_HOST=10.1.92.119` (내부 사설 IP)로 설정되어 있어 Azure에서 도달 불가.

---

## 네트워크 요청서 수정 필요 사항

### 결정적 오류: Oracle 1521 포트포워딩 누락

네트워크 요청서에 다음 내용이 있음:
> OracleDB(1521), MongoDB(27017)는 내부 서버에서만 접속하므로 포트포워딩 불필요

**이것이 잘못됨.** Azure 백엔드 → 로컬 Oracle DB 연결을 위해서는 Oracle 1521도 포트포워딩 필요:

| 외부포트 | 내부포트 | 용도 |
|---------|---------|------|
| 1521    | 1521    | OracleDB (Azure 백엔드 → 로컬 연결용) |

MongoDB는 Azure에서 직접 연결하지 않으므로 포트포워딩 불필요 (현재대로 OK).

### 추가해야 할 항목: Azure 아웃바운드 IP 화이트리스트

로컬 서버 방화벽에서 Azure의 아웃바운드 IP를 허용해야 함.
Azure Container Apps 아웃바운드 IP 확인 방법:

```bash
az containerapp show \
  --name <컨테이너앱이름> \
  --resource-group <리소스그룹> \
  --query "properties.outboundIpAddresses"
```

이 IP 목록을 네트워크 요청서 ⓐ 항목에 추가 요청 필요.

---

## 코드 변경 필요 사항

### 1. `.env` — ORACLE_HOST 변경 (Critical)

- **현재**: `ORACLE_HOST=10.1.92.119` (사설 IP, Azure에서 도달 불가)
- **변경**: `ORACLE_HOST=<공인IP 또는 도메인>` (네트워크팀이 포트포워딩 설정 후 확인)

**파일**: `integrated_PARK/.env`
**변수**: `ORACLE_HOST`

### 2. Azure Container Apps 환경변수도 함께 업데이트

Azure 포털 또는 CLI에서:
```bash
az containerapp update \
  --name <앱이름> \
  --resource-group <그룹명> \
  --set-env-vars ORACLE_HOST=<공인IP>
```

---

## 보안 고려사항

Oracle 1521을 공인 인터넷에 직접 노출하는 것은 **고위험**. 아래 중 하나 권장:

| 방식 | 장점 | 단점 |
|------|------|------|
| **IP 화이트리스트만 허용** | 간단 | Azure IP가 변경될 수 있음 |
| **VPN 터널 (권장)** | DB 포트 미노출, 안전 | 설정 복잡 |
| **SSH 터널** | 간단, 암호화 | 터널 유지관리 필요 |
| **Azure PostgreSQL 마이전** | 완전 클라우드, 안정 | 데이터 마이전 작업 필요 |

단기: IP 화이트리스트 + 포트포워딩
장기: Azure PostgreSQL Flexible Server 마이전 (`docs/plans/local-db-azure-migration.md` 참조)

---

## 검증 방법

포트포워딩 및 `.env` 변경 후:

```bash
# 1. 로컬에서 Oracle 연결 테스트
cd integrated_PARK
.venv/bin/python3 -c "
import oracledb, os
from dotenv import load_dotenv
load_dotenv()
conn = oracledb.connect(
    user=os.getenv('ORACLE_USER'),
    password=os.getenv('ORACLE_PASSWORD'),
    dsn=f\"{os.getenv('ORACLE_HOST')}:{os.getenv('ORACLE_PORT')}/{os.getenv('ORACLE_SID')}\"
)
print('연결 성공:', conn.version)
"

# 2. location 에이전트 실제 쿼리 테스트
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "강남 카페 창업 상권 분석해줘"}'
```

---

## 요약: 네트워크 요청서에 추가/수정할 것

1. **포트포워딩 추가**: `1521 → 1521` (OracleDB, Azure 연결용)
2. **IP 허용 추가**: Azure Container Apps 아웃바운드 IP 목록 (Azure CLI로 확인 후)
3. **보안**: 1521 포트는 Azure IP만 허용, 전체 개방 금지
