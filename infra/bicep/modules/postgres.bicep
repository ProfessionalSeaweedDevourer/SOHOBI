// PostgreSQL Flexible Server (Burstable B1ms) — 위치/상권 데이터 영속 저장
// Right-sizing: B1ms 24/7 ≈ $12-15/mo, 야간(23-08시) 정지 시 ~50% 절감 (전략 §3-A: 기존 B2s에서 다운사이즈)
// autostop은 cron(.github/workflows/pg-nightly-stop.yml)으로 별도 처리 — 본 모듈은 정지/기동 정책 미설정
//
// 인증: PG 네이티브(admin login + password). AAD 인증은 후속 PR에서 추가 (Container App principal 등록 필요)
// 네트워크: public + AllowAzureServices 방화벽 규칙 (Container App outbound IP가 dynamic이라 IP allowlist 불가)

@description('PG Flexible Server 이름 (3-63자, 소문자/숫자/하이픈)')
param name string

@description('리전')
param location string

@description('태그')
param tags object

@description('PostgreSQL 메이저 버전')
@allowed(['14', '15', '16'])
param version string = '16'

@description('SKU name. 비용 최소화: Standard_B1ms (1 vCPU, 2 GiB)')
param skuName string = 'Standard_B1ms'

@description('SKU tier. Burstable=B 시리즈')
@allowed(['Burstable', 'GeneralPurpose', 'MemoryOptimized'])
param skuTier string = 'Burstable'

@description('스토리지 크기(GiB). 최소 32. 늘릴 수만 있음(축소 불가)')
@minValue(32)
param storageSizeGB int = 32

@description('자동 백업 보존일수')
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 7

@description('관리자 로그인 이름')
param administratorLogin string = 'sohobiadmin'

@description('관리자 비밀번호. workflow에서 secret으로 주입 (--parameters administratorLoginPassword=...)')
@secure()
param administratorLoginPassword string

@description('초기 생성할 데이터베이스 이름')
param databaseName string = 'sohobi'

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    version: version
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword
    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: 'Disabled'
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
    authConfig: {
      passwordAuth: 'Enabled'
      activeDirectoryAuth: 'Disabled'
    }
  }
}

// "Allow access from Azure services" 특수 규칙: start=end=0.0.0.0
// Container App outbound IP는 dynamic이라 개별 allowlist 불가 → Azure 내부 트래픽 허용
resource firewallAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: server
  name: 'AllowAllAzureServicesAndResourcesWithinAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: server
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

output id string = server.id
output name string = server.name
output fqdn string = server.properties.fullyQualifiedDomainName
output databaseName string = database.name
output administratorLogin string = administratorLogin
