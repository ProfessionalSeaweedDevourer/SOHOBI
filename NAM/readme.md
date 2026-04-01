# GovSupportPlugin — 정부지원사업 & 소상공인 금융지원 통합 검색

소상공인/F&B 창업자가 받을 수 있는 **정부 보조금, 창업패키지, 정책자금 대출, 신용보증, 고용지원, 교육/컨설팅** 정보를 AI 기반으로 통합 검색하는 Semantic Kernel 플러그인입니다.

SOHOBI 프로젝트의 **행정 에이전트(AdminAgent)** 플러그인으로 동작하며, `integrated_PARK` 오케스트레이션 파이프라인에 바로 연결됩니다.

---

## 핵심 기능

### 1. 정부지원사업 검색
- 정부24 공공서비스 API 기반 데이터 (1,400건+)
- 업종/지역/창업단계에 맞는 지원사업 자동 매칭
- 보조금, 창업패키지, 사업화 자금, 교육 프로그램 등

### 2. 소상공인 금융지원 검색
- 소상공인 정책자금 (융자/대출)
- 신용보증/기술보증 지원
- 긴급경영안정자금, 재기지원자금
- 운전자금, 시설자금, 전환자금

### 3. 고용/교육 지원 검색
- 채용장려금, 고용안정지원금
- 두루누리 사회보험료 지원
- 경영 컨설팅, 역량강화 교육

---

## 기술 스택

| 구성 요소 | 기술 |
|-----------|------|
| AI 오케스트레이션 | Microsoft Semantic Kernel (Python) |
| LLM | Azure OpenAI GPT-4o |
| 임베딩 | Azure OpenAI text-embedding-3-large (3,072차원) |
| 검색 엔진 | Azure AI Search (하이브리드 + 시맨틱 랭커) |
| 데이터 저장 | Azure Cosmos DB (NoSQL, Serverless) |
| 원본 저장 | Azure Blob Storage |
| 데이터 소스 | 정부24 공공서비스 API (data.go.kr) |
| API 서버 | FastAPI + Uvicorn |

---

## 검색 아키텍처

```
사용자 질문
    │
    ▼
[쿼리 분석] — 지역 자동 추출 (17개 시/도)
    │
    ▼
[Azure OpenAI] — text-embedding-3-large로 쿼리 벡터화
    │
    ▼
[Azure AI Search] — 3중 검색
    ├── BM25 키워드 검색
    ├── 벡터 유사도 검색 (k=20)
    └── 시맨틱 랭커 재순위화
    │
    ├── OData 필터: target_region = '{지역}' OR '전국'
    │
    ▼
[결과 반환] — 상위 15건 → GPT가 분석/필터링 후 사용자에게 안내
```

---

## 데이터 파이프라인

데이터 수집부터 검색 인덱싱까지 4단계 자동화 파이프라인:

```
[Step 0] 정부24 API 수집 → CSV
  - 10,000건+ 전체 서비스 → F&B/금융 키워드 필터링
  - 35개 키워드: 소상공인, 창업, 대출, 융자, 보증, 고용지원 등
  - 출력: data/raw/gov24_programs.csv

[Step 1] CSV → Azure Blob Storage 업로드
  - sohobi-docs 컨테이너, raw/ 경로

[Step 2] Blob → Azure Cosmos DB 적재
  - 지역 자동 태깅 (REGION_MAP: 17개 시/도)
  - 메타 태그 임베딩 텍스트 생성:
    [지역: 서울] [분야: 창업] [유형: 현금] 사업명: ...
  - service_id 기반 중복 방지

[Step 3] Cosmos DB → Azure AI Search 인덱싱
  - text-embedding-3-large 벡터 생성 (3,072차원)
  - 시맨틱 검색 설정 (sohobi-semantic)
  - target_region 필터/패싯 필드 설정
  - 배치 업로드: 100건/배치, 0.5초 쓰로틀
```

파이프라인 스크립트 위치: `sohobi-azure/scripts/pipeline/`

---

## integrated_PARK 연동

### AdminAgent 등록 구조

```python
# integrated_PARK/agents/admin_agent.py
from plugins.gov_support_plugin import GovSupportPlugin
kernel.add_plugin(GovSupportPlugin(), plugin_name="GovSupport")
```

### 필요 환경변수

```env
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_SEARCH_ENDPOINT=...
AZURE_SEARCH_API_KEY=...
AZURE_SEARCH_INDEX_NAME=gov-programs-index
```

### SignOff 연동

AdminAgent의 응답은 SignOff Agent가 품질 검증합니다:
- **A1**: 법령/조항 인용 여부
- **A2**: 서비스 양식명 언급
- **A3**: 절차 단계 설명
- **A4**: 담당 기관명 안내
- **A5**: 처리 기한 정보

---

## 로컬 개발

```bash
# 1. 가상환경 & 의존성
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# 2. 환경변수 설정
# sohobi-azure/.env 파일에 Azure 키 설정

# 3. 독립 서버 실행 (테스트용)
uvicorn app:app --reload --port 8001

# 4. API 테스트
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "서울에서 카페 창업하려는데 지원금 있어?"}'
```

---

## 파일 구조

```
NAM/
├── GovSupportPlugin.py    ← 핵심 플러그인 (Semantic Kernel)
├── app.py                 ← 독립 테스트 서버 (FastAPI)
├── requirements.txt       ← 의존성 목록
└── readme.md              ← 이 문서
```

---

## 향후 확장 계획

| 플러그인 | 설명 | 상태 |
|----------|------|------|
| 정부지원사업 검색 | 보조금, 창업패키지, 정책자금 | 완료 |
| 소상공인 금융지원 | 대출, 융자, 보증 | 완료 (데이터 통합) |
| 고용/교육 지원 | 채용장려금, 컨설팅 | 완료 (데이터 통합) |
| 인허가 체크리스트 | 업종별 필요 허가/신고 목록 | 예정 |
| 소상공인 대출 비교 | 금리/한도/자격 실시간 비교 | 예정 |
| 세금 캘린더 | 부가세/종소세 신고 일정 알림 | 예정 |

---

## 담당

**남대은 (NAM)** — 데이터 파이프라인, RAG 검색 플러그인, 행정 에이전트 플러그인 개발
