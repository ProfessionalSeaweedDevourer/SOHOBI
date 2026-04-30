// SOHOBI Azure 인프라 — RG-scope entrypoint
// 신규 테넌트 (5555704e-...) / 신규 구독 (eba83124-...) / RG: rg-sohobi-prod (koreacentral)
// 기획안: docs/plans/2026-04-26-azure-tenant-migration.md
// 전략: docs/plans/strategic/azure-cost-and-tenant-strategy.md
//
// 본 파일은 Foundation 단계 — 의존 없는 기반 자원만 (Log Analytics, Storage, ACR).
// 후속 PR에서 Container App, Cosmos, PG, OpenAI, AI Search, Static Web App 추가 예정.

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

module backendApp 'modules/container-app.bicep' = {
  name: 'backendApp'
  params: {
    name: '${namePrefix}-backend'
    location: location
    tags: tags
    environmentId: containerAppsEnv.outputs.id
    acrName: acr.outputs.name
    // 첫 배포는 quickstart 이미지로 (실제 backend 이미지는 GitHub Actions deploy 후 교체)
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
