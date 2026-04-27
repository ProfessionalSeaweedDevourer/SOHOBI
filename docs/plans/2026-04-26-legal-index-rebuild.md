# Legal AI Search 인덱스 재구축 기획 (RAG 관점)

> 작성일: 2026-04-26
> 상태: **문서화 단계** (실행 미착수)
> 관련: [2026-04-26-azure-tenant-migration.md](2026-04-26-azure-tenant-migration.md) Phase 0 step 1 (AI Search 백필)
> 입력 데이터: 프로젝트 루트의 4개 JSON (커밋하지 않음 — `.gitignore` 또는 외부 보관 필요)

## Context

Azure 테넌트 이전 기획안에서 "AI Search 인덱스는 소스에서 재빌드"로 결정되었다. 사용자가 legal-index 재인덱싱용 원천 데이터(원본·전처리본 각 2개, 총 4개 JSON) 를 프로젝트 루트에 제공했고, 이를 기반으로 (1) 현 전처리 품질 평가 (2) 신규 구독에서의 인덱스 재구축안 (3) 전처리 개선안을 정리한다.

---

## 1. 입력 데이터 인벤토리

| 파일 | 단계 | 배치 | 레코드 | 비고 |
|------|------|------|--------|------|
| `law_data_for_embedding.json` | 원본 (article 단위) | 배치 1 | 291 | 개인정보 보호법 패밀리 |
| `law_data_for_embedding_1.json` | 원본 (article 단위) | 배치 2 | 3,120 | 30개 법령 |
| `refined_law_data.json` | 전처리(청크) | 배치 1 | 292 | 개인정보 보호법 2개 법령 |
| `refined_law_data_1.json` | 전처리(청크) | 배치 2 | 3,704 | 30개 법령 |

**합계**: 31개 법령, 청크화 후 **3,996 records**.

배치 1·2는 **법령 셋이 다른 별개 묶음**(intersection 0). `_1` 접미사는 v1이 아니라 "두 번째 배치" 의미.

### 법령 커버리지 (배치 2)
세무·재무 (소득세·부가가치세·주세), 식품위생, 건축, 폐기물관리, 근로기준·최저임금, 국민건강증진, 중소기업창업·소상공인 보호, 소방시설, 공중위생, 상가임대차 — 총 30개. 본법 + 시행령 + 시행규칙 패밀리.

### 스키마

**원본 (`law_data_for_embedding*`)**:
```json
{"law_name", "mst", "article_no", "content", "metadata": {"source", "type"}}
```

**전처리 (`refined_law_data*`)**:
```json
{
  "id": "law_270351_1_1",          // {prefix}_{mst}_{articleNo}_{seq}
  "lawName", "mst", "articleNo",
  "chapterTitle", "sectionTitle", "articleTitle",
  "content",                        // 청크 단위 텍스트
  "fullText",                       // "[lawName > chapter] content"
  "source", "docType",
  "chunkIndex", "isChunked"
}
```

---

## 2. 전처리 품질 평가 — RAG 관점

### 2-1. 잘 된 점
1. **계층 메타데이터 분리 보존**: `chapterTitle / sectionTitle / articleTitle` — 검색 필터·결과 표시·재정렬에 필수. 한국 법률 RAG 베스트 프랙티스.
2. **fullText에 breadcrumb 포함** (`[법령명 > 장] 본문`): 임베딩 시 컨텍스트 부여 → 같은 표현이 여러 법령에 등장해도 구분 가능.
3. **항(項) 단위 분할**: 식품위생법 37조처럼 긴 조문은 항별로 분리 (chunkIndex 0~13). 법률 검색의 **답변 grounding 단위와 일치** — 매우 적절.
4. **mst (법령 마스터키) 보존**: 국가법령정보센터 API 재동기화 가능. ID 안정성 확보.
5. **데이터 규모 적정**: 3,996 chunks → embedding 비용 1회 ~$0.016 (text-embedding-3-small 기준), Azure AI Search S1 한 인덱스에 충분.

### 2-2. 개선 필요 — 우선순위 순

#### [HIGH] chunkIndex=0 단독 청크가 articleTitle만 포함
- **현황**: 청크된 article 367개 중 **66개**에서 `chunkIndex=0`이 `"제37조(영업허가 등)"` 같은 12자 제목 한 줄만 담고 있음 (`law_277149_37_61_p0` 예시).
- **임팩트**: 임베딩 가치 0. 검색에 잡히면 "본문 없음"이 hit되어 noise. 토큰·인덱스 슬롯 낭비.
- **개선**: 인덱싱 단계에서 제외 OR 다음 청크와 병합. `articleTitle`은 별도 메타필드로 보존 중이므로 본문 청크에 prefix로만 사용.

#### [HIGH] 임베딩 텍스트에 articleTitle 누락
- **현황**: `fullText = [lawName > chapterTitle] content`. articleTitle은 별도 필드로 분리되어 임베딩 입력에서 빠져있음.
- **임팩트**: chunkIndex>0 항(항②, 항③ ...)이 임베딩 단독으로 들어가면 "어느 조의 어느 항인지" 의미가 약화됨. 짧은 항(78자~) 검색 정확도 저하.
- **개선**: 임베딩 입력 텍스트를 다음 형식으로 재구성:
  ```
  [{lawName} > {chapterTitle}] {articleTitle} ({chunkIndex+1}/{totalChunks}) {content}
  ```
  표시용 `fullText`와 임베딩용 `embeddingText`를 분리 저장.

#### [HIGH] 표·서식 이미지 토큰 + ASCII 박스 잔존
- **현황**: 107개 record에 `[표/서식 이미지]` 토큰 잔존, 104개에 `┌─│` ASCII 박스 그대로 노출 (부가가치세법 시행령 8조, 101조 등).
- **임팩트**: 토큰 낭비(부가세 시행령 101조 4,309자 중 절반이 표 노이즈), 임베딩 의미 희석, 결과 표시 시 가독성 최악.
- **개선**: 전처리 단계에서:
  - `[표/서식 이미지]` 다회 등장 → 1회로 정규화 + `(상세 표는 원문 참조: <법령정보센터 URL>)` 안내
  - ASCII 박스 라인 (`┌`, `│`, `└` 등 문자만 있는 라인) 제거
  - 표 자체를 별도 필드(`hasTable: true`)로 표시하여 검색은 본문만, 응답 생성 시 표 존재만 안내

#### [MED] 짧은 청크 (<100자) 277개 — 컨텍스트 부족
- **현황**: 청크된 record 979개 중 **277개(28%)** 가 100자 미만. 항 본문이 매우 짧은 경우(②항이 한 문장).
- **임팩트**: 임베딩 정보량 부족 → 인접 항·동일 조의 다른 청크와 의미적 거리가 가까워져 어느 chunk가 hit돼도 답변 정확도 비슷. 검색 결과 다양성·정확도 모두 저하.
- **개선 옵션**:
  - **A (권장)**: articleTitle을 임베딩 prefix로 강제 포함 (위 [HIGH] 2번과 동일 해결).
  - **B (추가)**: 100자 미만 항은 같은 조 내 인접 항과 sliding-window로 묶어서 별도 청크 추가 (검색 회수율 ↑, index size 1.2~1.3배).

#### [MED] 시행일·공포번호 메타데이터 부재
- **현황**: 현재 메타에 `docType: "현행법령"` 정도. 그러나 한국 법률은 "시행일 X 이전/이후" 구분이 매우 빈번한 실무 질문.
- **임팩트**: "2024년 7월 시행 개정 식품위생법" 같은 시점 한정 질의 답변 불가.
- **개선**: 국가법령정보센터 API에서 `enforceDate`, `promulgationNo`, `revisionType` (제정/개정/일부개정) 추가 수집 → 인덱스 필드로 보강.

#### [MED] 단일 chunk article 1,592개 — fullText 중복 가능
- **현황**: 1,959개 article 중 1,592개(81%)가 단일 chunk. 이 경우 `content == fullText - breadcrumb` 으로 정보 중복.
- **임팩트**: 인덱스 storage 낭비는 미미하나, `fullText` 와 `content` 모두 searchable이면 BM25 score 이중 가산.
- **개선**: 단일 chunk article은 `fullText` 필드를 검색 대상에서 제외 (`searchable: false`) 하고 표시용으로만 보존.

#### [LOW] 법령 커버리지 갭
- **현황**: 30개 법령. 산업안전보건법, 노동조합법, 외국인 근로자 고용법, 공정거래법, 부정청탁금지법 등 소상공인 빈출 질의 영역 일부 누락 가능성.
- **개선**: 과거 query 로그에서 legal 관련 질문 분석 → "검색 결과 없음" 비율이 높은 도메인 식별 → 2차 수집 우선순위 산출. 본 기획 외 별도 워크스트림.

---

## 3. 신규 인덱스 재구축안

### 3-1. Azure AI Search 인덱스 스키마 (`legal-index-v2`)

```python
{
  "name": "legal-index-v2",
  "fields": [
    {"name": "id", "type": "Edm.String", "key": True},
    {"name": "lawName", "type": "Edm.String", "searchable": True, "filterable": True, "facetable": True, "analyzer": "ko.lucene"},
    {"name": "lawCategory", "type": "Edm.String", "filterable": True, "facetable": True},  # 신규: 본법/시행령/시행규칙
    {"name": "mst", "type": "Edm.String", "filterable": True},
    {"name": "articleNo", "type": "Edm.String", "filterable": True},
    {"name": "articleId", "type": "Edm.String", "filterable": True, "facetable": True},  # 신규: parent grouping용 "law_{mst}_{articleNo}"
    {"name": "articleTitle", "type": "Edm.String", "searchable": True, "analyzer": "ko.lucene"},
    {"name": "chapterTitle", "type": "Edm.String", "searchable": True, "analyzer": "ko.lucene"},
    {"name": "sectionTitle", "type": "Edm.String", "searchable": True, "analyzer": "ko.lucene"},
    {"name": "content", "type": "Edm.String", "searchable": True, "analyzer": "ko.lucene"},
    {"name": "fullText", "type": "Edm.String", "searchable": False, "retrievable": True},  # 표시용으로만 retain
    {"name": "embeddingText", "type": "Edm.String", "searchable": False, "retrievable": False},  # audit용 (실제 임베딩 입력)
    {"name": "chunkIndex", "type": "Edm.Int32", "filterable": True, "sortable": True},
    {"name": "totalChunks", "type": "Edm.Int32", "filterable": True},  # 신규: parent group 크기
    {"name": "isChunked", "type": "Edm.Boolean", "filterable": True},
    {"name": "hasTable", "type": "Edm.Boolean", "filterable": True},  # 신규: 표 포함 여부
    {"name": "docType", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "enforceDate", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},  # 신규
    {"name": "source", "type": "Edm.String", "filterable": True},
    {"name": "contentVector", "type": "Collection(Edm.Single)", "searchable": True,
     "vectorSearchDimensions": 1536, "vectorSearchProfile": "default"}
  ],
  "vectorSearch": {
    "algorithms": [{
      "name": "hnsw-default", "kind": "hnsw",
      "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"}
    }],
    "profiles": [{"name": "default", "algorithm": "hnsw-default"}]
  },
  "semantic": {
    "configurations": [{
      "name": "legal-semantic",
      "prioritizedFields": {
        "titleField": {"fieldName": "articleTitle"},
        "prioritizedContentFields": [{"fieldName": "content"}],
        "prioritizedKeywordsFields": [{"fieldName": "lawName"}, {"fieldName": "chapterTitle"}]
      }
    }]
  }
}
```

핵심 결정:
- **Korean analyzer = `ko.lucene`** (Azure 내장 Lucene Korean). 형태소 분석으로 BM25 정확도 ↑.
- **`fullText`는 retrievable만, searchable=False**: 단일 chunk 중복 가산 방지.
- **`articleId` facet**: 검색 후 parent grouping용. `f"law_{mst}_{articleNo}"`.
- **하이브리드 검색**: BM25 + 벡터 + semantic ranking 3-way (Azure AI Search semantic ranker 활용).

### 3-2. 임베딩 입력 텍스트 정규화

```python
def compose_embedding_text(record):
    breadcrumb = f"[{record['lawName']}"
    if record['chapterTitle']:
        breadcrumb += f" > {record['chapterTitle']}"
    if record['sectionTitle']:
        breadcrumb += f" > {record['sectionTitle']}"
    breadcrumb += "]"
    
    chunk_marker = ""
    if record['totalChunks'] > 1:
        chunk_marker = f" ({record['chunkIndex']+1}/{record['totalChunks']})"
    
    return f"{breadcrumb} {record['articleTitle']}{chunk_marker} {record['content']}"
```

예시:
- 기존: `[식품위생법 > 제7장 영업] ② 식품의약품안전처장 또는...`
- 신규: `[식품위생법 > 제7장 영업] 제37조(영업허가 등) (3/13) ② 식품의약품안전처장 또는...`

### 3-3. 청크 정리 단계 (전처리 보강)

```
scripts/legal_index/
  ├── 01_clean.py
  │     - [표/서식 이미지] 다회 → 1회로 정규화
  │     - ASCII 박스 라인 제거 (정규식: ^[┌─│└┴┬┤├═║]*$)
  │     - title-only chunk (chunkIdx=0, content==articleTitle, len<30) 제거
  │     - hasTable=True 플래그 부여
  ├── 02_compose_text.py
  │     - embeddingText 필드 생성 (위 함수)
  │     - articleId, totalChunks 부여
  │     - lawCategory 분류 (lawName 정규식: 시행령/시행규칙/법)
  ├── 03_enrich_metadata.py
  │     - 국가법령정보센터 API 호출 → enforceDate, promulgationNo
  │     - 캐시 (mst → metadata) 로컬 SQLite
  ├── 04_embed.py
  │     - Azure OpenAI text-embedding-3-small (1536d)
  │     - batch_size=16 (rate limit 안전)
  │     - exponential backoff
  ├── 05_upload.py
  │     - Azure AI Search SDK upload (1000 docs/batch)
  │     - merge-or-upload 모드 (재실행 멱등)
  └── 06_verify.py
        - 인덱스 row count == 입력 record count
        - sample 10개 query 실행 → score 분포 확인
```

### 3-4. 검색 후처리 — parent grouping

`backend/plugins/legal_search_plugin.py` 수정:

```python
async def search_with_grouping(query, top_k=10):
    # 1. 하이브리드 검색 (BM25 + vector + semantic)
    raw_results = await azure_search.search(
        search_text=query,
        vector_queries=[VectorizedQuery(vector=embed(query), k_nearest_neighbors=20, fields="contentVector")],
        query_type="semantic",
        semantic_configuration_name="legal-semantic",
        top=top_k * 3,  # parent grouping 후 top_k 보장 위해 over-fetch
    )
    
    # 2. articleId로 grouping, 각 group에서 best score chunk만 선택
    grouped = {}
    for r in raw_results:
        aid = r['articleId']
        if aid not in grouped or r['@search.rerankerScore'] > grouped[aid]['@search.rerankerScore']:
            grouped[aid] = r
    
    # 3. 같은 article의 모든 chunk를 회수해서 합쳐서 반환 (응답 grounding 강화)
    final = []
    for aid, best in sorted(grouped.values(), key=lambda x: -x['@search.rerankerScore'])[:top_k]:
        all_chunks = await azure_search.search(filter=f"articleId eq '{aid}'", order_by="chunkIndex asc")
        final.append({
            "articleId": aid,
            "lawName": best['lawName'],
            "articleTitle": best['articleTitle'],
            "fullArticle": "\n".join(c['content'] for c in all_chunks),
            "score": best['@search.rerankerScore'],
            "url": build_law_url(best['mst'], best['articleNo']),
        })
    return final
```

이 변경의 효과:
- 한 조문이 여러 chunk로 hit되어도 결과 1개로 표시 (UX 개선)
- 응답 생성 LLM에는 article 전체 텍스트가 grounding으로 들어가 답변 일관성 ↑

---

## 4. 평가 (Evaluation)

### 4-1. 평가셋 구축
- 과거 query 로그(`backend/logger.py`의 queries.jsonl)에서 **legal 라우팅된 질문 100개** 샘플
- 사용자 대화 맥락 포함 (단일 질문이 아닌 멀티턴 일부)
- 각 질문에 대한 **정답 article (mst+articleNo)** 라벨링 — 검토 1인 + 더블체크 1인

### 4-2. 메트릭
| 메트릭 | 의미 | 목표 |
|--------|------|------|
| **Recall@5** | 정답 article이 top-5 안에 들어오는 비율 | 기존 대비 +10%p |
| **MRR** | 정답 article의 평균 역순위 | 기존 대비 +0.05 |
| **nDCG@10** | 순위 가중 정확도 | 기존 대비 +0.05 |
| **응답 grounding rate** | LLM 답변에 인용된 article이 검색 결과 안에 있는 비율 | >95% |
| **avg latency** | end-to-end 검색 지연 | <800ms p95 |

### 4-3. A/B
- 기존 `legal-index` (운영 중) vs `legal-index-v2` 동일 평가셋 실행
- v2가 모든 메트릭에서 동등 이상이면 cutover, 1개라도 회귀하면 원인 분석 후 재빌드

---

## 5. 핵심 파일 / 신규 작성 산출물

| 경로 | 용도 |
|------|------|
| `scripts/legal_index/01_clean.py` ~ `06_verify.py` | 6단계 인덱싱 파이프라인 (신규) |
| `scripts/legal_index/eval.py` | 평가셋 실행, 메트릭 계산 (신규) |
| `data/legal_eval_set.jsonl` | 100문항 평가셋 (신규, 라벨링 결과) |
| `infra/bicep/modules/ai-search.bicep` | `legal-index-v2` 정의 (Azure 이전 기획안과 통합) |
| `backend/plugins/legal_search_plugin.py` | parent grouping 후처리 추가 |

원본 4개 JSON: `data/legal/raw/` 디렉토리로 이동하고 `.gitignore` 처리 (용량·저작권 모두 고려).

---

## 6. 검증 (End-to-end)

### Phase A — 파이프라인 단위
```bash
# 클린업 후 통계
python scripts/legal_index/01_clean.py --in refined_law_data_1.json --out cleaned.jsonl
python -c "import json; data=[json.loads(l) for l in open('cleaned.jsonl')]; print(f'count: {len(data)}'); print(f'avg content len: {sum(len(r[\"content\"]) for r in data)//len(data)}')"
# 기대: title-only 66개 제거, 표 노이즈 정리 후 평균 길이 확인

# 임베딩 텍스트 샘플 검사
python scripts/legal_index/02_compose_text.py --in cleaned.jsonl --out composed.jsonl
head -3 composed.jsonl | jq -r '.embeddingText'
# 기대: "[식품위생법 > 제7장 영업] 제37조(영업허가 등) (3/13) ② ..." 형태
```

### Phase B — 인덱스 단위
```bash
python scripts/legal_index/05_upload.py --index legal-index-v2 --batch 1000
python scripts/legal_index/06_verify.py --index legal-index-v2 --sample 20
# 기대: row count match, sample query score >0.5
```

### Phase C — 검색 품질
```bash
python scripts/legal_index/eval.py --index legal-index-v2 --eval-set data/legal_eval_set.jsonl
# 출력: Recall@5, MRR, nDCG@10, 기존 인덱스와의 diff 표
```

### Phase D — 백엔드 통합
```bash
# 백엔드를 v2 인덱스로 가리키도록 환경변수 변경 후
curl -s -X POST $BACKEND_HOST/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "음식점 영업허가 받으려면 어떤 절차를 밟아야 하나요?"}'
# 기대: 식품위생법 제37조 article 전체가 grounding으로 사용됨, 답변에 조문 인용
```

---

## 7. 비용

| 항목 | 단가 | 추정량 | 비용 |
|------|------|--------|------|
| Embedding (text-embedding-3-small) | $0.02 / 1M tokens | ~800K tokens (3,996 chunks × 200 tokens 평균) | **~$0.02** |
| 국가법령정보센터 메타 보강 API | 무료 | 31 법령 | $0 |
| Azure AI Search S1 (월) | ~$250 | 1 service (gov-index와 공유) | **기존 비용 내** |
| 평가셋 라벨링 (수동) | 인력 1인일 | 100문항 × 5분 | 8시간 |

**1회 재인덱싱 비용 = $0.02 + 라벨링 8시간**.

---

## 8. 리스크

| 리스크 | 영향 | 완화책 |
|--------|------|--------|
| ko.lucene analyzer가 법률 도메인 형용사·복합명사 분리에 약함 | 검색 정확도 저하 | 사용자 사전(synonyms map) 등록 — "영업허가/영업등록/영업신고", "양도/양도양수" 등 동의어 |
| 국가법령정보센터 API rate limit | 메타 보강 단계 정체 | SQLite 캐시 + 단계 분리 (메타 없이도 인덱스는 동작 가능하게 nullable) |
| 평가셋 라벨 편향 | 평가 신뢰성 저하 | 2인 라벨 + 불일치 시 토론, 커버리지(카테고리별 분포) 명시 |
| 표·서식 이미지 정보 손실 | 일부 시행령(부가세 영세율, 사업장 범위 등) 답변 품질 저하 | hasTable=True인 article은 응답 시 "본 조항은 표를 포함하므로 [원문 링크] 참조" 자동 안내 |
| 인덱스 v1→v2 전환 중 운영 중단 | 사용자 검색 실패 | v2 빌드·검증 완료 후 alias 스왑(blue-green). 환경변수만 변경하면 즉시 rollback 가능 |

---

## 9. 다음 액션 (실행 트리거 시)

1. 평가셋 100문항 라벨링 워크스트림 시작 (8시간) — 가장 큰 병목
2. `scripts/legal_index/` 6단계 스크립트 PoC 작성 (배치 1: 개인정보 보호법 292개로 dry-run)
3. 신규 구독 Azure AI Search service 프로비저닝 (Azure 이전 기획안 Phase 0와 통합)
4. v2 인덱스 빌드 → 평가 → 통과 시 백엔드 환경변수 swap
5. 성공 시 동일 패턴을 `gov-programs-index`(NAM2)에도 적용 (별도 기획)

---

## 10. 비포함 (의도적 제외)

- **법령 커버리지 확장**: 30개 법령 외 추가 수집은 별도 도메인 갭 분석 워크스트림으로 분리.
- **대화형 follow-up용 별도 인덱스**: 본 기획은 retrieval만 다룸. 응답 생성 프롬프트 튜닝은 별건.
- **gov-programs-index 재빌드**: 동일 원칙 적용 가능하나 소스 데이터 구조가 다르므로 별도 기획 필요.
- **다국어 검색**: 한국어 단일.
