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

// JWT 서명 시크릿: 환경변수 JWT_SECRET 에서 읽음 (PG 비밀번호와 동일 패턴).
// GitHub Actions workflow 가 secret(JWT_SECRET)을 env 로 주입. non-local backend 부팅 필수값.
param jwtSecret = readEnvironmentVariable('JWT_SECRET', '')

// backend 운영 비밀값: 같은 이름의 GitHub secret 을 workflow 가 env 로 주입한다.
// PG_PASSWORD 는 pgAdministratorLoginPassword 를 재사용하므로 여기에 없다.
// 등록 절차: docs/plans/2026-10-11-bicep-secrets-manual-actions.md
param apiSecretKey = readEnvironmentVariable('API_SECRET_KEY', '')
param vworldApiKey = readEnvironmentVariable('VWORLD_API_KEY', '')
param kakaoRestKey = readEnvironmentVariable('KAKAO_REST_KEY', '')
param ktoGwInfoKey = readEnvironmentVariable('KTO_GW_INFO_KEY', '')
param googleClientId = readEnvironmentVariable('GOOGLE_CLIENT_ID', '')
param googleClientSecret = readEnvironmentVariable('GOOGLE_CLIENT_SECRET', '')

// Backend Container 이미지를 ACR 빌드 이미지로 전환 (cutover 사전 deploy 검증 + D-day 영구 유지).
// build-backend-new.yml 으로 sohobi-backend:latest 가 ACR 에 push 된 상태 전제.
// 이 토글 활성화 시 Container App 이 quickstart placeholder → 실 backend (port 8000, /health probe) 로 전환됨.
param useBackendAcrImage = true

// OpenAI 모델 배포 활성화 (2026-06-11 quota 승인 확인: gpt-5.4-mini·text-embedding-3-small 은
// GlobalStandard limit 1000, text-embedding-3-large 는 Standard SKU 로 배포 — 라이브 실측 일치).
// 배포 3종: gpt-5.4-mini(chat) + text-embedding-3-small(legal 1536d) + text-embedding-3-large(gov 3072d)
param openaiDeployModels = true
