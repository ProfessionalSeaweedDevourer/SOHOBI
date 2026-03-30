# 방어 패치: 클라이언트 지정 domain 검증

## Context

`/api/v1/query`는 클라이언트가 `domain` 파라미터를 지정하면 LLM 라우터를 완전히 우회한다.
일반 프론트엔드는 항상 `domain: null`을 보내므로 실사용자 영향은 없지만,
직접 API 호출(curl/Postman/악의적 클라이언트)로 법률 질문에 `domain: "finance"`를 넣으면:
- 재무 에이전트가 의미 없는 몬테카를로 시뮬레이션을 실행
- Sign-off가 finance 루브릭(F1~F5)으로만 검증 → 법률 오류 무검사 통과

목표: `domain`이 지정된 경우에도 라우터를 실행하여 불일치 시 라우터 결과로 override하고 보안 로그를 남긴다.

---

## 수정 대상 파일

- `integrated_PARK/api_server.py` — `/api/v1/query` 핸들러 내 도메인 결정 로직 (line 151~156)

---

## 구현 계획

### 변경 전 (api_server.py:151-156)

```python
if req.domain in ("admin", "finance", "legal", "location"):
    domain = req.domain
else:
    classification = await domain_router.classify(req.question)
    domain = classification["domain"]
```

### 변경 후

```python
# 라우터는 항상 실행 (domain 지정 여부와 무관)
classification = await domain_router.classify(req.question)
router_domain = classification["domain"]
router_confidence = classification.get("confidence", 0.0)

if req.domain in ("admin", "finance", "legal", "location"):
    if router_domain != req.domain and router_confidence >= 0.8:
        import logging
        logging.getLogger("sohobi.security").warning(
            "DOMAIN_OVERRIDE client=%r router=%r confidence=%.2f question=%r",
            req.domain, router_domain, router_confidence, req.question[:100],
        )
        domain = router_domain   # 라우터 결과 우선
    else:
        domain = req.domain      # 라우터 확신 부족 → 클라이언트 지정 존중
else:
    domain = router_domain
```

### 핵심 판단 기준

| 상황 | 처리 |
|------|------|
| 클라이언트 domain = None | 라우터 결과 사용 (기존과 동일) |
| 클라이언트 domain 지정, 라우터 일치 | 클라이언트 domain 사용 |
| 클라이언트 domain 지정, 라우터 불일치, confidence ≥ 0.8 | **라우터 domain으로 override + 보안 경고 로그** |
| 클라이언트 domain 지정, 라우터 불일치, confidence < 0.8 | 클라이언트 domain 존중 (라우터 불확실) |

confidence 임계값 0.8:
- 키워드 매칭 결과 = 0.85 → 신뢰 → override
- LLM 결과 가변, 파싱 실패 fallback = 0.3 → 불확실 → 클라이언트 존중

### 성능 영향

프론트엔드는 항상 `domain: null`을 보내므로 **실사용자 요청에 추가 LLM 호출 없음**.
`domain`을 직접 지정하는 경우(개발자/직접 API 호출)에만 라우터가 추가 실행됨.

---

## 검증

```bash
# 1. 법률 질문에 domain: "finance" 강제 지정 → router가 "legal"로 분류하면 override
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "임대차 계약서에 보증금 반환 조항이 없으면 법적으로 어떻게 됩니까?", "domain": "finance"}'
# 기대: domain 응답이 "legal", 서버 로그에 DOMAIN_OVERRIDE 경고 출력

# 2. 재무 질문에 domain: "finance" 지정 → 일치하므로 override 없음
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "월매출 700만원, 임대료 150만원이면 수익이 납니까?", "domain": "finance"}'
# 기대: domain 응답이 "finance", DOMAIN_OVERRIDE 로그 없음

# 3. domain 미지정 (프론트엔드 정상 경로) → 기존과 동일
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "임대차 보증금 반환 문제입니다.", "domain": null}'
# 기대: domain 응답이 "legal"
```
