// Container App — backend FastAPI 호스트
// Right-sizing: minReplicas=0 (idle scale-to-zero), Consumption profile
// 전략 §3-A: 야간 idle 시 0 replica → 컴퓨트 비용 0

@description('Container App 이름')
param name string

@description('리전')
param location string

@description('태그')
param tags object

@description('Container Apps 환경 ID')
param environmentId string

@description('ACR 이름 (loginServer 추출용)')
param acrName string

@description('Container 이미지 (예: sohobi-backend:latest). 첫 배포 전 placeholder OK')
param image string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('이미지가 ACR에서 오는지 여부. true면 registries 설정 + AcrPull 부여, false면 public image로 처리. 첫 배포는 false (quickstart placeholder)')
param useAcrImage bool = false

@description('컨테이너 내부 listen 포트. 기본 80 = quickstart placeholder image 호환. 실제 backend 이미지(8000) 배포 시 az containerapp update로 교체')
param targetPort int = 80

@description('최소 replica (0=scale-to-zero)')
@minValue(0)
@maxValue(10)
param minReplicas int = 0

@description('최대 replica')
@minValue(1)
@maxValue(30)
param maxReplicas int = 3

@description('CPU (vCPU)')
param cpu string = '0.5'

@description('Memory')
param memory string = '1Gi'

@description('환경 변수 배열 (실제 secret/value는 후속 PR에서 KeyVault reference로 주입)')
param envVars array = []

@description('Liveness probe HTTP path. 빈 문자열이면 probe 미설정 (quickstart placeholder 호환). 실제 backend 배포 시 /api/v1/health 등으로 override')
param livenessProbePath string = ''

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: useAcrImage ? [
        {
          server: acr.properties.loginServer
          identity: 'system'
        }
      ] : []
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: image
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: envVars
          probes: empty(livenessProbePath) ? [] : [
            {
              type: 'Liveness'
              httpGet: {
                path: livenessProbePath
                port: targetPort
              }
              initialDelaySeconds: 30
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

// AcrPull 역할: Container App system identity가 ACR에서 이미지 pull 가능하도록.
// 항상 부여(이상 없음). registries 설정은 useAcrImage로 분기 — 첫 부트스트랩은 public image로 통과시키고,
// 실제 backend 이미지 배포 시 useAcrImage=true로 전환하면 권한 이미 준비됨.
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, app.id, 'AcrPull')
  scope: acr
  properties: {
    principalId: app.identity.principalId
    // 7f951dda-... = AcrPull built-in role
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalType: 'ServicePrincipal'
  }
}

output id string = app.id
output name string = app.name
output fqdn string = app.properties.configuration.ingress.fqdn
output principalId string = app.identity.principalId
