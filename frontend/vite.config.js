import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // 개발 중 CORS 우회: /api/* 요청을 백엔드로 프록시
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
