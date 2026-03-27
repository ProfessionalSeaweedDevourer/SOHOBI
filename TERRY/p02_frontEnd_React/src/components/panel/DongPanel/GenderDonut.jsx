import { formatAmt } from "./formatHelpers";

// GenderDonut: SVG 도넛 차트 - 남성(#2563eb) / 여성(#ec4899)
// male/female: 원 금액 (만원 단위 아님, formatAmt으로 표시)
export function GenderDonut({ male, female }) {
   const total = (male || 0) + (female || 0);
   if (!total) return null;
   const malePct = Math.round(((male || 0) / total) * 100);
   const femalePct = 100 - malePct;
   // SVG 도넛: cx=50 cy=50 r=36 (둘레 ≈ 226)
   const R = 36,
      CX = 50,
      CY = 50;
   const circ = 2 * Math.PI * R;
   const maleDash = (malePct / 100) * circ;
   const femaleDash = circ - maleDash;
   return (
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
         <svg width="90" height="90" viewBox="0 0 100 100">
            {/* 여성 (배경) */}
            <circle
               cx={CX}
               cy={CY}
               r={R}
               fill="none"
               stroke="#fce7f3"
               strokeWidth="14"
            />
            {/* 남성 */}
            <circle
               cx={CX}
               cy={CY}
               r={R}
               fill="none"
               stroke="#2563eb"
               strokeWidth="14"
               strokeDasharray={`${maleDash} ${femaleDash}`}
               strokeDashoffset={circ * 0.25}
               strokeLinecap="round"
            />
            {/* 여성 위에 덮기 */}
            <circle
               cx={CX}
               cy={CY}
               r={R}
               fill="none"
               stroke="#ec4899"
               strokeWidth="14"
               strokeDasharray={`${femaleDash} ${maleDash}`}
               strokeDashoffset={circ * 0.25 - maleDash}
               strokeLinecap="round"
            />
            <text
               x={CX}
               y={CY - 5}
               textAnchor="middle"
               fontSize="13"
               fontWeight="700"
               fill="#1e293b"
            >
               {malePct}%
            </text>
            <text
               x={CX}
               y={CY + 10}
               textAnchor="middle"
               fontSize="9"
               fill="#64748b"
            >
               남성
            </text>
         </svg>
         <div
            style={{
               display: "flex",
               flexDirection: "column",
               gap: 8,
               flex: 1,
            }}
         >
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
               <div
                  style={{
                     width: 10,
                     height: 10,
                     borderRadius: "50%",
                     background: "#2563eb",
                     flexShrink: 0,
                  }}
               />
               <span style={{ fontSize: 12 }}>남성</span>
               <span
                  style={{
                     marginLeft: "auto",
                     fontWeight: 700,
                     fontSize: 12,
                     color: "#2563eb",
                  }}
               >
                  {malePct}% ({formatAmt(male)})
               </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
               <div
                  style={{
                     width: 10,
                     height: 10,
                     borderRadius: "50%",
                     background: "#ec4899",
                     flexShrink: 0,
                  }}
               />
               <span style={{ fontSize: 12 }}>여성</span>
               <span
                  style={{
                     marginLeft: "auto",
                     fontWeight: 700,
                     fontSize: 12,
                     color: "#ec4899",
                  }}
               >
                  {femalePct}% ({formatAmt(female)})
               </span>
            </div>
         </div>
      </div>
   );
}
