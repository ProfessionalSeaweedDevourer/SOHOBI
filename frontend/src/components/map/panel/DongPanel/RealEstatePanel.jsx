import { formatManwon } from "./formatHelpers";

// ── 실거래가 패널 ─────────────────────────────────────────────
// d: { 매매, 전세, 월세, 오피스텔전세, 오피스텔월세, 상업용매매 }
// 서울 열린데이터광장 + 국토부 오피스텔 + 국토부 상업용 통합
export function RealEstatePanel({ d }) {
   return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
         {d?.매매?.건수 > 0 && (
            <div
               style={{ background: "#eff6ff", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#2563eb",
                     marginBottom: 8,
                  }}
               >
                  🏢 매매
               </div>
               <div
                  style={{
                     display: "grid",
                     gridTemplateColumns: "1fr 1fr",
                     gap: 6,
                  }}
               >
                  {[
                     ["건수", `${d.매매.건수}건`],
                     ["평균", d.매매.평균가],
                     ["최저", d.매매.최저가],
                     ["최고", d.매매.최고가],
                  ].map(([k, v]) => (
                     <div key={k}>
                        <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
                        <div
                           style={{
                              fontSize: 12,
                              fontWeight: 700,
                              color: "#1e40af",
                           }}
                        >
                           {typeof v === "number" ? formatManwon(v) : v || "-"}
                        </div>
                     </div>
                  ))}
               </div>
               {d.매매.목록?.slice(0, 3).map((item, i) => (
                  <div
                     key={i}
                     style={{
                        fontSize: 11,
                        color: "#475569",
                        marginTop: 6,
                        lineHeight: 1.5,
                        borderTop: i === 0 ? "1px solid #dbeafe" : "none",
                        paddingTop: i === 0 ? 6 : 0,
                     }}
                  >
                     <span style={{ color: "#94a3b8" }}>
                        {item.계약일?.slice(0, 6)}
                     </span>{" "}
                     <span style={{ fontWeight: 700, color: "#2563eb" }}>
                        {item.거래금액}만원
                     </span>
                     {item.건물명 && (
                        <span style={{ color: "#94a3b8" }}>
                           {" "}
                           · {item.건물명}
                        </span>
                     )}
                     {item.용도 && (
                        <span style={{ color: "#94a3b8", fontSize: 10 }}>
                           {" "}
                           ({item.용도})
                        </span>
                     )}
                  </div>
               ))}
            </div>
         )}
         {d?.전세?.건수 > 0 && (
            <div
               style={{ background: "#f0fdf4", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#059669",
                     marginBottom: 8,
                  }}
               >
                  🔑 전세
               </div>
               <div
                  style={{
                     display: "grid",
                     gridTemplateColumns: "1fr 1fr",
                     gap: 6,
                  }}
               >
                  {[
                     ["건수", `${d.전세.건수}건`],
                     ["평균", d.전세.평균가],
                     ["최저", d.전세.최저가],
                     ["최고", d.전세.최고가],
                  ].map(([k, v]) => (
                     <div key={k}>
                        <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
                        <div
                           style={{
                              fontSize: 12,
                              fontWeight: 700,
                              color: "#065f46",
                           }}
                        >
                           {typeof v === "number" ? formatManwon(v) : v || "-"}
                        </div>
                     </div>
                  ))}
               </div>
            </div>
         )}
         {d?.월세?.건수 > 0 && (
            <div
               style={{ background: "#fefce8", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#a16207",
                     marginBottom: 8,
                  }}
               >
                  💰 월세
               </div>
               <div
                  style={{
                     display: "grid",
                     gridTemplateColumns: "1fr 1fr",
                     gap: 6,
                  }}
               >
                  {[
                     ["건수", `${d.월세.건수}건`],
                     ["평균보증금", d.월세.평균가],
                     ["최저", d.월세.최저가],
                     ["최고", d.월세.최고가],
                  ].map(([k, v]) => (
                     <div key={k}>
                        <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
                        <div
                           style={{
                              fontSize: 12,
                              fontWeight: 700,
                              color: "#92400e",
                           }}
                        >
                           {typeof v === "number" ? formatManwon(v) : v || "-"}
                        </div>
                     </div>
                  ))}
               </div>
            </div>
         )}
         {/* 오피스텔 전세 */}
         {d?.오피스텔전세?.건수 > 0 && (
            <div
               style={{ background: "#f0f9ff", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#0284c7",
                     marginBottom: 8,
                  }}
               >
                  🏢 오피스텔 전세
               </div>
               <div
                  style={{
                     display: "grid",
                     gridTemplateColumns: "1fr 1fr",
                     gap: 6,
                  }}
               >
                  {[
                     ["건수", `${d.오피스텔전세.건수}건`],
                     ["평균", d.오피스텔전세.평균가],
                     ["최저", d.오피스텔전세.최저가],
                     ["최고", d.오피스텔전세.최고가],
                  ].map(([k, v]) => (
                     <div key={k}>
                        <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
                        <div
                           style={{
                              fontSize: 12,
                              fontWeight: 700,
                              color: "#0369a1",
                           }}
                        >
                           {typeof v === "number" ? formatManwon(v) : v || "-"}
                        </div>
                     </div>
                  ))}
               </div>
            </div>
         )}
         {/* 오피스텔 월세 */}
         {d?.오피스텔월세?.건수 > 0 && (
            <div
               style={{ background: "#fefce8", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#a16207",
                     marginBottom: 8,
                  }}
               >
                  🏢 오피스텔 월세
               </div>
               <div
                  style={{
                     display: "grid",
                     gridTemplateColumns: "1fr 1fr",
                     gap: 6,
                  }}
               >
                  {[
                     ["건수", `${d.오피스텔월세.건수}건`],
                     ["평균보증금", d.오피스텔월세.평균보증금],
                     ["평균월세", d.오피스텔월세.평균월세],
                  ].map(
                     ([k, v]) =>
                        v && (
                           <div key={k}>
                              <div style={{ fontSize: 10, color: "#888" }}>
                                 {k}
                              </div>
                              <div
                                 style={{
                                    fontSize: 12,
                                    fontWeight: 700,
                                    color: "#92400e",
                                 }}
                              >
                                 {typeof v === "number"
                                    ? formatManwon(v)
                                    : v || "-"}
                              </div>
                           </div>
                        ),
                  )}
               </div>
            </div>
         )}
         {/* 상업·업무용 매매 */}
         {d?.상업용매매?.건수 > 0 && (
            <div
               style={{ background: "#fdf4ff", borderRadius: 12, padding: 14 }}
            >
               <div
                  style={{
                     fontSize: 11,
                     fontWeight: 700,
                     color: "#7e22ce",
                     marginBottom: 8,
                  }}
               >
                  🏪 상업·업무용 매매
               </div>
               <div
                  style={{
                     display: "grid",
                     gridTemplateColumns: "1fr 1fr",
                     gap: 6,
                  }}
               >
                  {[
                     ["건수", `${d.상업용매매.건수}건`],
                     ["평균", d.상업용매매.평균가],
                     ["최저", d.상업용매매.최저가],
                     ["최고", d.상업용매매.최고가],
                  ].map(([k, v]) => (
                     <div key={k}>
                        <div style={{ fontSize: 10, color: "#888" }}>{k}</div>
                        <div
                           style={{
                              fontSize: 12,
                              fontWeight: 700,
                              color: "#6b21a8",
                           }}
                        >
                           {typeof v === "number" ? formatManwon(v) : v || "-"}
                        </div>
                     </div>
                  ))}
               </div>
            </div>
         )}
         {d?.has_data === false && (
            <div
               style={{
                  color: "#bbb",
                  fontSize: 13,
                  textAlign: "center",
                  marginTop: 20,
               }}
            >
               최근 실거래 데이터 없음
            </div>
         )}
      </div>
   );
}
