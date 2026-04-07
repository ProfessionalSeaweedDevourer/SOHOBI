# 린트(Lint) 도입 계획

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-04-07 |
| 작성자 | PARK |
| 대상 브랜치 | `PARK` → `main` |
| 우선순위 | 중간 (기능 개발 병행 가능) |

---

## 1. 린트란 무엇인가

**린트(Lint)**는 코드를 실행하지 않고 소스 파일을 정적으로 분석해 문제를 찾아내는 도구다. 이름의 유래는 1970년대 Bell Labs의 C 언어 검사 도구 `lint`로, 옷감의 보풀(lint)을 골라내듯 코드의 잡티를 걷어낸다는 의미에서 비롯됐다.

린트가 찾아내는 문제의 범주:

| 범주 | 예시 |
|------|------|
| **문법 오류** | 닫히지 않은 괄호, 잘못된 들여쓰기 |
| **스타일 위반** | camelCase/snake_case 혼용, 줄 길이 초과 |
| **잠재적 버그** | 선언만 하고 쓰지 않는 변수, 미정의 변수 참조 |
| **보안** | `eval()` 사용, 하드코딩된 자격증명 패턴 |
| **복잡도** | 너무 긴 함수, 과도하게 중첩된 조건문 |

### 린트 vs 테스트

| 구분 | 린트 | 테스트 |
|------|------|--------|
| 실행 여부 | 코드를 실행하지 않음 | 코드를 실제로 실행 |
| 검사 대상 | 형식, 패턴, 스타일 | 동작, 결과값 |
| 속도 | 매우 빠름 (초 단위) | 상대적으로 느림 |
| 커버 범위 | 모든 파일 | 테스트가 작성된 경로만 |

두 도구는 대체 관계가 아니라 보완 관계다.

---

## 2. 잘 됐을 때의 이점

### 2-1. 리뷰어의 부담 감소

코드 리뷰에서 "여기 들여쓰기 맞춰주세요", "변수명 컨벤션이 다릅니다" 같은 스타일 지적이 사라진다. 리뷰어는 로직과 설계에만 집중할 수 있다.

### 2-2. 버그의 조기 발견

```python
# 예시: 사용하지 않는 변수 — 린트가 경고
def get_dong_density(sido, sigg, dong):
    result = dao.query(sido, sigg)   # dong을 쓰지 않음
    return result
```

이런 실수는 테스트를 통과하더라도 런타임에서 엉뚱한 결과를 낸다. 린트는 PR 단계에서 잡아낸다.

### 2-3. 코드베이스 일관성 유지

팀원이 여럿이고 각자 다른 스타일로 짜도, 린트 규칙이 공통 기준을 강제한다. "이 파일은 누가 짰는지 바로 티가 난다"는 상황을 방지한다.

### 2-4. 온보딩 비용 절감

새 팀원이 합류할 때 컨벤션 문서를 읽을 필요 없이, 린트 오류 메시지 자체가 가이드 역할을 한다.

### 2-5. CI 게이트로서의 역할

PR 머지 전 자동으로 실행돼 규칙 위반 코드가 `main`에 들어오는 것을 차단한다.

---

## 3. 이 프로젝트의 현재 상태

### 3-1. 발견된 주요 문제 (지도 파트 중심)

**Python — PEP 8 camelCase 위반:**

| 위치 | 현재 이름 | 올바른 형태 |
|------|----------|-----------|
| `integrated_PARK/map_data_router.py:114` | `getStoresByDong` | `get_stores_by_dong` |
| `integrated_PARK/map_data_router.py:303` | `getDongDensity` | `get_dong_density` |
| `integrated_PARK/map_data_router.py:506` | `getDongCentroids` | `get_dong_centroids` |
| `integrated_PARK/db/dao/mapInfoDAO.py:141` | `searchDong` | `search_dong` |
| `integrated_PARK/realestate_router.py:170` | `def searchDong(...)` | `search_dong` |

**Python — 파일명 컨벤션 위반:**

| 현재 파일명 | 올바른 형태 |
|------------|-----------|
| `db/dao/mapInfoDAO.py` | `db/dao/map_info_dao.py` |
| `db/dao/landmarkDAO.py` | `db/dao/landmark_dao.py` |
| `db/dao/dongMappingDAO.py` | `db/dao/dong_mapping_dao.py` |

**JavaScript — DB 컬럼명이 프론트엔드까지 노출:**

```js
// frontend/src/hooks/map/useDongPanel.js:68
// gu_nm (DB 스키마) 이 guNm 으로 JS 코드에 직접 노출됨
const fetchDongPanel = async (admCd, dongNm, guNm, admNm, mode, qtr) => {
```

`gu_nm`은 DB 내부 컬럼명이다. API 응답에서 `districtName` 등으로 변환해 내보내야 할 것을 그대로 흘려보낸 결과다.

**JavaScript — 축약 불일치:**

| 위치 | 문제 |
|------|------|
| `MapView.jsx:86` | `catFetchTimerRef` (`cat` = category인데 불명확) |
| `MapView.jsx:85` | `prevStorePopupRef` (`prev`의 의미 불명확) |
| `StorePopup.jsx:5` | `CAT_STYLE` (상수명이 축약) |

### 3-2. 현재 린트 설정 현황

- **Python**: 린트 설정 없음 (`.flake8`, `pyproject.toml` ruff 설정 없음)
- **JavaScript**: ESLint 없음 또는 최소 설정
- **CI**: 린트 게이트 없음

---

## 4. 도입 전략: Baseline 방식

### 핵심 원칙

> **기존 코드는 건드리지 않는다. 새 코드부터 강제한다.**

기존 코드에 린트를 한꺼번에 켜면 수백~수천 개의 오류가 터진다. 이걸 한꺼번에 고치려면 기능 개발이 멈추고, 모두 무시하면 린트가 유명무실해진다. Baseline 방식은 이 함정을 피한다.

### 작동 방식

```
1. 린트 config 추가
2. 현재 상태 전체를 baseline으로 스냅샷
   → 기존 위반은 "이미 알고 있음"으로 처리, CI에서 무시
3. 신규 파일 / 신규 코드에서 위반 발생 시 → CI 실패
4. 어떤 파일을 수정하면 → 그 파일의 위반도 함께 정리 (Boy Scout Rule)
```

---

## 5. 실행 계획

### Phase 1 — 설정 추가 (1회성 PR)

**Python: ruff 도입**

ruff는 flake8/isort/pyupgrade를 통합한 Rust 기반 린터로 속도가 매우 빠르다.

```toml
# integrated_PARK/pyproject.toml 에 추가
[tool.ruff]
line-length = 100
select = [
    "E",   # pycodestyle (들여쓰기, 공백)
    "F",   # pyflakes (미사용 import, 미정의 변수)
    "N",   # pep8-naming (snake_case 강제)
    "I",   # isort (import 정렬)
]
exclude = [".venv", "tests/"]

[tool.ruff.per-file-ignores]
# 기존 파일 baseline — 나중에 파일 단위로 제거
"db/dao/mapInfoDAO.py" = ["N802", "N803"]
"db/dao/landmarkDAO.py" = ["N802", "N803"]
"map_data_router.py" = ["N802", "N803"]
"realestate_router.py" = ["N802", "N803"]
```

**JavaScript: ESLint 도입**

```json
// frontend/.eslintrc.json
{
  "env": { "browser": true, "es2021": true },
  "extends": ["eslint:recommended", "plugin:react/recommended"],
  "rules": {
    "camelcase": ["warn", { "properties": "never" }],
    "no-unused-vars": "warn",
    "prefer-const": "error"
  }
}
```

**CI 게이트 추가:**

```yaml
# .github/workflows/lint.yml
name: Lint
on: [pull_request]
jobs:
  python-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check integrated_PARK/

  js-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd frontend && npm ci && npx eslint src/
```

### Phase 2 — Boy Scout Rule (진행 중 적용)

파일을 수정할 때마다 해당 파일의 위반을 같이 정리한다.

```
파일 수정 → ruff check 해당파일 → 위반 수정 → 커밋
예: refactor: map_data_router 함수명 snake_case 변환
```

`pyproject.toml`의 `per-file-ignores`에서 해당 파일 항목을 제거하는 것이 완료 기준이다.

### Phase 3 — API 응답 레이어 정리 (별도 PR)

`guNm`, `dongNm` 등 DB 컬럼명이 프론트까지 노출된 문제는 백엔드 응답 직렬화 시점에서 해결한다.

```python
# 예시: map_data_router.py 응답 변환 추가
return {
    "districtName": row["gu_nm"],   # DB 컬럼명 은닉
    "dongName":     row["adm_nm"],
    "admCode":      row["adm_cd"],
}
```

DB 스키마는 **건드리지 않는다.** 마이그레이션 비용이 이득을 초과한다.

### Phase 4 — 레거시 파일 일괄 정리 (조용한 시점)

기능 개발 동결 시점에 `per-file-ignores`에 남아있는 항목을 전부 정리하는 PR 1개를 올린다. `integrated_PARK` 폴더 리네임 작업과 묶어서 진행하면 구조 변경 PR을 최소화할 수 있다.

---

## 6. 완료 기준

| 항목 | 완료 조건 |
|------|----------|
| Python 린트 | `ruff check integrated_PARK/` 새 파일 위반 0개 |
| JS 린트 | `eslint src/` 신규 파일 위반 0개 |
| CI 게이트 | PR 머지 전 lint 워크플로우 통과 필수 |
| API 레이어 | 프론트엔드에서 `gu_nm`, `adm_nm` 등 DB 컬럼명 직접 참조 0개 |
| 레거시 정리 | `per-file-ignores` 항목 전부 제거 |

---

## 7. 관련 맥락

- `integrated_PARK` → `backend` 폴더 리네임 논의: 기능 개발 동결 시점에 Phase 4와 묶어서 진행 권장
- Boy Scout Rule을 팀 전체 PR 체크리스트에 추가할 것을 권장 (`.github/pull_request_template.md`)
