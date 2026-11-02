## 변경 내용 요약

<!-- 이 PR이 무엇을 하는지 1-3줄로 설명 -->

## 체크리스트

### 공통

- [ ] `backend/.env` 내용이 커밋에 포함되지 않았음
- [ ] `frontend/.env.local` 내용이 커밋에 포함되지 않았음

### 백엔드 배포 변경 시 (`backend/**` 수정)

- [ ] 머지 후 `build-backend-new.yml` 을 `deploy=true` 로 수동 실행 예정 (`backend/**` push 는 자동 배포되지 않는다)
- [ ] 새 env 는 `az containerapp update` 가 아니라 `infra/bicep/main.bicep` 에 넣었음 (Bicep 배포가 수동 env 를 지운다)

### Azure 환경변수 또는 API 키 변경 시

- [ ] `API_SECRET_KEY` GitHub secret 을 바꿨다면 Bicep 배포와 SWA 재빌드를 둘 다 돌릴 예정 (화면 `VITE_API_KEY` 가 같은 secret 을 쓴다)

### 지도 관련 변경 시 (`frontend/src/components/map/**`, `backend/map_data_router.py`)

- [ ] VWorld API 호출 시 domain 을 보냄 (화면 `VITE_VWORLD_DOMAIN`, 백엔드 `VWORLD_DOMAIN`. 빠지면 INCORRECT_KEY)
- [ ] 로컬에서 지적도 레이어 정상 표시 확인

## 테스트

<!-- TC 번호와 결과 기록 -->

| TC | 설명 | 결과 |
| -- | ---- | ---- |
|    |      |      |
