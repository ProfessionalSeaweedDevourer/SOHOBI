// Cosmos DB (Serverless) — backend session/event/feedback/checklist 등 운영 데이터
// Right-sizing: Serverless capacity mode → idle 시 RU 비용 0, 사용량 기반 과금 (전략 §3-A)
// AAD 전용: disableLocalAuth=true (handoff §traps: 신규도 default 비활성 가능성)

@description('Cosmos account 이름 (global unique, 3-44자, 소문자/숫자/하이픈)')
param name string

@description('리전')
param location string

@description('태그')
param tags object

@description('데이터베이스 이름')
param databaseName string = 'sohobi'

@description('Cosmos Data Contributor 역할을 부여받을 principalId 배열 (예: backend Container App system identity)')
param dataContributorPrincipalIds array = []

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: name
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    minimalTlsVersion: 'Tls12'
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Local'
      }
    }
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: account
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// 컨테이너 정의 — backend 코드에서 사용하는 6종
// (sessions/usage_events/feedback/checklist/roadmap_votes/users)
var containers = [
  {
    name: 'sessions'
    partitionKey: '/id'
    defaultTtl: 86400 // 24h
  }
  {
    name: 'usage_events'
    partitionKey: '/session_id'
    defaultTtl: -1 // no expiry
  }
  {
    name: 'feedback'
    partitionKey: '/agent_type'
    defaultTtl: -1
  }
  {
    name: 'checklist'
    partitionKey: '/session_id'
    defaultTtl: -1
  }
  {
    name: 'roadmap_votes'
    partitionKey: '/feature_id'
    defaultTtl: -1
  }
  {
    name: 'users'
    partitionKey: '/id'
    defaultTtl: -1
  }
]

resource sqlContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = [for c in containers: {
  parent: database
  name: c.name
  properties: {
    resource: {
      id: c.name
      partitionKey: {
        paths: [c.partitionKey]
        kind: 'Hash'
      }
      defaultTtl: c.defaultTtl
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
      }
    }
  }
}]

// Cosmos DB Built-in Data Contributor (built-in role definition ID 00000000-0000-0000-0000-000000000002)
// 이 역할은 SQL data plane 권한 — control plane RBAC와 다름
resource dataContributorAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = [for principalId in dataContributorPrincipalIds: {
  parent: account
  name: guid(account.id, principalId, 'DataContributor')
  properties: {
    roleDefinitionId: '${account.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: principalId
    scope: account.id
  }
}]

output id string = account.id
output name string = account.name
output endpoint string = account.properties.documentEndpoint
output databaseName string = database.name
