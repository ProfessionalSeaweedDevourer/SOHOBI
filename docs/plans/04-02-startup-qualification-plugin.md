# 창업 자격 서브 플러그인 구현 계획

## Context

사용자가 구상 중인 업종과 매장 형태를 입력하면, 현재 AdminAgent는 인허가 절차(영업신고·사업자등록 등)만 안내한다. 개업 전 반드시 **취득해야 하는 자격증**과 **수료해야 하는 교육**을 추가로 안내하는 기능이 없다. 이를 기존 AdminAgent의 네 번째 플러그인으로 추가한다.

## 기술 적합성 평가

- **적합**: 기존 `AdminProcedurePlugin` → JSON KB 패턴이 그대로 재사용 가능. 프론트엔드 변경 불필요(마크다운 렌더링으로 처리됨). Sign-off 루브릭 확장도 기존 구조를 따름.
- **주의**: 자격증 데이터는 하드코딩이므로 법령 개정 시 수동 업데이트 필요. JSON에 "출처 일자" 필드 추가로 관리.

---

## 구현 계획

### Step 1 — 데이터 파일 생성
**`integrated_PARK/data/startup_qualifications.json`** (신규)

8개 업종 그룹 초기 커버:

| id | 업종 | 자격/교육 |
|----|------|----------|
| `food_hygiene_mgr` | 일반·휴게음식점, 카페 | 식품위생관리인 교육 (식위법 제48조) — 필수 |
| `haccp_basic` | 식품제조업, 집단급식소 | HACCP 기초 교육 — 권장 |
| `alcohol_sales` | 음식점, 편의점 | 주류 판매 (주세법 제36조) — 참고 안내 |
| `beauty_license` | 미용실, 헤어샵 | 미용사 면허 (공중위생관리법 제6조) — 필수 |
| `nail_skin_cert` | 네일샵, 피부관리실 | 미용사(네일·피부) 면허 — 필수 |
| `hakwon_registration` | 학원, 교습소 | 학원 설립·운영 등록 (학원법 제6조) — 필수 |
| `tobacco_sales` | 편의점, 소매점 | 담배소매인 지정 (담배사업법 제16조) — 필수 |
| `pharmaceutical_sales` | 편의점, 드럭스토어 | 의약외품 판매업 신고 — 해당시 |

각 항목 필드: `id, name, category, business_types[], is_mandatory, law, form, issuing_authority, online, acquisition_method[], duration, cost, validity, notes, source_date`

---

### Step 2 — 플러그인 생성
**`integrated_PARK/plugins/startup_qualification_plugin.py`** (신규)

`AdminProcedurePlugin` 패턴 재사용:

```python
class StartupQualificationPlugin:
    def __init__(self):
        # data/startup_qualifications.json 로드 → id 기반 인덱스

    @kernel_function(
        name="get_startup_qualification",
        description="업종·매장 형태에 따라 개업 전 반드시 취득해야 하는 자격증 및 수료 교육을 조회합니다. 행정 절차(영업신고·보건증 등)가 아닌 '자격증·교육 이수' 관련 질문에 호출하세요."
    )
    def get_startup_qualification(self, query: str) -> str:
        # 1단계: QUALIFICATION_KEYWORD_MAP (자격 직접 키워드) 매칭
        # 2단계: BUSINESS_TYPE_MAP (업종 키워드) 매칭 → is_mandatory 우선 정렬
        # 미매칭: "조회 가능한 업종: ..." 반환
```

키워드 맵 예시:
```python
BUSINESS_TYPE_MAP = {
    "음식점": ["food_hygiene_mgr", "haccp_basic", "alcohol_sales"],
    "카페":   ["food_hygiene_mgr", "haccp_basic"],
    "미용실": ["beauty_license"],
    "네일":   ["nail_skin_cert"],
    "학원":   ["hakwon_registration"],
    "편의점": ["tobacco_sales", "pharmaceutical_sales"],
    ...
}
QUALIFICATION_KEYWORD_MAP = {
    "식품위생관리인": "food_hygiene_mgr",
    "미용사":        "beauty_license",
    "담배소매":      "tobacco_sales",
    ...
}
```

---

### Step 3 — AdminAgent 수정
**`integrated_PARK/agents/admin_agent.py`**

**3-A. import 추가** (line 18 다음):
```python
from plugins.startup_qualification_plugin import StartupQualificationPlugin
```

**3-B. `__init__` 플러그인 등록** (line 78 다음):
```python
if "StartupQualification" not in self._kernel.plugins:
    self._kernel.add_plugin(
        StartupQualificationPlugin(), plugin_name="StartupQualification"
    )
```

**3-C. `SYSTEM_PROMPT` 수정** (line 29, 기존 역할 선언 교체):
```
당신은 한국 소규모 창업자를 위한 행정 절차 및 창업 자격 전문 에이전트입니다.
```

**3-D. `SYSTEM_PROMPT`에 플러그인 지시 추가** (line 38 GovSupport 지시 다음에 삽입):
```
업종별 자격증·수료 교육(미용사 면허, 식품위생관리인, 학원 등록 자격, 담배소매인 지정 등)을
묻는 경우, 반드시 먼저 `StartupQualification-get_startup_qualification` 도구를 호출하여
법령 검증된 Knowledge Base의 정보를 기반으로 응답하십시오.

창업 준비 전반(예: "카페 창업 준비", "미용실 개업 절차")을 묻는 경우,
행정 절차(AdminProcedure)와 자격 요건(StartupQualification) 도구를 모두 호출하여
통합 안내를 제공하십시오.
```

**3-E. 응답 기준 섹션에 추가** (line 46 다음):
```
- 자격증·교육 정보를 포함할 때: 의무/권장 여부, 근거 법령, 발급 기관명을 명시한다
- 자격 유효 기간 및 갱신 교육 필요 여부를 안내한다
```

---

### Step 4 — Sign-off 루브릭 추가
**`integrated_PARK/prompts/signoff_admin/evaluate/skprompt.txt`**

**4-A. line 20~22 코드 목록 업데이트** (Q1, Q2, Q3 추가):
```
C1, C2, C3, C4, C5, A1, A2, A3, A4, A5, Q1, Q2, Q3, SEC1, SEC2, SEC3, RJ1, RJ2, RJ3를 반드시 평가해야 한다.
```
(자가 점검 라인도 동일하게 수정)

**4-B. `[L2 행정 도메인 루브릭]` 섹션과 `[L3 보안 루브릭]` 사이에 L2-Q 섹션 삽입**:
```
[L2-Q 자격 정보 루브릭 — 자격·교육 내용이 없는 응답은 Q1~Q3 모두 자동 passed]
자격·교육 관련 내용이 전혀 없는 응답(순수 행정 절차 문의 응답)은 Q1·Q2·Q3를 모두 passed로 분류한다.
자격·교육 정보가 포함된 경우에만 아래 항목을 평가한다.

- Q1 의무/권장 여부 명시: 자격증·교육이 법령상 의무인지 권장인지 구분하여 안내되어 있으면 통과.
  구분 없이 나열하거나 전혀 언급이 없으면 issues로 분류한다.
- Q2 취득 기관 명시: 자격증·교육 취득(이수) 기관명이 하나 이상 명시되어 있으면 통과.
  기관명이 전혀 없으면 issues로 분류한다.
- Q3 유효 기간·갱신 안내: 자격증·교육의 유효 기간 또는 갱신 교육 필요 여부가 언급되면 통과.
  언급이 없으면 warnings로 분류한다 (issues 아님).
```

---

### Step 5 — signoff_agent.py REQUIRED_CODES 수정
**`integrated_PARK/signoff/signoff_agent.py`, line 19**

```python
REQUIRED_CODES = {
    "admin": {"C1","C2","C3","C4","C5","A1","A2","A3","A4","A5","Q1","Q2","Q3"} | _SECURITY_CODES | _REJECTION_CODES,
    ...
}
```

---

## 변경 파일 요약

| 파일 | 유형 | 변경 규모 |
|------|------|----------|
| `integrated_PARK/data/startup_qualifications.json` | 신규 | ~200줄 JSON |
| `integrated_PARK/plugins/startup_qualification_plugin.py` | 신규 | ~120줄 |
| `integrated_PARK/agents/admin_agent.py` | 수정 | import 1줄 + `__init__` 2줄 + SYSTEM_PROMPT ~12줄 |
| `integrated_PARK/prompts/signoff_admin/evaluate/skprompt.txt` | 수정 | L2-Q 섹션 ~10줄 + 코드 목록 2곳 |
| `integrated_PARK/signoff/signoff_agent.py` | 수정 | line 19: Q1/Q2/Q3 추가 (1줄) |

## 검증 방법

```bash
# 1. 음식점 자격 조회 테스트
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "카페 창업하려는데 자격증이나 교육이 필요한가요?"}'

# 기대: 식품위생관리인 교육 (식위법 제48조), 필수/권장 구분, 발급 기관명 포함

# 2. 미용실 자격 테스트
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "미용실 개업 전 면허가 필요한가요?"}'

# 기대: 미용사 면허 (공중위생관리법 제6조), 한국보건의료인국가시험원 명시

# 3. 순수 행정 절차 질문 — Q1~Q3 자동 passed 확인 (dev mode 스트림)
curl -s -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "영업신고 절차 알려주세요"}' | grep signoff_result

# 기대: Q1·Q2·Q3 모두 passed, A1-A5 정상 평가
```
