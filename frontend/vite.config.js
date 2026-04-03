import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
   plugins: [react(), tailwindcss()],
   server: {
      port: 3000,
      proxy: {
         // 기존: 메인 에이전트 백엔드 (8000)
         "/api/v1": "http://localhost:8000",
         "/api/v1/": "http://localhost:8000",
         "/health": "http://localhost:8000",

         // 지도: 소상공인 DB (integrated_PARK 통합 서버, 포트 8000)
         // /map-api: useLandmarkLayer.js 폴백 경로 (rewrite 필요)
         "/map-api": {
            target: "http://localhost:8000",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/map-api/, ""),
         },
         // /map: MapView.jsx의 모든 /map/* 요청 커버
         "/map": { target: "http://localhost:8000", changeOrigin: true },

         // 지도: 부동산/상권 데이터 API (integrated_PARK 통합 서버, 포트 8000)
         "/realestate": {
            target: "http://localhost:8000",
            changeOrigin: true,
         },

         // 지도: VWorld 타일 및 WMS
         "/vworld": {
            target: "https://api.vworld.kr",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/vworld/, ""),
         },
         "/wms": {
            target: "https://api.vworld.kr",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/wms/, ""),
         },

         // 지도: Kakao REST API (지오코딩)
         "/kakao": {
            target: "https://dapi.kakao.com",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/kakao/, ""),
         },
      },
   },
});
