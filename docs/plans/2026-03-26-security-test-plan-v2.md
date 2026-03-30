# v2 보안 테스트 계획 문서 작성

## 작업 내용

`docs/test-reports/sohobi_security_test_plan_v2_20260326.md` 파일을 Write 도구로 한 번에 작성한다.

## 문서 구성

1. 인계 컨텍스트 — v1 파일 레퍼런스, 이전 세션에서 적용한 7개 수정 항목 요약
2. 재테스트 항목 — v1 FAIL/PARTIAL 케이스 재검증 (TC-03-R, TC-04-R, TC-05-R, TC-06-R, TC-11-R, TC-15-R, TC-18-R, TC-08/12/13-R)
3. 신규 테스트 항목 — 수정 후에도 남은 잔류 취약점 대상 (founder_context 주입, 다단계 에스컬레이션, 2000자 경계, 간접 추출, 도메인 강제 미스매치, sign-off 드래프트 내 JSON 주입 등)
4. 실행 방법 (curl 명령)
5. 합격 기준
