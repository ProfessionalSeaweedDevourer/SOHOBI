// RG-scope 월간 예산 알람 — 모델 배포(사용량 과금) 활성화에 따른 비용 가드
// Azure OpenAI에는 월간 토큰 하드 컷오프가 없으므로 budget 알림이 표준 대응:
//   1차 방어: 배포 capacity(TPM rate cap, openai.bicep) / 2차: backend rate limit / 3차: 본 알람
// 주의: RG scope라 RG 외부 비용(구독 수준 Defender 등)은 미포함 — 현재 전 자원이 rg-sohobi-prod에 있음

@description('예산 이름')
param name string = 'sohobi-prod-monthly'

@description('월 예산 금액 (구독 청구 통화 = KRW)')
param amount int = 60000

@description('알림 수신 이메일')
param contactEmails array

@description('예산 시작일 (월 1일이어야 함, YYYY-MM-01)')
param startDate string

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: name
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
      // endDate 생략 시 10년 기본
    }
    notifications: {
      actual50: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 50
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }
      actual80: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }
      actual100: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }
      forecast100: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: contactEmails
      }
    }
  }
}

output id string = budget.id
