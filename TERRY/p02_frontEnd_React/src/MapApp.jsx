import { useEffect, useState } from "react";
import MapView from "./components/MapView";

// ✅ effect 밖에서 키 체크 → setState 불필요
const JS_KEY = import.meta.env.VITE_KAKAO_JS_KEY;

export default function App() {
   const [kakaoReady, setKakaoReady] = useState(false);

   // JS 키 없으면 바로 에러 화면 (effect 없이)
   if (!JS_KEY) {
      return (
         <div style={S.center}>
            <div style={{ fontSize: 32 }}>⚠️</div>
            <div style={{ color: "#ff6b6b" }}>
               VITE_KAKAO_JS_KEY가 .env에 없습니다
            </div>
            <div style={{ color: "#8b949e", fontSize: 12 }}>
               kakao developers.com → 앱 키 → JavaScript 키
            </div>
         </div>
      );
   }

   return (
      <KakaoLoader
         jsKey={JS_KEY}
         onReady={() => setKakaoReady(true)}
         kakaoReady={kakaoReady}
      />
   );
}

// SDK 로드 로직을 별도 컴포넌트로 분리
function KakaoLoader({ jsKey, onReady, kakaoReady }) {
   const [loadError, setLoadError] = useState(false);

   useEffect(() => {
      // 이미 로드된 경우
      if (window.kakao && window.kakao.maps) {
         window.kakao.maps.load(onReady);
         return;
      }

      const script = document.createElement("script");
      script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${jsKey}&libraries=services,clusterer&autoload=false`;
      script.onload = () => window.kakao.maps.load(onReady);
      // ✅ 에러는 콜백에서 setState → cascading render 없음
      script.onerror = () => setLoadError(true);
      document.head.appendChild(script);
   }, [jsKey, onReady]);

   if (loadError) {
      return (
         <div style={S.center}>
            <div style={{ fontSize: 32 }}>⚠️</div>
            <div style={{ color: "#ff6b6b" }}>카카오맵 SDK 로드 실패</div>
            <div style={{ color: "#8b949e", fontSize: 12 }}>
               JavaScript 키를 확인하세요
            </div>
         </div>
      );
   }

   if (!kakaoReady) {
      return (
         <div style={S.center}>
            <div style={{ fontSize: 32 }}>🗺️</div>
            <div style={{ color: "#555" }}>지도 로딩 중...</div>
         </div>
      );
   }

   return (
      <div style={{ width: "100vw", height: "100vh", margin: 0, padding: 0 }}>
         <MapView />
      </div>
   );
}

const S = {
   center: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      background: "#f5f5f5",
      fontFamily: "monospace",
      flexDirection: "column",
      gap: 12,
   },
};
