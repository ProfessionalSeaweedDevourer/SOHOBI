// components/WmsPopup.jsx
// 카카오 연동: 앱 링크(kakaomap://place) 우선, 없으면 웹 링크
import { LAYER_META } from "../../../hooks/map/useWmsClick";


// ── 카카오맵 딥링크 생성 ──────────────────────────────────────
function kakaoMapLink(name, address) {
   // 카카오맵 앱 검색 딥링크
   const query = encodeURIComponent(address ? `${address} ${name}` : name);
   return `kakaomap://search?q=${query}`;
}

function kakaoWebLink(name, address) {
   const query = encodeURIComponent(address ? `${address} ${name}` : name);
   return `https://map.kakao.com/?q=${query}`;
}


// ── 공통 정보 행 컴포넌트 ─────────────────────────────────────
function InfoRow({ icon, children }) {
   if (!children) return null;
   return (
      <div style={{ display:"flex", alignItems:"flex-start", gap:7 }}>
         <span style={{ fontSize:13, flexShrink:0, marginTop:1 }}>{icon}</span>
         <span style={{ fontSize:13, color:"#444", lineHeight:1.4 }}>{children}</span>
      </div>
   );
}


// ── 지적도 팝업 내용 ─────────────────────────────────────────
function CadastralContent({ wmsPopup, landValue }) {
   return (
      <>
         <div style={{ fontSize:17, fontWeight:700, color:"#111", marginBottom:4 }}>
            {wmsPopup.addr || "주소 없음"}
         </div>
         <div style={{ height:1, background:"#f0f0f0", margin:"10px 0" }} />
         <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
            {wmsPopup.sido && <InfoRow icon="🏙️">{wmsPopup.sido} {wmsPopup.sigg} {wmsPopup.dong}</InfoRow>}
            {wmsPopup.jibun && <InfoRow icon="📋">지번: {wmsPopup.jibun}</InfoRow>}
            {wmsPopup.pnu   && <InfoRow icon="🔑">PNU: {wmsPopup.pnu}</InfoRow>}
         </div>
         <div style={{ height:1, background:"#f0f0f0", margin:"10px 0" }} />
         {landValue?.length > 0 ? (
            <div style={{ background:"#f0fdf4", border:"1px solid #bbf7d0", borderRadius:10, padding:"10px 12px" }}>
               <div style={{ fontSize:11, fontWeight:700, color:"#166534", marginBottom:6 }}>
                  🏷️ 개별공시지가 · {landValue[0].label || `${landValue[0].year}년 기준`}
               </div>
               {landValue.slice(0,3).map((lv,i) => (
                  <div key={i} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", fontSize:12, marginBottom:3 }}>
                     <span style={{ color:"#4b7c5e" }}>{lv.year}년{lv.month ? ` ${lv.month}월` : ""}</span>
                     <b style={{ color:"#14532d", fontSize:14 }}>{lv.price_str}</b>
                  </div>
               ))}
            </div>
         ) : wmsPopup.pnu ? (
            <div style={{ fontSize:11, color:"#bbb", textAlign:"center" }}>공시지가 정보 없음</div>
         ) : null}
      </>
   );
}


// ── 관광지/시장 팝업 내용 + 카카오맵 링크 ────────────────────
function PlaceContent({ wmsPopup }) {
   const appLink = kakaoMapLink(wmsPopup.name, wmsPopup.addr);
   const webLink = kakaoWebLink(wmsPopup.name, wmsPopup.addr);

   return (
      <>
         <div style={{ fontSize:17, fontWeight:700, color:"#111", marginBottom:4 }}>
            {wmsPopup.name}
         </div>
         <div style={{ height:1, background:"#f0f0f0", margin:"10px 0" }} />
         <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
            {wmsPopup.sido && <InfoRow icon="🏙️">{wmsPopup.sido} {wmsPopup.sigg}</InfoRow>}
            {wmsPopup.addr && <InfoRow icon="📍">{wmsPopup.addr}</InfoRow>}
            {wmsPopup.tel  && (
               <div style={{ display:"flex", alignItems:"flex-start", gap:7 }}>
                  <span style={{ fontSize:13, flexShrink:0, marginTop:1 }}>📞</span>
                  <a href={`tel:${wmsPopup.tel}`} style={{ fontSize:13, color:"#2563eb", textDecoration:"none" }}>
                     {wmsPopup.tel}
                  </a>
               </div>
            )}
            {wmsPopup.hours  && <InfoRow icon="🕐">{wmsPopup.hours}</InfoRow>}
            {wmsPopup.remark && <InfoRow icon="📝">{wmsPopup.remark}</InfoRow>}
         </div>

         {/* 카카오맵 링크 */}
         <div style={{ marginTop:12, display:"flex", gap:8 }}>
            {/* 앱 링크 (모바일) */}
            <a
               href={appLink}
               style={{
                  flex:1, display:"flex", justifyContent:"center", alignItems:"center",
                  background:"#fee500", borderRadius:10, padding:"9px",
                  fontSize:12, fontWeight:700, color:"#111", textDecoration:"none",
               }}
            >
               📱 카카오맵 앱
            </a>
            {/* 웹 링크 (PC) */}
            <a
               href={webLink}
               target="_blank"
               rel="noreferrer"
               style={{
                  flex:1, display:"flex", justifyContent:"center", alignItems:"center",
                  background:"#f5f5f5", borderRadius:10, padding:"9px",
                  fontSize:12, fontWeight:700, color:"#333", textDecoration:"none",
               }}
            >
               🌐 웹에서 보기
            </a>
         </div>
      </>
   );
}


// ── 메인 컴포넌트: WMS 레이어 클릭 팝업 ──────────────────────
export default function WmsPopup({ wmsPopup, landValue, onClose }) {
   if (!wmsPopup) return null;
   const meta = LAYER_META[wmsPopup.type] || LAYER_META.cadastral;

   return (
      <div className="mv-wms-popup">
         <div style={{ height:4, background:meta.color }} />
         <div style={{ padding:"12px 16px 16px" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
               <div style={{
                  borderRadius:20, padding:"3px 10px", fontSize:11, fontWeight:700,
                  background:meta.bg, color:meta.color, border:`1px solid ${meta.color}`,
               }}>
                  {meta.icon} {meta.label}
               </div>
               <button
                  onClick={onClose}
                  style={{ background:"transparent", border:"none", color:"#bbb", cursor:"pointer", fontSize:16 }}
               >
                  ✕
               </button>
            </div>

            {wmsPopup.type === "cadastral"
               ? <CadastralContent wmsPopup={wmsPopup} landValue={landValue} />
               : <PlaceContent wmsPopup={wmsPopup} />
            }
         </div>
      </div>
   );
}