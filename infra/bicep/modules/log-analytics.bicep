// Log Analytics workspace — Container App·기타 자원 진단 destination
// Right-sizing: PerGB2018 / 30일 보존 (최소)
// 전략 §3-B: 보존기간 단축으로 비용 최소

@description('워크스페이스 이름')
param name string

@description('리전')
param location string

@description('태그')
param tags object

@description('데이터 보존(일). 30=최소. 1주(7)는 무료지만 KQL 분석 부족')
@minValue(30)
@maxValue(730)
param retentionInDays int = 30

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      // 일일 수집 한도 (GB) — 폭주 시 청구 폭발 방지. portfolio라 0.5GB/일이면 충분
      dailyQuotaGb: json('0.5')
    }
  }
}

output workspaceId string = workspace.id
output customerId string = workspace.properties.customerId
output name string = workspace.name
