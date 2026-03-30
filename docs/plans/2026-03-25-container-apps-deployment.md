# Container Apps 배포 잠재 문제 종합 수정 계획

## Context

빌드 대기 중 코드베이스 전수 분석을 통해 Container Apps 배포 시 발생할 수 있는 문제를 사전 파악. 우선순위별로 정리.

---

## 1순위 — NAM 폴더 Docker 이미지 미포함 (기능 파괴)

### 문제

`integrated_PARK/plugins/food_business_plugin.py`:

```python
_NAM_DIR = Path(__file__).parent.parent.parent / "NAM"  # → 레포 루트/NAM/
```

Dockerfile 빌드 컨텍스트가 `integrated_PARK/`이므로 `NAM/` 폴더가 이미지에 없음.
결과: `import overlay_main` → `ModuleNotFoundError`, PDF 생성 완전 불가.

필요한 NAM 파일: `overlay_main.py`, `original.pdf`, `malgun.ttf`

### 수정

`NAM/`의 필요 파일 3개를 `integrated_PARK/nam/`으로 복사하고 경로 수정:

**`integrated_PARK/plugins/food_business_plugin.py`**:

```python
# 변경 전
_NAM_DIR = Path(__file__).parent.parent.parent / "NAM"

# 변경 후
_NAM_DIR = Path(__file__).parent.parent / "nam"
```

파일 복사 (실행 시):

```bash
mkdir -p integrated_PARK/nam
cp NAM/overlay_main.py NAM/original.pdf NAM/malgun.ttf integrated_PARK/nam/
```

**변경 파일:**

- `integrated_PARK/plugins/food_business_plugin.py` — `_NAM_DIR` 경로 1줄 수정
- `integrated_PARK/nam/` 디렉터리 신규 생성 (overlay_main.py, original.pdf, malgun.ttf)

---

## 2순위 — Cosmos DB 이름 불일치 가능성 (세션 소멸)

### 문제

`session_store.py` 기본값: `COSMOS_DATABASE="sohobi"`, `COSMOS_CONTAINER="sessions"`

Container App 환경변수에 이 두 값이 비어 있어 기본값 사용 중. 실제 Cosmos DB 계정(`sohobi-ejp-9638`)에 `sohobi` 데이터베이스와 `sessions` 컨테이너가 존재하는지 확인 필요.

### 수정 (Azure Cloud Shell 확인)

```bash
az cosmosdb sql database list \
  --account-name sohobi-ejp-9638 \
  --resource-group rg-ejp-9638 \
  --query "[].id" -o tsv

az cosmosdb sql container list \
  --account-name sohobi-ejp-9638 \
  --resource-group rg-ejp-9638 \
  --database-name sohobi \
  --query "[].id" -o tsv
```

DB/컨테이너 이름이 다르면:

```bash
az containerapp update \
  --name sohobi-backend \
  --resource-group rg-ejp-9638 \
  --set-env-vars COSMOS_DATABASE=<실제DB명> COSMOS_CONTAINER=<실제컨테이너명>
```

---

## 3순위 — EXPORT_SECRET 미설정 (보안)

`api_server.py`: `EXPORT_SECRET`이 빈 문자열이면 `key=""`로 로그 다운로드 인증 우회 가능.

Container App 환경변수에 임의 값 등록 필요 (Azure 설정, 코드 변경 없음):

```bash
az containerapp secret set \
  --name sohobi-backend \
  --resource-group rg-ejp-9638 \
  --secrets export-secret=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

---

## 4순위 — 기능 저하 (크래시 아님, 참고용)

| 항목 | 현황 | 영향 |
| --- | --- | --- |
| BLOB_LOGS_ACCOUNT 미설정 | 로컬 파일 폴백 | 컨테이너 재시작 시 로그 소멸 |
| AZURE_SEARCH_KEY/ENDPOINT 미설정 | 플러그인 자체 비활성화 | 법령 검색 불가 |
| SEOUL_API_KEY 미설정 | 플러그인 비활성화 | 서울 상권 데이터 없음 |
| PDF 파일 지속성 없음 | 에페머럴 FS | 생성된 PDF 다운로드 불가 |

---

## 실행 순서

1. Cloud Shell: Cosmos DB 이름 확인 → 필요 시 환경변수 업데이트 (즉시)
2. 코드: `food_business_plugin.py` 경로 수정 + `nam/` 디렉터리 추가 → PR
3. Cloud Shell: EXPORT_SECRET 설정 (즉시)
