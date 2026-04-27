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
// Outputs (후속 모듈에서 참조)
// ================================================================

output logAnalyticsId string = logAnalytics.outputs.workspaceId
output logAnalyticsCustomerId string = logAnalytics.outputs.customerId
output storageId string = storage.outputs.id
output storageName string = storage.outputs.name
output acrId string = acr.outputs.id
output acrLoginServer string = acr.outputs.loginServer
