# GovSupportPlugin — 정부지원사업 & 소상공인 금융지원 통합 검색

소상공인/F&B 창업자가 받을 수 있는 **정부 보조금, 창업패키지, 정책자금 대출, 신용보증, 고용지원, 교육/컨설팅** 정보를 AI 기반으로 통합 검색하는 Semantic Kernel 플러그인입니다.

SOHOBI 프로젝트의 **행정 에이전트(AdminAgent)** 플러그인으로 동작하며, `integrated_PARK` 오케스트레이션 파이프라인에 바로 연결됩니다.

---

## 핵심 기능

### 1. 정부지원사업 검색
- 다중 데이터 소스 기반 통합 데이터 (1,887건)
- 업종/지역/창업단계에 맞는 지원사업 자동 매칭
- 보조금, 창업패키지, 사업화 자금, 교육 프로그램 등

### 2. 소상공인 금융지원 검색
- 소상공인 정책자금 (융자/대출): 일반경영안정, 긴급경영, 성장촉진, 재도전, 전환자금
- 신용보증: 신용보증기금, 기술보증기금, 지역신보재단, 서울신보재단
- 운전자금, 시설자금, 전환자금

### 3. 고용/교육 지원 검색
- 채용장려금, 고용촉진장려금, 청년추가고용장려금
- 두루누리 사회보험료 지원, 일자리안정자금
- 경영 컨설팅, 역량강화 교육

### 4. 외식업/F&B 특화 지원
- 위생등급제 인센티브, HACCP 인증 지원
- 배달앱 수수료 지원, 온라인 판로개척
- 외식업 경영주 아카데미, 창업 인큐베이팅

### 5. 지역별 지원사업
- 서울/경기/부산 등 광역지자체 소상공인 지원사업
- 지역 이차보전(이자 지원), 임차료 지원, 공유주방 등

---

## 데이터 소스

| # | 소스 | API 키 환경변수 | 건수 | 설명 |
|---|------|-----------------|------|------|
| 1 | 정부24 공공서비스 API | `GOV24_API_KEY` | ~1,974건 | 정부 보조금, 지원사업, 창업패키지 (35개 키워드 필터링) |
| 2 | K-Startup 사업공고/소개 API | `KSTARTUP_API_KEY` | ~2,065건 | 창업진흥원 모집중 공고 + 사업소개 (data.go.kr #15125364) |
| 3 | 창업공간플랫폼 API | `KISED_SPACE_API_KEY` | (별도승인) | 전국 창업공간/보육센터 (data.go.kr #15125365) |
| 4 | 정부지원사업 주관기관 API | `KISED_AGENCY_API_KEY` | ~2,153건 | 지원사업별 수행기관 정보 (data.go.kr #15125366) |
| 5 | 창업에듀 교육과정 API | `KISED_EDU_API_KEY` | ~356건 | 온라인 창업교육 과정 (data.go.kr #15125358) |
| 6 | 중소벤처24 API | `SME24_API_KEY` | (연결중) | 중기부 지원사업 공고 (smes.go.kr) |
| 7 | 기업마당 API | `BIZINFO_API_KEY` | (연결중) | 범정부 지원사업 통합 검색 (bizinfo.go.kr) |
| 8 | 큐레이션 데이터 | (키 불필요) | 19건 | 소진공 정책자금, 신용보증, 고용지원, 외식업 특화 |
| | **합계 (현재)** | | **~5,600건+** | 중복 제거 후, AI Search 인덱싱 완료 |

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
| 데이터 소스 | 정부24 + 창업진흥원(4종) + 중소벤처24 + 기업마당 + 큐레이션 |
| API 서버 | FastAPI + Uvicorn |

---

## 검색 아키텍처

```
사용자 질문
    |
    v
[쿼리 분석] -- 지역 자동 추출 (17개 시/도)
    |
    v
[Azure OpenAI] -- text-embedding-3-large로 쿼리 벡터화
    |
    v
[Azure AI Search] -- 3중 검색
    +-- BM25 키워드 검색
    +-- 벡터 유사도 검색 (k=20)
    +-- 시맨틱 랭커 재순위화
    |
    +-- OData 필터: target_region = '{지역}' OR '전국'
    |
    v
[결과 반환] -- 상위 15건 -> GPT가 분석/필터링 후 사용자에게 안내
```

---

## 데이터 파이프라인 (Azure Functions 자동화)

데이터 수집 + 인덱싱이 Azure Functions 위에서 자동으로 동작합니다. 로컬에서 스크립트를 돌릴 필요 없습니다.

### 자동 실행
- 매주 월요일 새벽 3시(KST) Timer Trigger 자동 실행
- 전체 API 소스에서 수집 -> 중복 제거 -> Cosmos DB 적재 -> AI Search 임베딩 인덱싱

### 수동 실행
데이터를 즉시 갱신하고 싶을 때:
```bash
curl -X POST https://<함수앱이름>.azurewebsites.net/api/refresh_data \
  -H "x-functions-key: <함수키>"
```
응답 예시:
```json
{
  "status": "success",
  "collected": 1887,
  "sources": {"gov24": 1830, "kstartup": 0, "sme24": 0, "curated": 20},
  "cosmos_count": 1887,
  "search_count": 1887
}
```

### API 키 추가 방법
data.go.kr에서 새 API 키를 발급받으면:
1. Azure Portal -> 함수 앱 -> 구성 -> 애플리케이션 설정
2. 환경변수 추가 (아래 키 목록 참조)
3. 다음 주간 실행 시 자동 반영, 또는 수동 실행으로 즉시 반영
4. 코드 수정 불필요 — 키만 넣으면 해당 소스에서 자동 수집 시작

```
필요 환경변수:
GOV24_API_KEY, KSTARTUP_API_KEY, KISED_SPACE_API_KEY,
KISED_AGENCY_API_KEY, KISED_EDU_API_KEY, SME24_API_KEY, BIZINFO_API_KEY
```

### 파이프라인 흐름
```
[Azure Functions - Timer/HTTP Trigger]
    |
    v
[데이터 수집] -- 8개 소스 병렬 호출 + 큐레이션 데이터 병합
    +-- 정부24 API (GOV24_API_KEY)
    +-- K-Startup 사업공고 API (KSTARTUP_API_KEY)        ← 창업진흥원
    +-- 창업공간플랫폼 API (KISED_SPACE_API_KEY)         ← 창업진흥원
    +-- 정부지원사업 주관기관 API (KISED_AGENCY_API_KEY)  ← 창업진흥원
    +-- 창업에듀 교육과정 API (KISED_EDU_API_KEY)        ← 창업진흥원
    +-- 중소벤처24 API (SME24_API_KEY)
    +-- 기업마당 API (BIZINFO_API_KEY)
    +-- 큐레이션 데이터 (키 불필요) -- 소진공/신보/고용/외식업
    |
    v
[중복 제거] -- 프로그램명 기준
    |
    v
[Cosmos DB 적재] -- 지역 자동 태깅 + 메타태그 임베딩 텍스트
    |
    v
[AI Search 인덱싱] -- text-embedding-3-large (3,072차원) + 시맨틱 랭커
```

### Azure Functions 배포
```bash
cd NAM2/azure_functions
func azure functionapp publish <함수앱이름>
```

### 헬스체크
```
GET https://<함수앱이름>.azurewebsites.net/api/health
```

---

## Azure 팀 계정 이관

개인 계정에서 팀 계정으로 이관할 때:

```bash
# 1. .env.template을 복사해서 팀 계정 키 입력
cp .env.template .env.team
# 값 채우기 (AZURE_OPENAI_*, COSMOS_*, AZURE_SEARCH_*, AZURE_STORAGE_*)

# 2. 이관 스크립트 실행 (리소스 생성 + 데이터 전체 이관)
python scripts/migrate_azure_account.py --env .env.team

# 3. 이관 완료 후 .env.team을 .env로 교체
cp .env.team .env
```

이관 스크립트가 자동으로 하는 일:
- Cosmos DB 데이터베이스/컨테이너 생성
- Blob Storage 컨테이너 생성
- CSV -> Blob -> Cosmos DB -> AI Search 전체 파이프라인 실행

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
# Azure 인프라 (필수)
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_EMBEDDING_DIMS=3072
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_SEARCH_ENDPOINT=...
AZURE_SEARCH_API_KEY=...
AZURE_SEARCH_INDEX_NAME=gov-programs-index
COSMOS_ENDPOINT=...
COSMOS_KEY=...
COSMOS_DATABASE_NAME=sohobidb

# 공공데이터 API (데이터 수집용)
GOV24_API_KEY=...
KSTARTUP_API_KEY=...
KISED_SPACE_API_KEY=...
KISED_AGENCY_API_KEY=...
KISED_EDU_API_KEY=...
SME24_API_KEY=...
BIZINFO_API_KEY=...
```

전체 환경변수 목록은 `sohobi-azure/.env.template` 참조.

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
NAM2/
+-- GovSupportPlugin.py          <- 핵심 플러그인 (Semantic Kernel, 추천 엔진)
+-- app.py                       <- 독립 테스트 서버 (FastAPI)
+-- requirements.txt             <- 의존성 목록
+-- readme.md                    <- 이 문서
+-- azure_functions/
    +-- function_app.py          <- Azure Functions 진입점 (Timer/HTTP Trigger)
    +-- data_collector.py        <- 다중 API 데이터 수집기
    +-- data_pipeline.py         <- Cosmos DB + AI Search 적재 파이프라인
    +-- requirements.txt         <- Functions 의존성
    +-- host.json                <- Functions 런타임 설정
    +-- local.settings.json      <- 로컬 테스트용 환경변수 템플릿
    +-- .funcignore              <- 배포 제외 파일 목록
```

---

## 향후 확장 계획

| 플러그인 | 설명 | 상태 |
|----------|------|------|
| 정부지원사업 검색 | 보조금, 창업패키지, 정책자금 | 완료 |
| 소상공인 금융지원 | 대출, 융자, 보증 | 완료 (다중 소스) |
| 고용/교육 지원 | 채용장려금, 컨설팅 | 완료 (데이터 통합) |
| 외식업/F&B 특화 | 위생등급, HACCP, 배달지원 | 완료 |
| 지역별 지원사업 | 서울/경기/부산 특별자금 | 완료 |
| 인허가 체크리스트 | 업종별 필요 허가/신고 목록 | 예정 |
| 소상공인 대출 비교 | 금리/한도/자격 실시간 비교 | 예정 |
| 세금 캘린더 | 부가세/종소세 신고 일정 알림 | 예정 |

---

## 담당

**남대은 (NAM)** -- 데이터 파이프라인, RAG 검색 플러그인, 행정 에이전트 플러그인 개발
