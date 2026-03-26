import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
   plugins: [react()],
   server: {
      proxy: {
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
         "/kakao": {
            target: "https://dapi.kakao.com",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/kakao/, ""),
         },
         "/api": {
            target: "http://localhost:8681",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api/, ""),
         },
         "/agent": {
            target: "http://localhost:8000",
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/agent/, ""),
         },
      },
   },
});
