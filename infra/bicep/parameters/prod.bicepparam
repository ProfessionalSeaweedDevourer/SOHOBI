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
