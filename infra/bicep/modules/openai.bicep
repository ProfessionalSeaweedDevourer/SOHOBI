// Azure OpenAI — chat(gpt-5.4-mini) + embeddings(text-embedding-3-small/large)
// koreacentral 가용성 확인 완료 (2026-04-27). 구 환경 east us 2 → koreacentral 통일로 cross-region latency 제거 (전략 §2-2 #3)
//
// 인증: API key (publicNetworkAccess=Enabled, 기본 keyAuth). backend 코드가 AZURE_OPENAI_API_KEY를 사용하므로 호환 유지.
// AAD 전환은 후속 PR에서 backend 코드 변경과 함께 처리.
//
// 배포명 = 모델명 일치 (CLAUDE.md: AZURE_*_DEPLOYMENT 환경변수가 source-of-truth — 배포명은 모델명과 동일)

@description('OpenAI account 이름 (custom subdomain 호환: 2-40자, 알파벳/숫자/하이픈, 첫글자 알파벳)')
param name string

@description('리전')
param location string

@description('태그')
param tags object

@description('SKU (Standard만 지원)')
param skuName string = 'S0'

@description('모델 배포 진행 여부. false면 account만 생성. 신규 구독은 모델별 quota 0이므로 quota 승인 후 true로 전환')
param deployModels bool = false

@description('Chat 모델 배포 정보. gpt-5.4-mini는 GlobalStandard SKU만 지원 (koreacentral 2026-04-27 확인)')
param chatDeployment object = {
  name: 'gpt-5.4-mini'
  modelName: 'gpt-5.4-mini'
  modelVersion: '2026-03-17'
  skuName: 'GlobalStandard'
  capacity: 10
}

@description('Embedding small (legal-index용, 1536d). GlobalStandard SKU만 지원 (koreacentral 2026-04-27)')
param embeddingSmallDeployment object = {
  name: 'text-embedding-3-small'
  modelName: 'text-embedding-3-small'
  modelVersion: '1'
  skuName: 'GlobalStandard'
  capacity: 10
}

@description('Embedding large (gov-programs-index용, 3072d)')
param embeddingLargeDeployment object = {
  name: 'text-embedding-3-large'
  modelName: 'text-embedding-3-large'
  modelVersion: '1'
  skuName: 'Standard'
  capacity: 10
}

resource account 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: skuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

// 배포는 순차 처리(@batchSize 1) — Azure OpenAI는 같은 account에 동시 배포 시 conflict 가능
// deployModels=false면 빈 배열 → account만 생성, 모델 미배포 (신규 구독 quota 승인 대기 우회)
@batchSize(1)
resource deployments 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = [for d in (deployModels ? [
  chatDeployment
  embeddingSmallDeployment
  embeddingLargeDeployment
] : []): {
  parent: account
  name: d.name
  sku: {
    name: d.skuName
    capacity: d.capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: d.modelName
      version: d.modelVersion
    }
  }
}]

output id string = account.id
output name string = account.name
output endpoint string = account.properties.endpoint
output chatDeploymentName string = chatDeployment.name
output embeddingSmallDeploymentName string = embeddingSmallDeployment.name
output embeddingLargeDeploymentName string = embeddingLargeDeployment.name
