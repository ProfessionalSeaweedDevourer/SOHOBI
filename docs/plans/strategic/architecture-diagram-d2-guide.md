# 아키텍처 다이어그램 제작 지시 (SOHOBI 방식 이식)

**목표**: 프로젝트의 시스템 아키텍처 PNG를 `assets/sohobi-architecture.png` 방식으로 제작한다.

---

## 도구 스택

| 도구 | 용도 | 설치 |
|------|------|------|
| **D2** 0.7+ | 다이어그램 DSL → PNG 렌더링 | `brew install d2` (Mac) 또는 [d2lang.com](https://d2lang.com/tour/install) |
| **ELK 레이아웃** | D2 내장 (별도 설치 불필요) | — |

> **Mermaid는 사용하지 않는다.** 레이아웃 품질과 커스텀 스타일 한계로 D2로 교체한 결정이 SOHOBI에서 검증됨.

---

## 렌더링 명령

```bash
D2_LAYOUT=elk d2 --theme=0 --pad=50 \
  assets/source/architecture.d2 \
  assets/architecture.png
```

| 플래그 | 의미 |
|--------|------|
| `D2_LAYOUT=elk` | ELK 레이아웃 엔진 — 자동 배치 품질 우수 |
| `--theme=0` | 흰 배경 테마 (Word/PDF 문서 삽입 호환) |
| `--pad=50` | 외곽 여백 50px |

---

## D2 소스 템플릿

SOHOBI `assets/source/sohobi-architecture.d2` 를 기반으로 한 재사용 템플릿.  
`[대괄호]` 항목을 대상 프로젝트에 맞게 교체한다.

```d2
title: |md
  # [프로젝트명] 시스템 아키텍처
| {near: top-center}

vars: {
  d2-config: {
    layout-engine: elk
    pad: 50
  }
}

direction: right

# ── 사용자
user: 사용자 {
  shape: person
  style.fill: "#F9FAFB"
  style.stroke: "#374151"
}

# ── 프론트엔드
frontend: "Frontend\n[기술 스택]" {
  style.fill: "#E0F2FE"
  style.stroke: "#0284C7"
  style.border-radius: 8
}

# ── 백엔드 컨테이너 (점선 경계)
backend: "Backend  ·  [배포 환경]" {
  style.fill: "#FFFBEB"
  style.stroke: "#B45309"
  style.stroke-dash: 3
  style.border-radius: 10
  direction: right

  core: "[핵심 컴포넌트]" {
    style.fill: "#FEF3C7"
    style.stroke: "#B45309"
    style.border-radius: 6
  }

  # "최종 관문" 역할 컴포넌트는 육각형 + 강조색으로 구분
  gateway: "[검증·게이트웨이 컴포넌트]" {
    shape: hexagon
    style.fill: "#F59E0B"
    style.stroke: "#78350F"
    style.stroke-width: 4
    style.bold: true
  }
}

# ── 데이터 계층 (점선 묶음)
data: "데이터 계층" {
  style.fill: "#F9FAFB"
  style.stroke: "#6B7280"
  style.stroke-dash: 3
  style.border-radius: 10
  direction: down

  db: "[DB명]" {shape: cylinder; style.fill: "#F3F4F6"; style.stroke: "#4B5563"}
}

# ── 외부 서비스 (cloud shape)
llm: "[LLM / 외부 API]" {
  shape: cloud
  style.fill: "#EDE9FE"
  style.stroke: "#6D28D9"
}

# ── 엣지: 주요 흐름 (실선)
user -> frontend: 요청 {style.stroke-width: 2}
frontend -> backend.core: "API 호출" {style.stroke-width: 2}
backend.core -> backend.gateway: 초안 {style.stroke-width: 2}
backend.gateway -> frontend: 승인 응답 {style.stroke-width: 2; style.stroke: "#B45309"}

# ── 엣지: 재시도·에스컬레이션 루프 (점선 경고색)
backend.gateway -> backend.core: "retry / escalate" {
  style.stroke-dash: 5
  style.stroke: "#DC2626"
}

# ── 엣지: 외부 연계 (점선)
backend.core -> llm {style.stroke-dash: 3; style.stroke: "#6D28D9"}
backend.core -> data {style.stroke-dash: 3; style.stroke: "#4B5563"}
```

---

## 핵심 설계 원칙

| 원칙 | 적용 방법 |
|------|-----------|
| 장식 금지 | 노드당 정보 2줄 이하. 세부 서비스는 묶음 박스 |
| 흰색 배경 | `--theme=0` 플래그로 강제 |
| 색상 체계 | 프론트=파랑(#E0F2FE), 백엔드=노랑(#FFFBEB), 데이터=회색, LLM=보라, 최종관문=주황(#F59E0B) |
| "최종 관문" 강조 | `shape: hexagon` + `style.stroke-width: 4` |
| 재시도 루프 가시화 | `style.stroke-dash: 5` + 빨강(#DC2626) |
| 소스 보존 | `.d2` 원본은 `assets/source/`에 커밋, PNG만 최종 산출물로 배포 |
| 흑백 인쇄 호환 | 모든 색상은 배경 흰색 기준으로 충분한 대비 확보 |

---

## 파일 경로 규칙

```
assets/
  architecture.png          ← 최종 산출물 (PNG만, 문서 삽입용)
  source/
    architecture.d2         ← D2 소스 (재현 가능성 보장용, 커밋 대상)
```

---

## 레퍼런스

- 원본 소스: [`assets/source/sohobi-architecture.d2`](../../assets/source/sohobi-architecture.d2)
- 원본 산출물: [`assets/sohobi-architecture.png`](../../assets/sohobi-architecture.png) (6578×2196px)
- 제작 경위: [`handoff/sohobi-assets-manifest.md`](../../handoff/sohobi-assets-manifest.md)
- D2 공식 문서: [d2lang.com](https://d2lang.com)
