// Container Apps Environment — Container App 호스팅용 공유 환경
// Right-sizing: Consumption-only workload profile (사용량 기반, idle 시 0)
// 전략 §3-A: minReplicas=0 / Consumption profile

@description('환경 이름')
param name string

@description('리전')
param location string

@description('태그')
param tags object

@description('Log Analytics workspace customerId (workspace ID)')
param logAnalyticsCustomerId string

@description('Log Analytics workspace primary shared key')
@secure()
param logAnalyticsSharedKey string

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}

output id string = env.id
output name string = env.name
output defaultDomain string = env.properties.defaultDomain
