// 위치: src/components/panel/DongPanel.jsx


// ── 금액 포맷 헬퍼 ─────────────────────────────────────────────
function formatAmt(v) {
   if (!v || v === 0) return "-";
   if (v >= 1e8) return `${(v / 1e8).toFixed(1)}억`;
   if (v >= 1e4) return `${Math.round(v / 1e4)}만`;
   return `${v}`;
}


// ── 막대 차트 행 컴포넌트 ─────────────────────────────────────
function BarRow({ label, val, total, color }) {
   const pct = total > 0 ? Math.round((val / total) * 100) : 0;
   return (
      <div style={{ marginBottom: 8 }}>
         <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:3 }}>
            <span>{label}</span>
            <span style={{ fontWeight:700 }}>{formatAmt(val)} ({pct}%)</span>
         </div>
         <div style={{ height:6, background:"#e2e8f0", borderRadius:3, overflow:"hidden" }}>
            <div style={{ width:`${pct}%`, height:"100%", background:color, borderRadius:3 }} />
         </div>
      </div>
   );
}


// ── 실거래가 패널 ────────────────────────────────────────────
function RealEstatePanel({ d }) {
   return (
      <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
         {d?.매매?.건수 > 0 && (
            <div style={{ background:"#eff6ff", borderRadius:12, padding:14 }}>
               <div style={{ fontSize:11, fontWeight:700, color:"#2563eb", marginBottom:8 }}>🏢 매매</div>
               <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
                  {[["건수",`${d.매매.건수}건`],["평균",d.매매.평균가],["최저",d.매매.최저가],["최고",d.매매.최고가]].map(([k,v]) => (
                     <div key={k}>
                        <div style={{ fontSize:10, color:"#888" }}>{k}</div>
                        <div style={{ fontSize:12, fontWeight:700, color:"#1e40af" }}>{v||"-"}</div>
                     </div>
                  ))}
               </div>
               {d.매매.목록?.slice(0,3).map((item,i) => (
                  <div key={i} style={{ fontSize:11, color:"#475569", marginTop:6, lineHeight:1.5,
                     borderTop:i===0?"1px solid #dbeafe":"none", paddingTop:i===0?6:0 }}>
                     <span style={{ color:"#94a3b8" }}>{item.계약일?.slice(0,6)}</span>
                     {" "}<span style={{ fontWeight:700, color:"#2563eb" }}>{item.거래금액}만원</span>
                     {item.건물명 && <span style={{ color:"#94a3b8" }}> · {item.건물명}</span>}
                     {item.용도   && <span style={{ color:"#94a3b8", fontSize:10 }}> ({item.용도})</span>}
                  </div>
               ))}
            </div>
         )}
         {d?.전세?.건수 > 0 && (
            <div style={{ background:"#f0fdf4", borderRadius:12, padding:14 }}>
               <div style={{ fontSize:11, fontWeight:700, color:"#059669", marginBottom:8 }}>🔑 전세</div>
               <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
                  {[["건수",`${d.전세.건수}건`],["평균",d.전세.평균가],["최저",d.전세.최저가],["최고",d.전세.최고가]].map(([k,v]) => (
                     <div key={k}>
                        <div style={{ fontSize:10, color:"#888" }}>{k}</div>
                        <div style={{ fontSize:12, fontWeight:700, color:"#065f46" }}>{v||"-"}</div>
                     </div>
                  ))}
               </div>
            </div>
         )}
         {d?.월세?.건수 > 0 && (
            <div style={{ background:"#fefce8", borderRadius:12, padding:14 }}>
               <div style={{ fontSize:11, fontWeight:700, color:"#a16207", marginBottom:4 }}>💰 월세</div>
               <div style={{ fontSize:12, color:"#854d0e" }}>{d.월세.건수}건</div>
            </div>
         )}
         {d?.has_data === false && (
            <div style={{ color:"#bbb", fontSize:13, textAlign:"center", marginTop:20 }}>
               최근 3년 실거래 데이터 없음
            </div>
         )}
      </div>
   );
}


// ── 매출 패널 ───────────────────────────────────────────────
function SalesPanel({ d, panelColor, panelBg }) {
   return (
      <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
         <div style={{ background:panelBg, borderRadius:12, padding:14 }}>
            <div style={{ fontSize:10, color:"#888", marginBottom:4 }}>총 매출</div>
            <div style={{ fontSize:22, fontWeight:800, color:panelColor }}>{formatAmt(d.sales)}</div>
            <div style={{ fontSize:11, color:"#64748b", marginTop:2 }}>
               점포수 {d.selng_co?.toLocaleString() || "-"}개
               {d.quarter && ` · ${String(d.quarter).replace(/(\d{4})(\d)/, "$1년 $2분기")}`}
            </div>
         </div>

         <div style={{ background:"#f8fafc", borderRadius:12, padding:14 }}>
            <div style={{ fontSize:11, fontWeight:700, color:"#475569", marginBottom:8 }}>📅 주중/주말</div>
            <BarRow label="주중" val={d.sales_mdwk}  total={d.sales} color="#3b82f6" />
            <BarRow label="주말" val={d.sales_wkend} total={d.sales} color="#8b5cf6" />
         </div>

         <div style={{ background:"#f8fafc", borderRadius:12, padding:14 }}>
            <div style={{ fontSize:11, fontWeight:700, color:"#475569", marginBottom:8 }}>👤 성별 매출</div>
            <BarRow label="남성" val={d.sales_male}   total={d.sales} color="#2563eb" />
            <BarRow label="여성" val={d.sales_female} total={d.sales} color="#ec4899" />
         </div>

         {(d.age20 || d.age30 || d.age40 || d.age50) && (
            <div style={{ background:"#f8fafc", borderRadius:12, padding:14 }}>
               <div style={{ fontSize:11, fontWeight:700, color:"#475569", marginBottom:8 }}>🎂 연령대 매출</div>
               {[["20대",d.age20],["30대",d.age30],["40대",d.age40],["50대",d.age50]].map(([label,val]) => {
                  const pct = d.sales > 0 ? Math.round(((val||0)/d.sales)*100) : 0;
                  return (
                     <div key={label} style={{ marginBottom:6 }}>
                        <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:2 }}>
                           <span>{label}</span>
                           <span style={{ fontWeight:700 }}>{formatAmt(val)} ({pct}%)</span>
                        </div>
                        <div style={{ height:5, background:"#e2e8f0", borderRadius:3, overflow:"hidden" }}>
                           <div style={{ width:`${pct}%`, height:"100%", background:"#059669", borderRadius:3 }} />
                        </div>
                     </div>
                  );
               })}
            </div>
         )}
      </div>
   );
}


// ── 메인 컴포넌트: 동 클릭 시 오른쪽 슬라이드 패널 ───────────
export default function DongPanel({ dongPanel, onClose }) {
   if (!dongPanel) return null;

   const d          = dongPanel.apiData;
   const isRE       = dongPanel.mode === "realestate";
   const panelColor = isRE ? "#2563EB" : "#059669";
   const panelBg    = isRE ? "#eff6ff" : "#f0fdf4";

   return (
      <div className="mv-dong-panel">
         <div className="mv-dong-panel__header" style={{ background: panelColor }}>
            <div className="mv-dong-panel__header-row">
               <div>
                  <div className="mv-dong-panel__gu">{dongPanel.admNm}</div>
                  <div className="mv-dong-panel__name">{dongPanel.dongNm}</div>
               </div>
               <button onClick={onClose} className="mv-dong-panel__close">✕</button>
            </div>
            <div className="mv-dong-panel__mode-label">
               {isRE ? "🏢 실거래가 분석" : "📊 상권 매출 분석"}
            </div>
         </div>

         <div className="mv-dong-panel__body">
            {!d ? (
               <div style={{ color:"#bbb", fontSize:13, textAlign:"center", marginTop:40 }}>
                  데이터 없음
               </div>
            ) : isRE ? (
               <RealEstatePanel d={d} />
            ) : (
               <SalesPanel d={d} panelColor={panelColor} panelBg={panelBg} />
            )}
         </div>
      </div>
   );
}