# 의존성 전반 업데이트 플랜

## Context

현재 `integrated_PARK/requirements.txt`와 루트 `requirements.txt` 간에 패키지 불일치가 존재하며, 일부 패키지는 새 버전이 출시되었을 가능성이 있다. 프론트엔드(`frontend/package.json`)도 일부 패키지가 caret 범위로 느슨하게 관리되고 있다. 이번 업데이트의 목적은 최신 안정 버전으로 올리고 두 requirements.txt 파일 간 일관성을 확보하는 것이다.

---

## 현황 파악 (발견된 불일치)

### integrated_PARK/requirements.txt에는 있으나 루트 requirements.txt에는 없음
| 패키지 | 버전 | 용도 |
|--------|------|------|
| `azure-cosmos` | 4.9.0 | 세션 저장소 |
| `azure-storage-blob` | 12.25.1 | 로그 영구 저장 |
| `psycopg2-binary` | 2.9.9 | PostgreSQL (상권 에이전트) |
| `chardet` | 5.2.0 | 문자 인코딩 감지 |

### 루트 requirements.txt에는 있으나 integrated_PARK/requirements.txt에는 없음
| 패키지 | 버전 | 담당팀 |
|--------|------|--------|
| `azure-functions` | 1.21.3 | NAM |
| `starlette` | 0.46.2 | CHOI |
| `mcp` | 1.26.0 | CHOI |
| `pyyaml` | 6.0.2 | CHANG |
| `jupyterlab` | 4.4.1 | CHOI |

---

## 업데이트 전략

### Phase 1: 현재 버전 감사 (outdated 확인)

```bash
# 백엔드
cd integrated_PARK && .venv/bin/pip list --outdated

# 프론트엔드
cd frontend && npm outdated
```

### Phase 2: 백엔드 — integrated_PARK/requirements.txt 업데이트

아래 패키지 그룹별로 최신 안정 버전 확인 후 `==` 고정:

**우선순위 높음 (보안·안정성)**
- `aiohttp` — 보안 패치 빈번
- `openai` — API 변경 잦음
- `fastapi` / `uvicorn[standard]` — 마이너 업데이트
- `azure-identity` / `azure-core` / `azure-search-documents` — Azure SDK 동기화

**우선순위 중간 (기능 업데이트)**
- `semantic-kernel` — SK 팀이 활발히 개발 중, 브레이킹 체인지 주의
- `pydantic` — v2 마이너 업데이트
- `numpy` / `matplotlib` — 마이너 업데이트
- `jinja2` / `requests` / `python-dotenv`

**호환성 주의 패키지**
- `semantic-kernel` ↔ `openai`: SK가 요구하는 openai 최소 버전 확인 필요
  - SK 1.40.0 기준 `openai>=1.0.0` 범위 확인 후 openai 업데이트
- `pydantic` ↔ `fastapi`: FastAPI가 요구하는 pydantic 버전 범위 확인

### Phase 3: 루트 requirements.txt 동기화

integrated_PARK/requirements.txt 업데이트 완료 후:
1. integrated_PARK 전용 패키지(azure-cosmos, azure-storage-blob, psycopg2-binary, chardet)를 루트에 추가 (PARK 섹션 표기)
2. 버전 번호 루트와 통일

### Phase 4: 프론트엔드 — package.json 업데이트

```bash
cd frontend && npm update        # caret 범위 패키지 latest minor로 업데이트
npm outdated                     # 업데이트 후 잔여 outdated 확인
```

주목할 패키지:
- `motion` (12.23.24) — Framer Motion에서 분리된 패키지, 브레이킹 체인지 주의
- `@radix-ui/*` — 여러 패키지 버전 일관성 확인
- `lucide-react` (0.487.0) — 아이콘 이름 변경 가능성

업데이트 후 package-lock.json 재생성 확인.

---

## 수정 대상 파일

| 파일 | 작업 |
|------|------|
| `integrated_PARK/requirements.txt` | 버전 업데이트 + 누락 패키지 없음 확인 |
| `requirements.txt` (루트) | 불일치 패키지 추가, 버전 동기화 |
| `frontend/package.json` | 버전 업데이트 |
| `frontend/package-lock.json` | npm update 후 자동 재생성 |

---

## 검증

```bash
# 1. 백엔드 설치 확인
cd integrated_PARK && .venv/bin/pip install -r requirements.txt

# 2. 백엔드 서버 기동 확인
.venv/bin/python3 api_server.py &
sleep 3
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트"}' | python3 -m json.tool

# 3. 프론트엔드 빌드 확인
cd frontend && npm install && npm run build
```

---

## 주의사항

- `semantic-kernel` 메이저/마이너 업그레이드 시 `kernel_setup.py` API 변경 여부 확인
- `openai` v2.x → v3.x 범프 시 클라이언트 초기화 코드 확인 (`integrated_PARK/kernel_setup.py`)
- `.env` 키는 건드리지 않음
- 업데이트 후 `pip check`로 의존성 충돌 확인
