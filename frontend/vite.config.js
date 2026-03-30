import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // 기존: 메인 에이전트 백엔드 (8000)
      '/api/v1': 'http://localhost:8000',
      '/api/v1/': 'http://localhost:8000',
      '/health': 'http://localhost:8000',

      // 지도: 소상공인 DB (포트 8681, TERRY FASTAPI_URL)
      '/map-api': {
        target: 'http://localhost:8681',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/map-api/, ''),
      },

      // 지도: 부동산/상권 데이터 API (포트 8682, TERRY REALESTATE_URL)
      '/realestate': {
        target: 'http://localhost:8682',
        changeOrigin: true,
      },

      // 지도: VWorld 타일 및 WMS
      '/vworld': {
        target: 'https://api.vworld.kr',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/vworld/, ''),
      },
      '/wms': {
        target: 'https://api.vworld.kr',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/wms/, ''),
      },

      // 지도: Kakao REST API (지오코딩)
      '/kakao': {
        target: 'https://dapi.kakao.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/kakao/, ''),
      },
    },
  },
})
