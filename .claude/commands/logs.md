백엔드 로그를 조회하고 요약하라.

인자: $ARGUMENTS
- 인자가 없으면 기본값 `type=queries&limit=50` 사용
- 인자 예시: `errors 20` → `type=errors&limit=20`
- 인자 예시: `rejections 100` → `type=rejections&limit=100`

실행 절차:
1. `source integrated_PARK/.env`로 환경변수 로드
2. `curl -s "$BACKEND_HOST/api/v1/logs?<파라미터>" | python3 -m json.tool`
3. 결과를 요약한다:
   - 총 건수, 시간 범위
   - 에러가 있으면 에러 유형별 집계
   - 주목할 패턴 (반복 에러, 느린 응답 등) 강조
4. 상세 필터링이 필요하면 `docs/guides/backend-logs.md` 참조
