// 신규 구독 (eba83124-...) prod 파라미터
using '../main.bicep'

param namePrefix = 'sohobi'
param env = 'prod'
param location = 'koreacentral'
param tags = {
  project: 'sohobi'
  env: 'prod'
  'managed-by': 'bicep'
}

// PG 관리자 비밀번호: 환경변수 PG_ADMIN_PASSWORD 에서 읽음
// - 로컬: export PG_ADMIN_PASSWORD='...' 후 az deployment 실행
// - GitHub Actions: workflow가 secret을 env로 주입
param pgAdministratorLoginPassword = readEnvironmentVariable('PG_ADMIN_PASSWORD', '')

// Backend Container 이미지를 ACR 빌드 이미지로 전환 (cutover 사전 deploy 검증 + D-day 영구 유지).
// build-backend-new.yml 으로 sohobi-backend:latest 가 ACR 에 push 된 상태 전제.
// 이 토글 활성화 시 Container App 이 quickstart placeholder → 실 backend (port 8000, /health probe) 로 전환됨.
param useBackendAcrImage = true
