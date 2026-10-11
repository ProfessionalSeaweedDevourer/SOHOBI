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

@description('JWT 서명 시크릿. 빈 문자열이면 secret 미생성. non-local 환경의 backend 는 부팅에 필수 (api_server.py 가드). secretRef=jwt-secret 로 env 주입')
@secure()
param jwtSecret string = ''

// 운영 비밀값. 2026-06-25 Bicep 배포가 CLI 로 넣었던 secret 을 덮어써, 이 앱은 그 뒤로 PG 연결과 API 키 인증이
// 꺼진 채 떠 있었다. 근거: docs/plans/strategic/maintenance-mode-low-cost-ops.md 결함 (A)
//
// 필수(pgPassword, apiSecretKey): jwtSecret 과 같은 규칙. 값이 비면 secret 을 만들지 않고, env 는 main.bicep 이
// 무조건 넣는다. 그래서 값이 빠진 채로는 배포가 성공하지 않는다.
// 선택(나머지 5개): 값이 있을 때만 secret 과 env 를 한 쌍으로 만든다(아래 secrets, env). 나중에 GitHub secret 을
// 등록하고 Bicep 배포를 다시 돌리면 붙는다.

@description('필수. PG 접속 비밀번호. secretRef=pg-password, env PG_PASSWORD 는 main.bicep 이 넣는다')
@secure()
param pgPassword string = ''

@description('필수. API 키 인증 키. secretRef=api-secret-key, env API_SECRET_KEY 는 main.bicep 이 넣는다. 비면 backend/auth.py 가 검증을 건너뛴다(fail-open)')
@secure()
param apiSecretKey string = ''

@description('선택. VWorld API 키 → env VWORLD_API_KEY (필지, 토지이용 조회)')
@secure()
param vworldApiKey string = ''

@description('선택. Kakao REST 키 → env KAKAO_REST_KEY (행정동 중심점 조회)')
@secure()
param kakaoRestKey string = ''

@description('선택. 한국관광공사 API 키 → env KTO_GW_INFO_KEY (축제 조회)')
@secure()
param ktoGwInfoKey string = ''

@description('선택. Google OAuth client ID → env GOOGLE_CLIENT_ID. 비면 /auth/google 이 501')
@secure()
param googleClientId string = ''

@description('선택. Google OAuth client secret → env GOOGLE_CLIENT_SECRET')
@secure()
param googleClientSecret string = ''

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
      // 민감 값은 Container App secret 으로 저장하고 env 는 secretRef 로 참조한다.
      // out-of-band 'az containerapp secret set' 은 다음 Bicep 배포가 덮어쓰므로(좀비 버그 발생 경로) Bicep 을 source-of-truth 로 둔다.
      // 값마다 따로 걸러 concat 으로 잇는다. 한 조건 안에 묶으면 다른 secret 이 jwtSecret 유무에 따라 함께 사라진다.
      secrets: concat(
        empty(jwtSecret) ? [] : [ { name: 'jwt-secret', value: jwtSecret } ],
        empty(pgPassword) ? [] : [ { name: 'pg-password', value: pgPassword } ],
        empty(apiSecretKey) ? [] : [ { name: 'api-secret-key', value: apiSecretKey } ],
        empty(vworldApiKey) ? [] : [ { name: 'vworld-api-key', value: vworldApiKey } ],
        empty(kakaoRestKey) ? [] : [ { name: 'kakao-rest-key', value: kakaoRestKey } ],
        empty(ktoGwInfoKey) ? [] : [ { name: 'kto-gw-info-key', value: ktoGwInfoKey } ],
        empty(googleClientId) ? [] : [ { name: 'google-client-id', value: googleClientId } ],
        empty(googleClientSecret) ? [] : [ { name: 'google-client-secret', value: googleClientSecret } ]
      )
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
          // 선택 비밀값의 env 는 secrets 와 같은 조건으로 붙인다. 없는 secret 을 secretRef 로 가리키면 배포가 거부된다.
          env: concat(
            envVars,
            empty(vworldApiKey) ? [] : [ { name: 'VWORLD_API_KEY', secretRef: 'vworld-api-key' } ],
            empty(kakaoRestKey) ? [] : [ { name: 'KAKAO_REST_KEY', secretRef: 'kakao-rest-key' } ],
            empty(ktoGwInfoKey) ? [] : [ { name: 'KTO_GW_INFO_KEY', secretRef: 'kto-gw-info-key' } ],
            empty(googleClientId) ? [] : [ { name: 'GOOGLE_CLIENT_ID', secretRef: 'google-client-id' } ],
            empty(googleClientSecret) ? [] : [ { name: 'GOOGLE_CLIENT_SECRET', secretRef: 'google-client-secret' } ]
          )
          // probe 전략: Startup + Liveness 2종.
          // - Startup: cold start 보호 (AZURE_OPENAI client init, DB pool warmup). 통과 전까지 Liveness 평가 보류.
          //   periodSeconds=5 * failureThreshold=30 = 최대 150초 부팅 허용.
          // - Liveness: 부팅 후 health degrade 감지. 실패 시 컨테이너 재시작 (single revision mode 에서는 traffic 유지)
          // Readiness 는 single revision mode 에서 의미 제한적이므로 생략 (revision shift 없음).
          probes: empty(livenessProbePath) ? [] : [
            {
              type: 'Startup'
              httpGet: {
                path: livenessProbePath
                port: targetPort
              }
              initialDelaySeconds: 5
              periodSeconds: 5
              failureThreshold: 30
            }
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
