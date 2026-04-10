# integrated_PARK/db

데이터베이스 조회 레이어. Azure PostgreSQL Flexible Server에 연결하여 상권·재무·지도 데이터를 제공한다.

---

## 구조

```
db/
├── repository.py       상권분석 에이전트(LocationAgent)용 메인 DB 레이어
├── finance_db.py       재무 시뮬레이션용 DB 조회 (DBWork 클래스)
├── schema_pg.sql       PostgreSQL 테이블 스키마 정의
├── export_oracle_to_csv.py  Oracle → CSV 마이그레이션 유틸리티 (일회성)
└── dao/                지도 모드용 Data Access Object 모듈
```

## 환경변수

`integrated_PARK/.env`에 다음 변수가 필요하다:

| 변수 | 설명 |
|------|------|
| `PG_HOST` | Azure PostgreSQL 서버 호스트 |
| `PG_PORT` | 포트 (기본 5432) |
| `PG_DB` | 데이터베이스명 |
| `PG_USER` | 접속 사용자 |
| `PG_PASSWORD` | 접속 비밀번호 |

## 주요 모듈

### repository.py

`CommercialRepository` — LocationAgent가 사용하는 유일한 DB 인터페이스.
- 행정동 코드 기반 지역 매핑 (208개 키워드)
- 업종 코드 매핑 (서비스 업종 코드)
- 커넥션 풀: `psycopg2.pool.ThreadedConnectionPool`

### finance_db.py

`DBWork` — FinanceSimulationPlugin이 사용하는 재무 데이터 조회.
- BaseDAO 상속, 커넥션 풀 공유
- 업종·지역별 평균 매출 조회

### dao/ — 지도 모드 DAO

| DAO | 역할 |
|-----|------|
| `baseDAO.py` | 커넥션 풀 공유 기반 클래스 |
| `dongMappingDAO.py` | 행정동 코드 ↔ 이름 매핑 |
| `landValueDAO.py` | 공시지가 조회 |
| `landmarkDAO.py` | 랜드마크·주요 시설 조회 |
| `mapInfoDAO.py` | 지도 표시용 종합 정보 |
| `molitRtmsDAO.py` | 국토부 실거래가 (전국) |
| `sangkwonDAO.py` | 상권 분석 데이터 |
| `sangkwonStoreDAO.py` | 상권 내 점포 데이터 |
| `seoulRtmsDAO.py` | 서울 실거래가 |
