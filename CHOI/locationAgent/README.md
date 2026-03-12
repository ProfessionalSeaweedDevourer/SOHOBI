상권분석 에이전트 (LocationAgent)

기존 사용하던 데이터는 지역이 '동'단위였지만 이번에 사용한 데이터는 '상권단위'

Azure OpenAI + Semantic Kernel + SQLite를 활용한 F&B 창업 지원 상권분석 에이전트입니다.
오케스트레이터(부모 에이전트)에 SK Plugin으로 연결되는 자식 에이전트입니다.

## 폴더 구조
```
test_sang/
├── agent/
│   └── location_agent.py       # 상권분석 에이전트 본체 (DB 조회 → LLM 분석)
├── db/
│   ├── commercial.db           # SQLite DB (load_csv.py 실행 시 생성)
│   ├── load_csv.py             # CSV → DB 적재 스크립트 (실제 데이터)
│   ├── mock_db.py              # 샘플 데이터 생성 (테스트용)
│   └── repository.py           # DB 조회 레이어 (Oracle 전환 시 이 파일만 수정)
├── plugin/
│   └── location_plugin.py      # 오케스트레이터 연결용 SK Plugin 래퍼
├── test/
│   └── test_location.py        # 단독 테스트
├── .env                        # API 키 설정 (Git 미포함)
└── .env.example                # 환경변수 예시
```

## 시스템 구조
```
[오케스트레이터]
    ↓ SK Plugin 직접 연결
[LocationAgent]
    ↓ SQL 조회
[SQLite DB] ← CSV 데이터 적재
    ↓
상권별 매출/점포수 분석 결과 반환
```

## 데이터 출처

- 매출: 서울시 상권분석서비스 추정매출-상권 (VwsmTrdarSelngQq)
- 점포: 서울시 상권분석서비스 점포 (VwsmTrdarStorQq)
- 기준 분기: 2024년 1~4분기

## 지원 지역 / 업종

**지역**: 홍대, 합정, 연남동, 망원, 신촌, 강남, 이태원, 건대, 잠실

**업종**: 한식, 중식, 일식, 양식, 베이커리, 패스트푸드, 치킨, 분식, 호프, 카페, 미용실, 편의점 등

## 실행 방법
```bash
# 1. 가상환경 활성화
.venv\Scripts\activate

# 2. 패키지 설치 (최초 1회)
pip install semantic-kernel python-dotenv pandas

# 3. .env 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 4. DB 적재 (CSV 파일 필요)
python db/load_csv.py

# 5. 테스트 실행
python test/test_location.py
```

## 환경변수 (.env)
```
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

## Oracle 전환 시

`db/repository.py` 파일만 수정하면 됩니다:
- `import sqlite3` → `import cx_Oracle`
- `sqlite3.connect()` → `cx_Oracle.connect(user, pw, dsn)`
- SQL: `LIMIT N` → `WHERE ROWNUM <= N`
- 플레이스홀더: `?` → `:1`
