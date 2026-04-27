# Legal AI Search 인덱스 재구축 파이프라인

기획: [docs/plans/2026-04-26-legal-index-rebuild.md](../../docs/plans/2026-04-26-legal-index-rebuild.md)

## 단계별 스크립트

| 순서 | 스크립트 | 입력 | 출력 |
|------|---------|------|------|
| 1 | `01_clean.py` | refined_law_data*.json | cleaned.jsonl |
| 2 | `02_compose_text.py` | cleaned.jsonl | composed.jsonl |
| 3 | `03_enrich_metadata.py` (선택) | composed.jsonl | enriched.jsonl |
| 4 | `04_embed.py` | composed.jsonl 또는 enriched.jsonl | embedded.jsonl |
| 5 | `05_upload.py` | embedded.jsonl | Azure AI Search 인덱스 |
| 6 | `06_verify.py` | (인덱스명) | verification report |

## 평가
- `eval.py`: 평가셋 + 인덱스명 입력 → Recall@5, MRR, nDCG@10 출력
- 평가셋: `data/legal_eval_set.jsonl` (100문항, 라벨링 필요)

## 실행 예시

```bash
# 배치 1·2 통합 클린업
python scripts/legal_index/01_clean.py \
  --in refined_law_data.json refined_law_data_1.json \
  --out artifacts/cleaned.jsonl

# 임베딩 텍스트 구성
python scripts/legal_index/02_compose_text.py \
  --in artifacts/cleaned.jsonl \
  --out artifacts/composed.jsonl

# (선택) 시행일·공포번호 보강 — 국가법령정보센터 API 키 필요
python scripts/legal_index/03_enrich_metadata.py \
  --in artifacts/composed.jsonl \
  --out artifacts/enriched.jsonl

# 임베딩 (Azure OpenAI text-embedding-3-small 1536d)
python scripts/legal_index/04_embed.py \
  --in artifacts/composed.jsonl \
  --out artifacts/embedded.jsonl \
  --batch-size 16

# 인덱스 업로드
python scripts/legal_index/05_upload.py \
  --in artifacts/embedded.jsonl \
  --index legal-index-v2 \
  --create-if-missing

# 검증
python scripts/legal_index/06_verify.py --index legal-index-v2

# 평가
python scripts/legal_index/eval.py \
  --index legal-index-v2 \
  --eval-set data/legal_eval_set.jsonl
```

## 환경변수 (Azure)

- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`
- `AZURE_EMBEDDING_DEPLOYMENT` (기본 `text-embedding-3-small`)
- `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_KEY`
- `LAW_API_KEY` (선택, 03 단계 — 국가법령정보센터 OpenAPI)
