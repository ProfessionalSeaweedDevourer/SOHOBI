// components/popup/LandmarkPopup.jsx

const TYPE_STYLE = {
   12: {
      color: "#f59e0b",
      bg: "#fffbeb",
      label: "🏛️ 관광지",
      border: "#fcd34d",
   },
   14: {
      color: "#8b5cf6",
      bg: "#f5f3ff",
      label: "🎭 문화시설",
      border: "#c4b5fd",
   },
   15: { color: "#ef4444", bg: "#fef2f2", label: "🎉 축제", border: "#fca5a5" },
   school: {
      color: "#10b981",
      bg: "#f0fdf4",
      label: "🏫 학교",
      border: "#6ee7b7",
   },
};

function getTypeStyle(typeKey) {
   return TYPE_STYLE[String(typeKey)] || TYPE_STYLE["12"];
}

export default function LandmarkPopup({ popup, onClose }) {
   if (!popup) return null;

   const isSchool = popup._type === "school";
   const typeKey = isSchool ? "school" : String(popup.content_type_id || "12");
   const ts = getTypeStyle(typeKey);

   return (
      <div
         style={{
            position: "absolute",
            bottom: 50,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 300,
            width: 320,
            background: "#fff",
            borderRadius: 16,
            boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
            overflow: "hidden",
         }}
      >
         {/* 상단 컬러 바 */}
         <div style={{ height: 4, background: ts.color }} />

         {/* 이미지 (랜드마크만) */}
         {!isSchool && popup.image && (
            <div
               style={{
                  width: "100%",
                  height: 160,
                  overflow: "hidden",
                  background: "#f3f4f6",
               }}
            >
               <img
                  src={popup.image}
                  alt={popup.title}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  onError={(e) => {
                     e.target.style.display = "none";
                  }}
               />
            </div>
         )}

         <div style={{ padding: "12px 16px 16px" }}>
            {/* 헤더 */}
            <div
               style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
               }}
            >
               <div
                  style={{
                     borderRadius: 20,
                     padding: "3px 10px",
                     fontSize: 11,
                     fontWeight: 700,
                     background: ts.bg,
                     color: ts.color,
                     border: `1px solid ${ts.border}`,
                  }}
               >
                  {ts.label}
               </div>
               <button
                  onClick={onClose}
                  style={{
                     background: "transparent",
                     border: "none",
                     color: "#bbb",
                     cursor: "pointer",
                     fontSize: 16,
                  }}
               >
                  ✕
               </button>
            </div>

            {/* 이름 */}
            <div
               style={{
                  fontSize: 17,
                  fontWeight: 700,
                  color: "#111",
                  marginBottom: 4,
               }}
            >
               {isSchool ? popup.school_nm : popup.title}
            </div>

            {/* 학교 타입 */}
            {isSchool && popup.school_type && (
               <div style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>
                  {popup.school_type}
                  {popup.found_type && ` · ${popup.found_type}`}
               </div>
            )}

            <div
               style={{ height: 1, background: "#f0f0f0", margin: "10px 0" }}
            />

            {/* 정보 rows */}
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
               {(popup.addr || popup.road_addr || popup.addr1) && (
                  <Row
                     icon="📍"
                     text={popup.addr || popup.road_addr || popup.addr1}
                  />
               )}
               {popup.tel && (
                  <Row
                     icon="📞"
                     text={
                        <a
                           href={`tel:${popup.tel}`}
                           style={{ color: "#2563eb", textDecoration: "none" }}
                        >
                           {popup.tel}
                        </a>
                     }
                  />
               )}
               {popup.homepage && (
                  <Row
                     icon="🌐"
                     text={
                        <a
                           href={
                              popup.homepage.startsWith("http")
                                 ? popup.homepage
                                 : `http://${popup.homepage}`
                           }
                           target="_blank"
                           rel="noreferrer"
                           style={{
                              color: "#2563eb",
                              textDecoration: "none",
                              wordBreak: "break-all",
                              fontSize: 12,
                           }}
                        >
                           {popup.homepage
                              .replace(/^https?:\/\//, "")
                              .slice(0, 40)}
                           {popup.homepage.length > 50 ? "..." : ""}
                        </a>
                     }
                  />
               )}
               {popup.start_date && (
                  <Row
                     icon="📅"
                     text={`${popup.start_date} ~ ${popup.end_date || ""}`}
                  />
               )}
               {isSchool && popup.found_date && (
                  <Row icon="📅" text={`개교: ${popup.found_date}`} />
               )}
            </div>

            {/* 개요 */}
            {!isSchool && popup.overview && (
               <div
                  style={{
                     marginTop: 10,
                     padding: "10px 12px",
                     background: ts.bg,
                     borderRadius: 10,
                     fontSize: 12,
                     color: "#555",
                     lineHeight: 1.6,
                     maxHeight: 80,
                     overflow: "hidden",
                     display: "-webkit-box",
                     WebkitLineClamp: 4,
                     WebkitBoxOrient: "vertical",
                  }}
               >
                  {popup.overview}
               </div>
            )}
         </div>
      </div>
   );
}

function Row({ icon, text }) {
   return (
      <div style={{ display: "flex", alignItems: "flex-start", gap: 7 }}>
         <span style={{ fontSize: 13, flexShrink: 0, marginTop: 1 }}>
            {icon}
         </span>
         <span style={{ fontSize: 13, color: "#444", lineHeight: 1.4 }}>
            {text}
         </span>
      </div>
   );
}
