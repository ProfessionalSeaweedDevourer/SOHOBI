// SOHOBI Azure 인프라 — RG-scope entrypoint
// 신규 테넌트 (5555704e-...) / 신규 구독 (eba83124-...) / RG: rg-sohobi-prod (koreacentral)
// 기획안: docs/plans/2026-04-26-azure-tenant-migration.md
// 전략: docs/plans/strategic/azure-cost-and-tenant-strategy.md
//
// 본 파일은 RG 전체 인프라 entrypoint — Log Analytics, Storage, ACR, Container App,
// Cosmos, PostgreSQL, OpenAI, 비용 가드(budget)를 모듈로 배선한다.

targetScope = 'resourceGroup'

@description('리소스 이름 prefix. 글로벌 unique 자원의 충돌 방지용')
param namePrefix string = 'sohobi'

@description('환경 식별자')
@allowed(['prod', 'staging', 'dev'])
param env string = 'prod'

@description('주요 리전')
param location string = resourceGroup().location

@description('공통 태그')
param tags object = {
  project: 'sohobi'
  env: env
  'managed-by': 'bicep'
}

@description('PostgreSQL Flexible Server 관리자 비밀번호. workflow에서 secret(PG_ADMIN_PASSWORD)으로 주입')
@secure()
param pgAdministratorLoginPassword string

@description('JWT 서명 시크릿. workflow에서 secret(JWT_SECRET)으로 주입. non-local backend 부팅 필수값. 빈 값이면 미주입(quickstart placeholder 호환)')
@secure()
param jwtSecret string = ''

// backend 운영 비밀값. 모두 workflow 가 같은 이름의 GitHub secret 을 env 로 넘기고 prod.bicepparam 이 읽는다.
// PG 비밀번호는 별도 파라미터 없이 pgAdministratorLoginPassword 를 재사용한다(같은 배포가 서버 비밀번호도 적용하므로 항상 일치).
// 필수: apiSecretKey. 선택: 나머지 5개 (비어 있으면 해당 secret 과 env 를 만들지 않는다).

@description('필수. API 키 인증 키 (GitHub secret API_SECRET_KEY). 프론트엔드가 보내는 키(VITE_API_KEY)와 같은 값이어야 한다')
@secure()
param apiSecretKey string = ''

@description('선택. VWorld API 키 (GitHub secret VWORLD_API_KEY)')
@secure()
param vworldApiKey string = ''

@description('선택. Kakao REST 키 (GitHub secret KAKAO_REST_KEY)')
@secure()
param kakaoRestKey string = ''

@description('선택. 한국관광공사 API 키 (GitHub secret KTO_GW_INFO_KEY)')
@secure()
param ktoGwInfoKey string = ''

@description('선택. Google OAuth client ID (GitHub secret GOOGLE_CLIENT_ID)')
@secure()
param googleClientId string = ''

@description('선택. Google OAuth client secret (GitHub secret GOOGLE_CLIENT_SECRET)')
@secure()
param googleClientSecret string = ''

// ================================================================
// Foundation 자원
// ================================================================

module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'logAnalytics'
  params: {
    name: '${namePrefix}-logs'
    location: location
    tags: tags
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    // global unique 필요 — '<prefix><env>logs' 형태 (24자, 소문자/숫자만)
    name: toLower('${namePrefix}${env}logs')
    location: location
    tags: tags
  }
}

module acr 'modules/acr.bicep' = {
  name: 'acr'
  params: {
    // global unique 필요 — alphanumeric only, 5-50자
    name: toLower('${namePrefix}${env}acr')
    location: location
    tags: tags
  }
}

// ================================================================
// Compute 자원
// ================================================================

// Log Analytics shared key — Container Apps Environment 진단 destination 인증용.
// listKeys()로 deploy time에 fetch (코드/state에 평문 저장 없음).
resource logAnalyticsRef 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: '${namePrefix}-logs'
  dependsOn: [logAnalytics]
}

module containerAppsEnv 'modules/container-apps-env.bicep' = {
  name: 'containerAppsEnv'
  params: {
    name: '${namePrefix}-${env}-env'
    location: location
    tags: tags
    logAnalyticsCustomerId: logAnalytics.outputs.customerId
    logAnalyticsSharedKey: logAnalyticsRef.listKeys().primarySharedKey
  }
}

@description('실 backend 이미지를 ACR에서 가져올지. true 전환 전 ACR에 이미지 사전 적재 필수 (build-backend-new.yml workflow_dispatch)')
param useBackendAcrImage bool = false

@description('Backend Container 이미지 (ACR 사용 시 sohobi-backend:latest 등). useBackendAcrImage=false면 무시되고 quickstart 사용')
param backendImage string = 'sohobi-backend:latest'

var backendAppName = '${namePrefix}-backend'

module backendApp 'modules/container-app.bicep' = {
  name: 'backendApp'
  params: {
    name: backendAppName
    location: location
    tags: tags
    environmentId: containerAppsEnv.outputs.id
    acrName: acr.outputs.name
    image: useBackendAcrImage ? '${acr.outputs.loginServer}/${backendImage}' : 'mcr.microsoft.com/k8se/quickstart:latest'
    useAcrImage: useBackendAcrImage
    targetPort: useBackendAcrImage ? 8000 : 80
    livenessProbePath: useBackendAcrImage ? '/health' : ''
    jwtSecret: useBackendAcrImage ? jwtSecret : ''
    pgPassword: useBackendAcrImage ? pgAdministratorLoginPassword : ''
    apiSecretKey: useBackendAcrImage ? apiSecretKey : ''
    vworldApiKey: useBackendAcrImage ? vworldApiKey : ''
    kakaoRestKey: useBackendAcrImage ? kakaoRestKey : ''
    ktoGwInfoKey: useBackendAcrImage ? ktoGwInfoKey : ''
    googleClientId: useBackendAcrImage ? googleClientId : ''
    googleClientSecret: useBackendAcrImage ? googleClientSecret : ''
    envVars: useBackendAcrImage ? [
      // 비-민감 endpoint·식별자. 민감 값(API key·password)은 Container App secret + secretRef로 주입
      { name: 'APP_ENV', value: 'production' }
      // 부팅 필수: non-local 환경에서 JWT_SECRET 미설정 시 api_server.py 가 RuntimeError 로 부팅 차단
      { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
      // 필수 비밀값. JWT_SECRET 처럼 무조건 넣으므로 값이 빠지면 배포가 성공하지 않는다
      // (azure-bicep-deploy.yml 이 그 전에 미등록 이름을 밝히고 멈춘다). 선택 비밀값 5개의 env 는 모듈이 붙인다.
      { name: 'PG_PASSWORD', secretRef: 'pg-password' }
      // 비면 backend/auth.py 가 인증을 건너뛴다(fail-open). 2026-10-11 실측: 이 env 가 없어 키 없는 호출이 200 이었다
      { name: 'API_SECRET_KEY', secretRef: 'api-secret-key' }
      // Google 로그인 주소 (backend/auth_router.py). 기본값이 localhost 라 비우면 로그인 후 localhost 로 돌아간다.
      // BACKEND_HOST 는 OAuth redirect_uri 의 앞부분이므로 Google 콘솔의 승인된 redirect URI 와 같아야 한다
      { name: 'FRONTEND_URL', value: 'https://sohobi.net' }
      { name: 'BACKEND_HOST', value: 'https://${backendAppName}.${containerAppsEnv.outputs.defaultDomain}' }
      { name: 'AZURE_OPENAI_ENDPOINT', value: openai.outputs.endpoint }
      { name: 'AZURE_OPENAI_API_VERSION', value: '2024-08-01-preview' }
      { name: 'AZURE_DEPLOYMENT_NAME', value: openai.outputs.chatDeploymentName }
      { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT', value: openai.outputs.chatDeploymentName }
      { name: 'AZURE_EMBEDDING_DEPLOYMENT', value: openai.outputs.embeddingLargeDeploymentName }
      { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: openai.outputs.embeddingLargeDeploymentName }
      { name: 'AZURE_OPENAI_EMBEDDING_DIMS', value: '3072' }
      // cosmos.outputs.* 참조는 backendApp ↔ cosmos 순환 의존 발생 (cosmos가 backendApp.principalId 의존)
      // → 결정적 naming convention 기반 static 구성으로 우회
      { name: 'COSMOS_ENDPOINT', value: 'https://${namePrefix}-${env}-cosmos.documents.azure.com:443/' }
      // 백엔드 코드는 COSMOS_DATABASE (suffix 없음) 만 읽음 (backend/session_store.py:46, backend/roadmap_router.py:225 등). NAME suffix 표기는 stale 컨벤션이므로 source-of-truth 키로 통일
      { name: 'COSMOS_DATABASE', value: 'sohobi' }
      { name: 'PG_HOST', value: postgres.outputs.fqdn }
      { name: 'PG_PORT', value: '5432' }
      { name: 'PG_DB', value: postgres.outputs.databaseName }
      { name: 'PG_USER', value: postgres.outputs.administratorLogin }
      { name: 'PG_SSLMODE', value: 'require' }
      { name: 'VWORLD_DOMAIN', value: 'https://sohobi.net' }
      { name: 'AZURE_STORAGE_CONTAINER', value: 'sohobi-logs' }
      // RAG는 cutover 후 pgvector 백필 전까지 비활성 — backend에 fallback 로직 있음
      { name: 'RAG_BACKEND', value: 'disabled' }
    ] : []
  }
}

// ================================================================
// 데이터 자원
// ================================================================

module cosmos 'modules/cosmos.bicep' = {
  name: 'cosmos'
  params: {
    // global unique. 3-44자, 소문자/숫자/하이픈
    name: '${namePrefix}-${env}-cosmos'
    location: location
    tags: tags
    databaseName: 'sohobi'
    dataContributorPrincipalIds: [
      backendApp.outputs.principalId
    ]
  }
}

@description('OpenAI 모델 배포 활성화. false면 account만 생성. 신규 구독 quota 승인 후 true로 전환')
param openaiDeployModels bool = false

module openai 'modules/openai.bicep' = {
  name: 'openai'
  params: {
    // global unique. custom subdomain 호환을 위해 2-40자
    name: '${namePrefix}-${env}-openai'
    location: location
    tags: tags
    deployModels: openaiDeployModels
  }
}

@description('Azure AI Search 활성화. Basic SKU = $73/월 정액, 사용량 무관. 자체 RAG(FAISS/SQLite-VSS/pgvector) 대안 검토 중이라 default=false')
param enableAiSearch bool = false

module aiSearch 'modules/ai-search.bicep' = if (enableAiSearch) {
  name: 'aiSearch'
  params: {
    // global unique. 2-60자, 소문자/숫자/하이픈
    name: '${namePrefix}-${env}-search'
    location: location
    tags: tags
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    // global unique. 3-63자, 소문자/숫자/하이픈
    name: '${namePrefix}-${env}-pg'
    location: location
    tags: tags
    databaseName: 'sohobi'
    administratorLoginPassword: pgAdministratorLoginPassword
  }
}

// ================================================================
// 비용 가드
// ================================================================

@description('월 예산 (KRW). 프로젝트 정식 종료 후 최소 비용 유지보수 기준 — baseline ~₩6~7K(ACR Basic이 대부분)의 약 3배로 설정해 정상 달엔 조용하고, 비정상 비용(예: stuck 리비전)은 며칠 내 50/80% 알람으로 조기 포착. 2026-06-23 ₩60,000 → ₩20,000 하향 (구 한도는 stuck 리비전을 13일+ 지나서야 100%에 닿아 조기탐지 실패).')
param budgetAmountKrw int = 20000

@description('예산 알림 수신 이메일')
param budgetContactEmails array = [
  'erik.j.park@gmail.com'
  'guga.kr@gmail.com'
  'leftdeadman@gmail.com'
  'delta115zx@naver.com'
]

@description('예산 시작일 (월 1일 고정, YYYY-MM-01). 기본값은 배포 당월로, 예산을 처음 만들 때만 맞다. 기존 예산의 시작일은 바꿀 수 없어(400 "Start date of budgets cannot be updated") 다른 달에 배포하면 실패하므로, 운영은 prod.bicepparam 에서 기존 값으로 고정한다')
param budgetStartDate string = utcNow('yyyy-MM-01')

module budget 'modules/budget.bicep' = {
  name: 'budget'
  params: {
    amount: budgetAmountKrw
    contactEmails: budgetContactEmails
    startDate: budgetStartDate
  }
}

// ================================================================
// Outputs (후속 모듈에서 참조)
// ================================================================

output logAnalyticsId string = logAnalytics.outputs.workspaceId
output logAnalyticsCustomerId string = logAnalytics.outputs.customerId
output storageId string = storage.outputs.id
output storageName string = storage.outputs.name
output acrId string = acr.outputs.id
output acrLoginServer string = acr.outputs.loginServer
output containerAppsEnvId string = containerAppsEnv.outputs.id
output backendAppFqdn string = backendApp.outputs.fqdn
output backendAppPrincipalId string = backendApp.outputs.principalId
output cosmosEndpoint string = cosmos.outputs.endpoint
output cosmosDatabaseName string = cosmos.outputs.databaseName
output postgresFqdn string = postgres.outputs.fqdn
output postgresDatabaseName string = postgres.outputs.databaseName
output postgresAdministratorLogin string = postgres.outputs.administratorLogin
output openaiEndpoint string = openai.outputs.endpoint
output openaiChatDeployment string = openai.outputs.chatDeploymentName
output openaiEmbeddingSmallDeployment string = openai.outputs.embeddingSmallDeploymentName
output openaiEmbeddingLargeDeployment string = openai.outputs.embeddingLargeDeploymentName
output aiSearchEndpoint string = enableAiSearch ? aiSearch!.outputs.endpoint : ''
output aiSearchName string = enableAiSearch ? aiSearch!.outputs.name : ''
