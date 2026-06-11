# 신규 테넌트 cutover 사전 적재 완료 세션 인수인계

## 세션 요약

2026-06-11 cutover 잔여 작업 전수 실측 후, 라이브 무영향 작업(R1 secrets·기동 / R2 모델 배포 / R3 데이터 사전 적재 / R5 budget)을 모두 실행 완료. 신규 환경은 **데이터 적재 + 풀 E2E(chat·location grade A) 통과** 상태. 남은 것은 R4(SWA 재생성)·R6(D-day 전환)과 Bicep drift 해소.

## 완료 내역

| 작업 | 결과 |
|------|------|
| OpenAI 모델 3종 배포 | gpt-5.4-mini(GS 10) + embedding small(GS 10) + large(Std 10), quota 전 모델 limit 1000 승인 확인 |
| backend secrets·env 복원 | 구 prod env 52종 미러링 + 신규 endpoint 치환. rev Healthy, /health 200 |
| RBAC 부여 (CLI, IaC 미반영) | backend → Storage Blob Data Contributor(sohobiprodlogs) + Cognitive Services OpenAI User(sohobi-prod-openai) |
| PG 데이터 | 11 tables / 3,133,752 rows 이전 완료 (dump 44s + restore 161s, libpq 18.3 사용) |
| Cosmos 데이터 | 6 컨테이너 4,728 docs 이전 완료 |
| Blob 로그 | 3종 AppendBlob로 이전 + 신규 로그 병합, append 연속성 검증 |
| Budget | sohobi-prod-monthly ₩60,000/월, Actual 50/80/100% + Forecast 100% |
| PR #365 | OPEN — 모델 배포 + budget Bicep. 검증 코멘트 첨부 완료 |

## 결정 사항 (이 세션)

- **도메인(sohobi.net, 구 sub App Service Domain)은 당분간 구 sub 유지** — 고정 비용 회피. 문제 발생 시 별도 이전 (autoRenew=false, 만료 2027-03-29 주의)
- 호출량 가드는 3중(배포 capacity 10K TPM / backend rate limit / budget 알람)으로 충분 판단

---
<!-- CLAUDE_HANDOFF_START
branch: main
pr: 365 (OPEN — 머지 대기)
prev: 2026-04-27-azure-tenant-foundation-handoff.md

[unresolved]
- HIGH infra/bicep — Bicep deploy가 Container App secrets/env(CLI 주입 52종)를 19종으로 롤백시키는 drift. 이번 세션 rev7 ActivationFailed 실사고. 해소 전 모든 Bicep deploy 후 secrets/env 재적용 필수. 해결 방향: secrets를 Bicep secrets 블록(또는 KeyVault ref)로 코드화
- MED R4 — 신규 sub에 SWA 재생성 + GitHub Actions 연결 + frontend VITE_API_URL 신규 backend로 (custom domain 바인딩은 D-day에 구 sub DNS A/TXT 변경과 함께)
- MED R6 — D-day 실행 (docs/runbooks/azure-cutover.md). 데이터 사전 적재 끝났으므로 증분만: PG는 사실상 정적, Cosmos --since, Blob tail
- LOW 도메인 — sohobi.net autoRenew=false / 만료 2027-03-29 / 구 sub 소속. 2027-01 전 갱신 또는 transfer-out 결정 필요
- LOW legal-index가 choi 개인 계정(choi-search) 의존 (PR #363) — pgvector 전환(PR #340 Phase A-C)으로 해소 예정
- LOW PG nightly cron이 신규 PG도 정지함 — D-day 전 사전 적재 데이터는 영향 없으나 야간 검증 작업 시 Stopped 가능성 인지

[decisions]
- 도메인 구 sub 유지 (고정비 회피). DNS·SWA cutover는 구 sub DNS zone 레코드 변경으로 처리
- backend env 복원 전략: 구 prod env 전체 미러링 + 신규 endpoint 치환 (P3 Bicep 19종은 불충분 — GOOGLE_*, AZURE_SIGNOFF_*, GOV_*, JWT_* 등 누락이 ActivationFailed 원인이었음)
- errors.jsonl은 구 이력 + 신규 엔트리 병합, AppendBlob 타입 필수 (BlockBlob이면 logger append_block 실패)
- PARK user 임시 RBAC(Cosmos Data Contributor, Blob Reader/Contributor)는 D-day 증분 import에 재사용하므로 유지

[next]
1. PR #365 리뷰·머지 (머지 후 CI deploy가 또 env drift 일으킴 — 머지 직후 secrets/env 재적용 필수, 위 HIGH 참조)
2. drift 해소 PR: container-app.bicep에 secrets 블록 + 전체 env 코드화 (민감값은 deploy 시 param 또는 KeyVault)
3. R4 SWA: az staticwebapp create (신규 sub, Free) + frontend deploy workflow + VITE_API_URL=신규 FQDN
4. R6 D-day: runbook 따라 증분 sync + 구 sub DNS A/TXT를 신규 SWA로 + smoke + 모니터링
5. cutover 후: pgvector Phase A-C (PR #340), 구 환경 7-14일 cool-down 후 정리

[traps]
- Bicep deploy = Container App secrets/env 전체 롤백 (이번 세션 실사고. 재적용 절차: az containerapp secret set 17종 → az containerapp update --set-env-vars 52종. 값 소스: 구 prod containerapp secret list --show-values + 신규 OpenAI key)
- 신규 backend 처음 응답까지 cold start 30-60s (scale-to-zero) — smoke 폴링 필수
- pg_restore가 PG18 클라이언트 → PG16 서버 시 SET transaction_timeout 에러 2건 무해 (exit 1이어도 데이터 정상)
- 신규 Cosmos/Storage는 PARK user 기본 권한 없음 — data plane 작업 전 역할 부여 필요 (이미 부여됨, 위 decisions)
- pg_stat n_live_tup은 추정치 — row 검증은 COUNT(*) 또는 양쪽 동일 방법 비교
CLAUDE_HANDOFF_END -->
