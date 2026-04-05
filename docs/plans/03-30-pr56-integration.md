# PR#56 변경 사항 통합본 반영 계획

## Context

PR#56 (CHOI2 브랜치)이 main에 머지되면서 두 영역에 중요 기능이 추가됐다:
1. **TERRY/p02_frontEnd_React** — ChatPanel에 대화 맥락 기억 + 지도 하이라이트 연동, MapView에 `handleHighlightArea`
2. **CHOI/locationAgent_DB** — API 응답에 `adm_codes` 포함, 지역·업종 정규화 확장

이 변경들은 `frontend/`(통합 프론트) 및 `integrated_PARK/agents/location_agent.py`(통합 백엔드)에는 반영되지 않았다.
본 플랜은 이 두 파일을 업데이트해 PR#56의 핵심 기능을 통합본에 적용한다.

---

## 수정된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `integrated_PARK/agents/location_agent.py` | `analyze()`, `compare()`, `generate_draft()` 반환을 `{draft, adm_codes, type}` dict로 변경 |
| `integrated_PARK/orchestrator.py` | dict에서 `adm_codes`, `analysis_type` 추출 → `complete` 이벤트에 포함 (run/run_stream 양쪽) |
| `frontend/src/components/map/MapView.jsx` | `handleHighlightArea()` 추가 (OL extent 활용), `<ChatPanel onHighlightArea>` prop 전달 |
| `frontend/src/components/map/ChatPanel.jsx` | `onHighlightArea` prop 수신, `lastLocationRef`/`lastBusinessRef` 대화 맥락, 자동 보완 로직 |

---

## 구현 요약

### 백엔드

`repository.py`의 기존 `_get_adm_codes(location)` 메서드(AREA_MAP 조회)를 직접 활용.
`analyze()`, `compare()` 모두 dict 반환으로 변경:
```python
return {"draft": analysis, "adm_codes": adm_codes, "type": "analyze"}
```

`generate_draft()` → `result["draft"]`/`result["adm_codes"]` 추출 후 retry 적용, 최종 dict 반환.

`orchestrator.py` — 기존 finance 패턴 (`isinstance(raw, dict)` 분기) 확장:
```python
adm_codes = raw.get("adm_codes", [])
analysis_type = raw.get("type", "")
```
→ `complete` 이벤트에 `adm_codes`, `analysis_type` 포함.

### 프론트엔드

**MapView.jsx**: `handleHighlightArea(admCodes)` 추가.
- AREA_MAP adm_cd 매칭하는 폴리곤 → `DONG_STYLE_SELECTED` 적용
- `extendExtent` + `createEmptyExtent`로 바운딩 박스 계산 → `view.fit()`으로 자동 이동

**ChatPanel.jsx**: 3가지 변경:
1. `onHighlightArea` prop 추가
2. `lastLocationRef`, `lastBusinessRef` ref — complete 이벤트 후 AREA_KEYWORDS/BIZ_LIST로 추출하여 저장
3. 자동 보완 (`handleSend` 내):
   - 지역 없음 + 업종 있음 + lastLocation → `"${lastLocation} ${text} 상권 분석해줘"`
   - 지역 있음 + 업종 없음 + lastBusiness → `"${text} ${lastBusiness} 상권 분석해줘"`

---

## 검증 방법

1. **백엔드 단독 테스트**:
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/stream \
     -H "Content-Type: application/json" \
     -d '{"question": "홍대 카페 상권 분석해줘"}' \
     --no-buffer | grep '"event"'
   ```
   → `complete` 이벤트에 `"adm_codes": [...]` 비어있지 않은 배열 확인

2. **프론트엔드 통합 테스트**:
   - `npm run dev` 실행 후 `/map` 접속
   - 채팅에 "홍대 카페 상권 분석해줘" 입력
   - 분석 결과 후 홍대 행정동 폴리곤 강조 + 지도 자동 이동 확인
   - 이어서 "잠실은?" 입력 → `lastBusiness("카페")` 보완되어 "잠실 카페" 쿼리 발송 확인

3. **edge case**:
   - `adm_codes` 빈 배열 → 기존 하이라이트 초기화
   - 비교 분석 → `analysis_type === "compare"` → 하이라이트 초기화

---

## 제외 사항 (향후 Phase)

- DB 쿼리 병렬화 (`asyncio.gather`) — 인계 문서 Phase 3
- AREA_MAP / INDUSTRY_CODE_MAP 확장 (CHOI 65개 유사어) — 별도 PR
- Phase 2: `ResponseCard.jsx` deeplink (`/map?adm_cd=...`) — 인계 문서 Phase 2
