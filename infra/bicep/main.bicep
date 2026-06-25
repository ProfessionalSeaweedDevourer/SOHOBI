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

module backendApp 'modules/container-app.bicep' = {
  name: 'backendApp'
  params: {
    name: '${namePrefix}-backend'
    location: location
    tags: tags
    environmentId: containerAppsEnv.outputs.id
    acrName: acr.outputs.name
    image: useBackendAcrImage ? '${acr.outputs.loginServer}/${backendImage}' : 'mcr.microsoft.com/k8se/quickstart:latest'
    useAcrImage: useBackendAcrImage
    targetPort: useBackendAcrImage ? 8000 : 80
    livenessProbePath: useBackendAcrImage ? '/health' : ''
    jwtSecret: useBackendAcrImage ? jwtSecret : ''
    envVars: useBackendAcrImage ? [
      // 비-민감 endpoint·식별자. 민감 값(API key·password)은 Container App secret + secretRef로 주입
      { name: 'APP_ENV', value: 'production' }
      // 부팅 필수: non-local 환경에서 JWT_SECRET 미설정 시 api_server.py 가 RuntimeError 로 부팅 차단
      { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
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

@description('예산 시작일 (월 1일 고정, YYYY-MM-01). 과거 시작일은 생성 시점 기준 약 3개월까지만 허용되므로 배포 당월로 자동 계산 — 기존 budget 업데이트 시 원래 startDate가 유지됨')
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
