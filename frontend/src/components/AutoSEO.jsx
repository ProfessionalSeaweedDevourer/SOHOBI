import { useLocation } from 'react-router-dom';
import { seoConfig } from '../config/seoConfig';
import SEO from './SEO';

const BREADCRUMB_MAP = {
  '/': null,
  '/home': [{ name: '홈', path: '/' }, { name: '모드 선택', path: '/home' }],
  '/features': [{ name: '홈', path: '/' }, { name: '기능 소개', path: '/features' }],
  '/map': [{ name: '홈', path: '/' }, { name: '상권분석 지도', path: '/map' }],
  '/user': [{ name: '홈', path: '/' }, { name: 'AI 상담', path: '/user' }],
  '/privacy': [{ name: '홈', path: '/' }, { name: '개인정보처리방침', path: '/privacy' }],
  '/changelog': [{ name: '홈', path: '/' }, { name: '업데이트 로그', path: '/changelog' }],
  '/roadmap': [{ name: '홈', path: '/' }, { name: '로드맵', path: '/roadmap' }],
};

export default function AutoSEO() {
  const { pathname } = useLocation();
  const config = seoConfig[pathname];

  if (!config) return null;

  return (
    <SEO
      title={config.title}
      description={config.description}
      path={pathname}
      jsonLd={config.jsonLd}
      noindex={config.noindex}
      breadcrumbs={BREADCRUMB_MAP[pathname]}
    />
  );
}
