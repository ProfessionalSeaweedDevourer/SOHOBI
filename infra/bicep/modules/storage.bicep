// Storage Account — 백엔드 로그 (queries/rejections/errors append blob) + 진단 destination
// 기존 sohobi9638logs 동등. Standard_LRS Hot Tier (가장 저렴 + portfolio 충분)

@description('Storage account 이름. 글로벌 unique, 3-24자 소문자/숫자만')
@minLength(3)
@maxLength(24)
param name string

@description('리전')
param location string

@description('태그')
param tags object

@description('Blob container 이름 — 백엔드 logger.py가 참조')
param logsContainerName string = 'sohobi-logs'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true  // backend logger.py가 connection string 또는 AAD 둘 다 지원하도록
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7  // 실수 삭제 방지 7일 soft delete
    }
  }
}

resource logsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: logsContainerName
  properties: {
    publicAccess: 'None'
  }
}

output id string = storage.id
output name string = storage.name
output blobEndpoint string = storage.properties.primaryEndpoints.blob
output logsContainer string = logsContainer.name
