// Azure AI Search — legal-index(small embeddings) + gov-programs-index(large embeddings) 호스팅
// SKU: basic. free tier semantic search 포함. ~$73/mo (24/7 정액)
// 전략 §6: 외부 계정(choiasearchhh) 의존 제거 후 자체 인덱스로 재구축
//
// 본 모듈은 빈 서비스만 프로비저닝 — 인덱스는 별도 파이프라인 빌드:
//   - legal-index: PR #325 6단계 파이프라인 (data/legal/raw → 인덱싱)
//   - gov-programs-index: 정부24 API 자동수집 Function App (cutover 후 백필)
//
// 인증: API key (backend 코드 호환). AAD 전환은 후속 PR.

@description('AI Search 서비스 이름 (2-60자, 소문자/숫자/하이픈, global unique)')
param name string

@description('리전')
param location string

@description('태그')
param tags object

@description('SKU. basic = 1 replica/1 partition, free semantic search')
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3'])
param skuName string = 'basic'

@description('replica 개수 (basic은 1)')
@minValue(1)
@maxValue(12)
param replicaCount int = 1

@description('partition 개수 (basic은 1)')
@minValue(1)
@maxValue(12)
param partitionCount int = 1

@description('semantic search tier. basic SKU는 free 가능')
@allowed(['disabled', 'free', 'standard'])
param semanticSearch string = 'free'

resource search 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: replicaCount
    partitionCount: partitionCount
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    semanticSearch: semanticSearch
    authOptions: {
      apiKeyOnly: {}
    }
    disableLocalAuth: false
  }
}

output id string = search.id
output name string = search.name
output endpoint string = 'https://${search.name}.search.windows.net'
output principalId string = search.identity.principalId
