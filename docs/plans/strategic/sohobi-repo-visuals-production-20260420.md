# SOHOBI 리포지토리 — 경력기술서 시각 자산 제작 지시문

**작성일**: 2026-04-20
**대상**: Claude Code (SOHOBI 리포 연결 세션, 시각 자산 제작 단계)
**목표**: 박주현 경력기술서 통합 버전에 삽입할 SOHOBI 관련 시각 자산 2종(+ 선택 1종)을 제작한다. 본 세션은 문서 빌드를 수행하지 않으며, 별도 통합 빌드 세션에서 GRIP 측 산출물과 결합된다.

---

## 입력 자산

- SOHOBI 리포 전체
- SOHOBI 실서비스 로그: `sohobi-logs-queries-2026-04-20.json` (1,112 entries)
  - 사용자가 제공 예정. 루트 또는 `docs/logs/`에 배치

## 시각 자산 제작 원칙

1. 장식 금지. 각 시각은 텍스트 주장의 증빙 또는 압축이어야 한다
2. 스타일 통일: 동일 색상 팔레트(단색 또는 2색), 동일 폰트, 동일 여백
3. 흑백 인쇄 호환
4. 소스 보존: 생성 스크립트·Mermaid 소스는 `assets/source/`에 커밋
5. 라스터(PNG)만 문서 삽입용 최종 산출물로 배포

---

## Figure 1 — SOHOBI 멀티에이전트 시스템 아키텍처

**파일**: `assets/sohobi-architecture.png`
**소스**: `assets/source/sohobi-architecture.mmd` (Mermaid)

### 포함 요소

- 사용자 → Frontend (Azure Static Web App) → Backend (Azure Container Apps)
- Backend 내부 흐름:
  - `domain_router` → Orchestrator → 도메인 에이전트 5종 (admin · finance · legal · location · chat)
  - 각 도메인 에이전트 응답 → **Sign-off Agent (검증 층)** → 사용자
- 데이터 계층 병기:
  - Azure PostgreSQL Flexible Server (공공 데이터·상권)
  - Cosmos DB (PostgreSQL API) — 로그·세션·피드백·체크리스트
  - Azure AI Search (법무 RAG·정부지원사업 매칭)
  - Azure Blob Storage (로그 영구 저장)
- LLM: Azure OpenAI (gpt-5.4-mini) 단일 박스 — 각 에이전트가 연결됨을 표시
- 지도: OpenLayers + VWorld WMS + Kakao Maps + 공공 데이터 (location 에이전트 옆 작은 박스)

### 스타일 지침

- Mermaid `flowchart TB` 또는 `flowchart LR` (가독성 검토 후 선택)
- **Sign-off Agent는 다른 색·다른 모양**으로 구분하여 "최종 관문" 의미 전달 (사각형 대신 육각형 또는 굵은 테두리)
- 과도한 디테일 금지 — 플러그인·세부 서비스는 간략 박스
- 가로 폭 1,600px 이상 렌더링
- PNG 저장 시 투명 배경 대신 흰색 배경 (Word 문서 호환)

### 제작 순서

1. Mermaid 소스 `assets/source/sohobi-architecture.mmd` 작성
2. `mmdc` CLI로 PNG 렌더링: `mmdc -i sohobi-architecture.mmd -o sohobi-architecture.png -w 1600 -b white`
3. 해상도·가독성 검증
4. Sign-off 박스가 한눈에 "검증 층"으로 읽히는지 확인

### 캡션

- **국문**: Figure 1. SOHOBI 멀티에이전트 시스템 아키텍처. 5개 도메인 에이전트 응답이 Sign-off Agent에서 최종 검증된 뒤 사용자에게 전달된다.
- **영문**: Figure 1. SOHOBI multi-agent system architecture. Responses from five domain agents pass through the Sign-off Agent for final verification before reaching the user.

---

## Figure 2 — Sign-off Agent 런타임 효과성 차트

**파일**: `assets/sohobi-signoff-performance.png`
**소스**: `assets/source/generate_signoff_chart.py` (matplotlib)

### 데이터 소스

`sohobi-logs-queries-2026-04-20.json` (n=1,112)

### 기준 수치 (스크립트가 계산하여 렌더링)

- Grade 분포: A 83.5% (929), B 5.7% (63), C 10.3% (115), None 0.4% (5)
- Status 분포: approved 89.8% (999), escalated 10.2% (113)
- Retry Count 분포: 0회 86.8% (965), 1회 6.9% (77), 2회 0.8% (9), 3회 5.2% (58), 4회 0.3% (3)
- 재시도 발생률 = 1회 이상 retry = 13.2%

### 차트 구성 (권장: 가로 3분할 subplots)

**파트 1 — Grade 분포 도넛**
- 중앙 텍스트: `n = 1,112`
- 색상: A는 돋보이는 색(녹색 계열 권장), C는 경고색(빨강·주황 계열), B는 중간(노랑), None은 회색

**파트 2 — Status 분포 가로 막대**
- approved 89.8% vs escalated 10.2%
- 각 막대에 수치 라벨 (백분율 + 건수)

**파트 3 — Retry Count 분포 세로 막대**
- 0/1/2/3/4회
- 제목 아래 서브타이틀: "재시도 루프를 통한 품질 복구 13.2%"

### 스타일 지침

- 단일 matplotlib figure, `plt.subplots(1, 3, figsize=(14, 4.5))`
- 해상도 DPI 200
- 전체 타이틀: "Sign-off Agent 런타임 효과성 (실서비스 쿼리 1,112건 기준)"
- 영문 버전 파라미터 지원: `--lang en`으로 영문 타이틀·라벨 재생성 가능하게 구조화
- 폰트: 기본 matplotlib sans-serif. 한글이 깨지지 않도록 `matplotlib.rcParams['font.family']`를 `NanumGothic` 또는 `Malgun Gothic`으로 지정. 환경에 해당 폰트가 없으면 `apt-get install fonts-nanum` 선행

### 스크립트 요구사항

```python
# assets/source/generate_signoff_chart.py
# CLI 인자: --input <json_path> --output <png_path> --lang ko|en
# 기능:
#   1. JSON 로드, 위 지표 계산
#   2. 3-subplot figure 생성
#   3. PNG 저장
# 재실행 가능해야 하며, 로그가 변경되면 자동 재계산
```

### 캡션

- **국문**: Figure 2. Sign-off Agent 실측 성능. 전체 응답의 10.2%를 검증 단계에서 차단하고 13.2%를 재시도 루프로 복구하여 최종 A등급 83.5%를 확보.
- **영문**: Figure 2. Sign-off Agent runtime effectiveness. 10.2% of responses were blocked at the verification stage and 13.2% recovered through the retry loop, securing a final 83.5% A-grade rate.

---

## Figure 3 (선택) — SOHOBI 사용자 화면 스크린샷

**파일**: `assets/sohobi-user-screenshot.png`
**소스**: sohobi.net 공개 페이지 또는 로컬 개발 환경

### 권장 조건

- **우선순위 1**: 도메인 에이전트 응답에 A/B/C 등급 배지가 노출되는 샘플 응답이 보이는 화면
- **우선순위 2**: 랜딩 페이지 또는 5개 도메인 카드 그리드가 보이는 UserChat 초기 화면

### 제작 방법

두 가지 옵션 중 선택:

**옵션 A — Playwright 자동 캡처**:
```python
# assets/source/capture_screenshot.py
# - Playwright로 sohobi.net 접근
# - 특정 샘플 질문 입력 후 응답 대기
# - 등급 배지 노출 확인 후 스크린샷
# - 1600x900 해상도, viewport 지정
```
이 방법은 재현 가능하지만 서버 상태에 의존. 공개 페이지로만 제한 (인증 불필요 범위).

**옵션 B — 사용자 수동 제공**:
- Playwright 자동화가 현실적으로 어려우면, 사용자에게 직접 캡처 요청
- 요청 시 가이드: "1600x900 이상, 등급 배지 보이는 응답 1건, PII 없는 샘플 질문"

### 캡션

- **국문**: Figure 3. SOHOBI 사용자 화면. 도메인 에이전트 응답에 A/B/C 등급 배지가 노출되어 응답 신뢰도를 사용자가 직접 확인할 수 있다.
- **영문**: Figure 3. SOHOBI user interface. A/B/C grade badges are exposed on domain agent responses, allowing users to directly verify response reliability.

### 선택 처리 방침

- 첫 세션에서 옵션 A를 시도 → 실패 시 옵션 B로 사용자에게 요청
- 두 옵션 모두 어려우면 **Figure 3 생략** — 필수 아님

---

## 인수인계 매니페스트 작성

**파일**: `handoff/sohobi-assets-manifest.md`

다음 포맷:

```markdown
# SOHOBI 시각 자산 인수인계 매니페스트

**제작일**: [YYYY-MM-DD]
**제작 세션**: SOHOBI 리포지토리 시각 자산 제작 세션
**수신 세션**: SOHOBI 리포 통합 빌드 세션 (동일 리포)

## 포함 자산

| 파일명 | 소스 | 캡션 (국문) | 캡션 (영문) |
|---|---|---|---|
| sohobi-architecture.png | Mermaid 생성 | [Figure 1 국문 캡션] | [Figure 1 영문 캡션] |
| sohobi-signoff-performance.png | matplotlib 생성 | [Figure 2 국문 캡션] | [Figure 2 영문 캡션] |
| sohobi-user-screenshot.png (선택) | [캡처 방법] | [Figure 3 국문 캡션] | [Figure 3 영문 캡션] |

## 재현 가능성

- Figure 1: `assets/source/sohobi-architecture.mmd` + `mmdc -i ... -o ... -w 1600 -b white`
- Figure 2: `assets/source/generate_signoff_chart.py --input ... --output ... --lang [ko|en]`
- Figure 3: (선택 제작 방법 명시)

## 통합 빌드 세션에 전달할 사항

- 세 PNG 파일(또는 2개 필수 + 1개 선택)을 `assets/` 디렉토리에 배치 완료
- 경력기술서 마크다운 삽입 위치:
  - Figure 1: SOHOBI 프로젝트 블록 도입부
  - Figure 2: SOHOBI "Sign-off Agent 런타임 효과성" bullet 직후 또는 블록 말미
  - Figure 3: 블록 말미 또는 생략
```

---

## 작업 순서 요약

1. **Figure 1 Mermaid 작성·렌더링** → 사용자 확인
2. **Figure 2 matplotlib 차트 생성** → 사용자 확인
3. **Figure 3 시도 (Playwright)** — 실패 시 사용자에게 수동 캡처 요청 또는 생략
4. **인수인계 매니페스트 작성**
5. 세션 종료, 사용자에게 "통합 빌드 세션 시작 가능" 통지

각 Figure 완료 후 사용자 피드백 받은 뒤 다음 Figure 진행. 한 번에 달리지 않는다.

## 절대 금지

- 경력기술서 `.docx`·`.pdf` 빌드 시도 (본 세션 범위 밖 — 통합 빌드 세션에서 수행)
- 인증이 필요한 SOHOBI 페이지(`/my-report`, `/my-logs`, `/dev` 등) 스크린샷 (PII 유출 위험)
- 로그 JSON 원본을 assets/에 복사 (대용량, 시각 자료 아님)
- 과도한 디테일로 Figure 1을 채우기 (읽히지 않는 다이어그램은 음의 자산)

---

**지시문 끝.**
