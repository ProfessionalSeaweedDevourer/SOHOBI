export const SITE_URL = 'https://sohobi.net';

export const seoConfig = {
  '/': {
    title: 'AI 기반 외식업 창업 컨설팅',
    description:
      '소호비(SOHOBI) — AI 기반 외식업 창업 컨설팅. 사업성 분석, 상권분석, 재무 시뮬레이션, 법률·세무 상담을 무료로 제공합니다.',
  },
  '/features': {
    title: '기능 소개 — AI 창업 에이전트',
    description:
      '행정 절차 안내, 재무 시뮬레이션, 법무 정보, 상권 분석, 정부 지원 추천 등 SOHOBI의 핵심 기능을 확인하세요.',
    jsonLd: {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: [
        {
          '@type': 'Question',
          name: '소호비는 어떤 서비스인가요?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: '소호비(SOHOBI)는 AI 기반 외식업 창업 컨설팅 플랫폼입니다. 사업성 분석, 상권분석, 재무 시뮬레이션, 법률·세무 상담을 무료로 제공합니다.',
          },
        },
        {
          '@type': 'Question',
          name: '상권 분석은 어떻게 하나요?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: '서울 2025년 4분기 데이터 기반으로 월매출·유동인구·경쟁업체·개폐업률을 분석합니다. 복수 지역 비교도 가능합니다.',
          },
        },
        {
          '@type': 'Question',
          name: '재무 시뮬레이션은 어떻게 작동하나요?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: '몬테카를로 시뮬레이션(10,000회)으로 창업 수익성을 분석합니다. 손익분기점, 손실 확률, 투자 회수 시나리오를 차트로 확인할 수 있습니다.',
          },
        },
        {
          '@type': 'Question',
          name: '창업 관련 법률 정보도 제공하나요?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: '네, 임대차 계약·권리금·상가건물임대차보호법 등 창업자가 꼭 알아야 할 법적 정보를 법령 조항 인용과 함께 제공합니다.',
          },
        },
        {
          '@type': 'Question',
          name: '정부 지원 사업은 어떻게 추천받나요?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: '업종·나이·지역을 알려주시면 5,600건 이상의 지원사업 중 수혜 가능한 보조금·창업패키지·대출·신용보증을 자동으로 매칭해드립니다.',
          },
        },
      ],
    },
  },
  '/map': {
    title: '상권분석 지도',
    description:
      '서울 행정동별 상권 데이터를 지도에서 탐색하세요. 점포 밀도, 업종 분포, 유동인구 정보를 실시간으로 확인할 수 있습니다.',
  },
  '/user': {
    title: 'AI 창업 상담',
    description:
      '창업 관련 질문을 입력하면 전문 AI 에이전트가 사업성, 재무, 법률, 상권을 종합 분석하여 답변합니다.',
  },
  '/home': {
    title: '모드 선택',
    description:
      '소호비의 다양한 모드를 선택하세요. AI 상담, 상권 지도 등 목적에 맞는 기능을 이용할 수 있습니다.',
  },
  '/privacy': {
    title: '개인정보처리방침',
    description:
      'SOHOBI 개인정보처리방침. 수집하는 개인정보 항목, 이용 목적, 보유 기간 등을 안내합니다.',
  },
  '/changelog': {
    title: '업데이트 로그',
    description: 'SOHOBI 최신 업데이트 및 변경 사항을 확인하세요.',
  },
  '/roadmap': {
    title: '로드맵',
    description:
      'SOHOBI 개발 로드맵. 예정된 기능과 진행 상황을 확인하고 투표로 의견을 보내주세요.',
  },
  // noindex 페이지
  '/dev': { title: '개발자 채팅', noindex: true },
  '/dev/login': { title: '개발자 로그인', noindex: true },
  '/dev/logs': { title: '로그 뷰어', noindex: true },
  '/auth/callback': { title: '인증', noindex: true },
  '/my-report': { title: '내 보고서', noindex: true },
  '/my-logs': { title: '내 상담 기록', noindex: true },
};

