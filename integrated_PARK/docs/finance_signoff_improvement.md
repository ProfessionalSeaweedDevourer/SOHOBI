# Finance Agent Sign-off 개선 보고서

**작성일**: 2026-03-12
**대상 폴더**: `integrated_PARK/`
**관련 파일**:
- `plugins/finance_simulation_plugin.py`
- `agents/finance_agent.py`
- `prompts/signoff_finance/evaluate/skprompt.txt`

---

## 1. 배경 — 개선 전 상황

### 증상

`/api/v1/query` 엔드포인트에 재무 질문을 보내면, 응답 품질에 무관하게 항상 `status: escalated` 가 반환되었다.

```
status: escalated | domain: finance | retry_count: 3
message: "재시도 3회 초과. 마지막 거부 이유: 응답에 사용된 시뮬레이션의 구체적인 가정 조건을 설명하고,
          예측의 불확실성에 관련된 더 구체적인 정보 또는 신뢰 구간을 제공하는 문구를 추가하세요."
```

### 개선 전 실제 API 출력 (전문)

테스트 질문: `"월 매출 700만원, 원가 200만원, 급여 250만원 수익 시뮬레이션"`

```json
{
  "request_id": "d0b1cd3d",
  "status": "escalated",
  "domain": "finance",
  "draft": "[사용자 질문]\n월 매출 700만원, 원가 200만원, 급여 250만원 수익 시뮬레이션\n\n[에이전트 응답]\n귀하의 사업 시뮬레이션 결과에 따르면, 평균 월 순이익은 약 2,005,269원으로 나타났습니다. 손실 발생 확률이 0.0%로 계산되었지만, 이는 시뮬레이션의 결과일 뿐 실제 사업 환경에서는 다양한 변수로 인해 변동이 있을 수 있습니다. 따라서 예측의 불확실성을 고려하여 신중하게 해석하는 것이 중요합니다.\n\n사업 가능성을 평가할 때, 다음과 같은 요소를 고려할 수 있습니다:\n\n**기회 요인:**\n- **안정적인 수익성:** 평균 월 순이익이 긍정적으로 나타났습니다. 이는 사업이 지속적으로 수익을 창출할 가능성을 시사합니다.\n- **손실 발생 확률:** 시뮬레이션에서는 손실 발생 확률이 0%로 나타났지만, 이는 이론적인 결과일 수 있으므로 실제 운영에서는 다양한 리스크를 고려해야 합니다.\n\n**위험 요인:**\n- **시장 변동성:** 시장 상황의 변화, 경쟁 증가, 소비자 선호 변화 등이 사업에 영향을 미칠 수 있습니다.\n- **비용 증가 가능성:** 원가나 급여가 예상보다 증가할 경우 순이익이 감소할 수 있습니다.\n\n**시나리오 분석:**\n- **낙관적 시나리오:** 시장 상황이 호전되고 비용이 안정적으로 유지될 경우, 순이익이 더욱 증가할 수 있습니다.\n- **기본 시나리오:** 현재 시뮬레이션 결과를 바탕으로 한 안정적인 수익 창출이 예상됩니다.\n- **비관적 시나리오:** 시장 불확실성이나 비용 증가로 인해 순이익이 감소할 수 있으며, 예기치 않은 손실이 발생할 가능성도 있습니다.\n\n**리스크 경고:**\n모든 사업에는 불확실성과 리스크가 존재합니다. 시뮬레이션 결과는 참고 자료일 뿐이며, 실제 사업 운영에서는 다양한 외부 요인과 내부 요인을 고려해야 합니다. 따라서 투자 결정을 내리기 전에 충분한 시장 조사와 리스크 평가가 필요합니다.\n\n이 정보는 투자 권유가 아닌 참고용으로 제공되는 것이며, 사업 운영에 대한 최종 결정은 경영자의 판단에 따라 이루어져야 합니다.",
  "retry_count": 3,
  "message": "재시도 3회 초과. 마지막 거부 이유: 응답에 사용된 시뮬레이션의 구체적인 가정 조건을 설명하고, 예측의 불확실성에 관련된 더 구체적인 정보 또는 신뢰 구간을 제공하는 문구를 추가하세요."
}
```

---

## 2. 원인 분석

### Sign-off 루브릭 구조

`prompts/signoff_finance/evaluate/skprompt.txt`는 두 가지 금융 도메인 항목에서 계속 탈락했다:

| 코드 | 항목 | 탈락 이유 |
|---|---|---|
| **F3** | 가정 전제 언급 존재 여부 | 시뮬레이션 입력값(월매출·원가·급여)이 응답 본문에 명시되지 않음 |
| **F4** | 불확실성 언급 존재 여부 | "다양한 변수로 인해 변동이 있을 수 있다"는 정성적 표현만 있고, 신뢰구간·표준편차 등 정량적 수치가 없음 |

### 구조적 버그 위치

**`finance_agent.py` — `_EXPLAIN_PROMPT`**

```python
# 개선 전: 시뮬레이션 결과 2개만 LLM에 전달
_EXPLAIN_PROMPT = """다음은 창업 재무 시뮬레이션 결과입니다:
- 평균 월 순이익: {avg_profit:,}원
- 손실 발생 확률: {loss_prob:.1%}
...
```

`_EXPLAIN_PROMPT`에 시뮬레이션 **입력 파라미터**(매출·원가·급여 등)가 포함되지 않아서,
LLM은 어떤 가정 조건으로 계산했는지 알 수 없었다.
또한 시뮬레이션 플러그인이 평균값과 손실확률만 반환하여, 신뢰구간을 작성하는 것이 불가능했다.

**`plugins/finance_simulation_plugin.py` — `monte_carlo_simulation` 반환값**

```python
# 개선 전: 통계량 2개만 반환
return {"average_net_profit": round(avg), "loss_probability": round(loss_prob, 4)}
```

10,000회 시뮬레이션을 수행하면서도 표준편차·백분위수를 계산하지 않아,
LLM이 구체적인 신뢰구간을 응답에 포함시킬 수 없었다.

---

## 3. 절차별 개선 사항

### 개선 1 — `FinanceSimulationPlugin.monte_carlo_simulation` 통계량 확장

`plugins/finance_simulation_plugin.py`

**변경 전**
```python
avg = sum(results) / iterations
loss_prob = sum(1 for r in results if r < 0) / iterations
return {"average_net_profit": round(avg), "loss_probability": round(loss_prob, 4)}
```

**변경 후**
```python
avg = sum(results) / iterations
loss_prob = sum(1 for r in results if r < 0) / iterations
sorted_results = sorted(results)
std = math.sqrt(sum((r - avg) ** 2 for r in results) / iterations)
p5  = sorted_results[int(iterations * 0.05)]
p95 = sorted_results[int(iterations * 0.95)]
return {
    "average_net_profit": round(avg),
    "loss_probability":   round(loss_prob, 4),
    "std_profit":         round(std),          # 표준편차 — 변동성 지표
    "p5_net_profit":      round(p5),           # 하위 5% — 비관 시나리오 기준
    "p95_net_profit":     round(p95),          # 상위 95% — 낙관 시나리오 기준
}
```

반환 키가 2개 → 5개로 확장되었으며, 90% 신뢰구간 (`p5` ~ `p95`)과 표준편차를 통해
시뮬레이션의 통계적 불확실성을 정량적으로 표현할 수 있게 되었다.

---

### 개선 2 — `_EXPLAIN_PROMPT`에 가정 조건과 신규 통계량 전달

`agents/finance_agent.py`

**변경 전**
```python
explain_prompt = _EXPLAIN_PROMPT.format(
    avg_profit=sim_result["average_net_profit"],
    loss_prob=sim_result["loss_probability"],
    question=question,
)
```

**변경 후** — 가정 조건 문자열 구성 후 전달
```python
# 가정 조건 문자열 구성
rev = variables.get("revenue", [])
rev_str = f"{rev[0]:,}원" if len(rev) == 1 else f"{min(rev):,}~{max(rev):,}원 (복수 시나리오)"
assumption_lines = [
    f"- 월매출: {rev_str} (±10% 정규분포 가정)",
    f"- 원가: {variables.get('cost', 0):,}원 (±10% 정규분포 가정)",
    f"- 급여: {variables.get('salary', 0):,}원",
]
if variables.get("rent"):  assumption_lines.append(f"- 임대료: {variables['rent']:,}원")
if variables.get("admin"): assumption_lines.append(f"- 관리비: {variables['admin']:,}원")
if variables.get("fee"):   assumption_lines.append(f"- 수수료: {variables['fee']:,}원")
assumption_lines.append(f"- 세율: {variables.get('tax_rate', 0.2):.0%}")
assumptions = "\n".join(assumption_lines)

explain_prompt = _EXPLAIN_PROMPT.format(
    assumptions=assumptions,
    avg_profit=sim_result["average_net_profit"],
    std_profit=sim_result["std_profit"],
    p5=sim_result["p5_net_profit"],
    p95=sim_result["p95_net_profit"],
    loss_prob=sim_result["loss_probability"],
    question=question,
)
```

---

### 개선 3 — `_EXPLAIN_PROMPT` 내용 확장

**변경 전**
```
다음은 창업 재무 시뮬레이션 결과입니다:
- 평균 월 순이익: {avg_profit:,}원
- 손실 발생 확률: {loss_prob:.1%}
```

**변경 후**
```
다음은 창업 재무 시뮬레이션 결과입니다.

[시뮬레이션 가정 조건]
{assumptions}

[시뮬레이션 결과 — 10,000회 몬테카를로]
- 평균 월 순이익: {avg_profit:,}원
- 표준편차: {std_profit:,}원
- 90% 신뢰구간: {p5:,}원 ~ {p95:,}원  (하위 5% ~ 상위 95%)
- 손실 발생 확률: {loss_prob:.1%}

위 결과를 바탕으로 사업 가능성을 설명하세요.
- 응답 첫 단락에 위의 가정 조건(월매출, 원가, 급여 등)을 명시하세요.
- 신뢰구간과 표준편차를 언급하여 예측의 불확실성을 구체적으로 설명하세요.
...
```

LLM에게 가정 조건을 **첫 단락에 명시**하도록 지시하고,
신뢰구간·표준편차를 프롬프트에 직접 제공함으로써 정량적 불확실성 표현을 강제했다.

---

## 4. 개선 효과

### 정량 비교

| 지표 | 개선 전 | 개선 후 |
|---|---|---|
| `status` | `escalated` | **`approved`** |
| `retry_count` | 3 (최대치 초과) | 1~2 |
| Sign-off F3 (가정 전제) | 항상 탈락 | 통과 |
| Sign-off F4 (불확실성) | 항상 탈락 | 통과 |
| 시뮬레이션 반환 통계량 | 2개 | **5개** |
| LLM에 전달되는 시뮬레이션 정보 | 2개 수치 | 가정 조건 + 5개 통계량 |

### 개선 후 실제 API 출력 (전문)

테스트 질문: `"월 매출 700만원, 원가 200만원, 급여 250만원 수익 시뮬레이션"`

```json
{
  "request_id": "a5b5b58c",
  "status": "approved",
  "domain": "finance",
  "draft": "[사용자 질문]\n월 매출 700만원, 원가 200만원, 급여 250만원 수익 시뮬레이션\n\n[에이전트 응답]\n시뮬레이션을 통해 창업의 재무적 가능성을 평가하기 위해 다음과 같은 가정 조건을 설정했습니다: 월매출은 7,000,000원으로 ±10%의 정규분포를 따르며, 원가는 2,000,000원으로 ±10%의 정규분포를 따릅니다. 급여는 2,500,000원이며, 세율은 20%로 설정되었습니다.\n\n시뮬레이션 결과에 따르면, 평균 월 순이익은 1,991,280원이며, 표준편차는 590,904원입니다. 이는 순이익이 평균적으로 이 범위 내에서 변동할 수 있음을 의미합니다. 또한, 90% 신뢰구간은 1,012,884원에서 2,965,805원으로 나타났습니다. 이는 시뮬레이션 결과의 불확실성을 보여주며, 이 범위 내에서 순이익이 발생할 가능성이 높음을 시사합니다.\n\n손실 발생 확률이 0.0%로 나타났지만, 이는 시뮬레이션의 결과일 뿐 실제 사업 환경에서는 다양한 변수로 인해 손실이 발생할 가능성이 존재합니다. 따라서, 비관적인 시나리오에서는 예상치 못한 비용 증가나 매출 감소로 인해 손실이 발생할 수 있음을 경고합니다.\n\n위험 요인으로는 시장 변동성, 예상치 못한 비용 증가, 경쟁 심화 등이 있으며, 기회 요인으로는 매출 증가 가능성, 비용 절감 전략, 시장 확장 등이 있습니다.\n\n낙관적인 시나리오에서는 매출이 증가하고 비용이 안정적으로 유지되어 높은 순이익을 기대할 수 있습니다. 기본 시나리오에서는 평균적인 매출과 비용을 유지하며 안정적인 수익을 기대할 수 있습니다. 비관적인 시나리오에서는 매출 감소와 비용 증가로 인해 수익이 감소하거나 손실이 발생할 수 있습니다.\n\n이 정보는 투자 권유가 아닌 정보 제공을 목적으로 하며, 경영자가 사업 결정을 내릴 때 참고할 수 있는 자료로 활용하시길 바랍니다. 사업 환경의 불확실성을 항상 고려하여 신중한 판단을 하시기 바랍니다.",
  "retry_count": 1,
  "message": ""
}
```

### 응답 내용 비교 (핵심 차이)

| 항목 | 개선 전 | 개선 후 |
|---|---|---|
| 가정 조건 명시 | 없음 | "월매출 7,000,000원, ±10% 정규분포, 원가 2,000,000원, 세율 20%" |
| 불확실성 표현 | "다양한 변수로 인해 변동이 있을 수 있다" (정성적) | "표준편차 590,904원, 90% 신뢰구간 1,012,884원 ~ 2,965,805원" (정량적) |
| 손실 확률 | 0%라는 수치만 언급 | 0%지만 실제 손실 가능성 경고 포함 |

---

## 5. 한계 및 추가 개선 여지

- **`retry_count`가 1~2로 잔존**: 루브릭을 1회 통과하지 못하는 경우가 있다. LLM 응답의 확률적 특성(temperature=0.3)에 의한 것으로, 완전 해결을 위해서는 temperature를 0으로 낮추거나 프롬프트를 추가 강화할 수 있다.
- **복수 매출 시나리오 미검증**: revenue 리스트에 여러 값을 넣는 케이스(예: `[5000000, 7000000, 9000000]`)의 응답 품질은 별도 테스트가 필요하다.
- **초기 투자 회수 흐름 미테스트**: `initial_investment` 파라미터 포함 시 `[투자 회수 전망]` 섹션 품질은 별도 검증이 필요하다.
