// 프론트엔드 Static Web App. 배포는 GitHub Actions 가 배포 토큰으로 dist 를 올린다(리포 연결 없음).
// 2026-10-22~23 구 테넌트 정리로 옛 SWA(delightful-rock-0de6c000f)가 사라져 새 구독에 다시 만든다.
// 경위: docs/plans/2026-11-02-sohobi-net-outage-recovery.md

@description('Static Web App 이름')
param name string

@description('리전. SWA 는 koreacentral 을 지원하지 않아 가장 가까운 eastasia 를 쓴다')
param location string = 'eastasia'

param tags object = {}

resource swa 'Microsoft.Web/staticSites@2023-12-01' = {
  name: name
  location: location
  tags: tags
  // Free: 비용 0, 미리보기 환경 3개 (azure-static-web-apps.yml 의 정원 검사와 맞춘다)
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
  }
}

output name string = swa.name
output defaultHostname string = swa.properties.defaultHostname
