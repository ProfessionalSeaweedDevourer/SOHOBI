## 변경 내용 요약

<!-- 이 PR이 무엇을 하는지 1-3줄로 설명 -->

## 체크리스트

### 공통

- [ ] `backend/.env` 내용이 커밋에 포함되지 않았음
- [ ] `frontend/.env.local` 내용이 커밋에 포함되지 않았음

### 백엔드 배포 변경 시 (`backend/**` 수정)

- [ ] `deploy-backend.yml`의 `--set-env-vars` 각 변수를 **개별 따옴표**로 분리했음
  ```yaml
  # 올바른 방법
  --set-env-vars "VAR1=value1" "VAR2=value2"
  # 잘못된 방법 (API 키 오염 사고 원인)
  --set-env-vars "VAR1=value1 VAR2=value2"
  ```

### Azure 환경변수 또는 API 키 변경 시

- [ ] `API_SECRET_KEY` (Azure) ↔ `VITE_API_KEY` (GitHub Secret) 동일 값 확인
- [ ] 키 변경 후 SWA 재빌드 트리거 예정

### 지도 관련 변경 시 (`frontend/src/components/map/**`, `backend/map_data_router.py`)

- [ ] VWorld API 호출 시 `VITE_VWORLD_DOMAIN` 환경변수 사용 (`localhost` 하드코딩 금지)
- [ ] 로컬에서 지적도 레이어 정상 표시 확인

## 테스트

<!-- TC 번호와 결과 기록 -->

| TC | 설명 | 결과 |
| -- | ---- | ---- |
|    |      |      |
