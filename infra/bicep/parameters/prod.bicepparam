// 신규 구독 (eba83124-...) prod 파라미터
using '../main.bicep'

param namePrefix = 'sohobi'
param env = 'prod'
param location = 'koreacentral'
param tags = {
  project: 'sohobi'
  env: 'prod'
  'managed-by': 'bicep'
}
