// Azure Container Registry — Container App image 호스팅
// Basic SKU = ~$5/월 (가장 저렴 tier). Standard·Premium은 portfolio에 과함

@description('ACR 이름. 글로벌 unique, 5-50자 alphanumeric')
@minLength(5)
@maxLength(50)
param name string

@description('리전')
param location string

@description('태그')
param tags object

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false  // managed identity 기반 인증 권장
    publicNetworkAccess: 'Enabled'  // GitHub Actions push 위해 필수
    zoneRedundancy: 'Disabled'
  }
}

output id string = acr.id
output name string = acr.name
output loginServer string = acr.properties.loginServer
