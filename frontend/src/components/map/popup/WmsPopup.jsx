// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\popup\WmsPopup.jsx
// 공식 프론트 위치: frontend\src\components\map\popup\WmsPopup.jsx

// 카카오 연동: 앱 링크(kakaomap://place) 우선, 없으면 웹 링크
import { LAYER_META } from "../../../hooks/map/useWmsClick";
import "./WmsPopup.css";

// ── 카카오맵 웹 링크 생성 ──────────────────────────────────────
function kakaoWebLink(name, address) {
  const query = encodeURIComponent(address ? `${address} ${name}` : name);
  return `https://map.kakao.com/?q=${query}`;
}

// ── 공통 정보 행 컴포넌트 ─────────────────────────────────────
function InfoRow({ icon, children }) {
  if (!children) return null;
  return (
    <div className="wp-row">
      <span className="wp-row-icon">{icon}</span>
      <span className="wp-row-text">{children}</span>
    </div>
  );
}

// ── 지적도 팝업 내용 ─────────────────────────────────────────
function CadastralContent({ wmsPopup, landValue }) {
  return (
    <>
      <div className="wp-title">{wmsPopup.addr || "주소 없음"}</div>
      <div className="wp-divider" />
      <div className="wp-rows">
        {wmsPopup.sido && (
          <InfoRow icon="🏙️">
            {wmsPopup.sido} {wmsPopup.sigg} {wmsPopup.dong}
          </InfoRow>
        )}
        {wmsPopup.jibun && <InfoRow icon="📋">지번: {wmsPopup.jibun}</InfoRow>}
        {wmsPopup.pnu && <InfoRow icon="🔑">PNU: {wmsPopup.pnu}</InfoRow>}
      </div>
      <div className="wp-divider" />
      {landValue?.length > 0 ? (
        <div className="wp-landval">
          <div className="wp-landval-title">
            🏷️ 개별공시지가 · {landValue[0].label || `${landValue[0].year}년 기준`}
          </div>
          {landValue.slice(0, 3).map((lv, i) => (
            <div key={i} className="wp-landval-row">
              <span className="wp-landval-year">
                {lv.year}년{lv.month ? ` ${lv.month}월` : ""}
              </span>
              <b className="wp-landval-price">{lv.price_str}</b>
            </div>
          ))}
        </div>
      ) : wmsPopup.pnu ? (
        <div className="wp-empty">공시지가 정보 없음</div>
      ) : (
        <div className="wp-empty">
          지적도 레이어를 활성화하면
          <br />
          공시지가를 조회할 수 있습니다
        </div>
      )}
    </>
  );
}

// ── 관광지/시장 팝업 내용 + 카카오맵 링크 ────────────────────
function PlaceContent({ wmsPopup }) {
  const webLink = kakaoWebLink(wmsPopup.name, wmsPopup.addr);

  return (
    <>
      <div className="wp-title">{wmsPopup.name}</div>
      <div className="wp-divider" />
      <div className="wp-rows">
        {wmsPopup.sido && (
          <InfoRow icon="🏙️">
            {wmsPopup.sido} {wmsPopup.sigg}
          </InfoRow>
        )}
        {wmsPopup.addr && <InfoRow icon="📍">{wmsPopup.addr}</InfoRow>}
        {wmsPopup.tel && (
          <div className="wp-row">
            <span className="wp-row-icon">📞</span>
            <a href={`tel:${wmsPopup.tel}`} className="wp-link">
              {wmsPopup.tel}
            </a>
          </div>
        )}
        {wmsPopup.hours && <InfoRow icon="🕐">{wmsPopup.hours}</InfoRow>}
        {wmsPopup.remark && <InfoRow icon="📝">{wmsPopup.remark}</InfoRow>}
      </div>

      {/* 카카오맵 웹 링크 (앱 스킴 제거 - 브라우저 오류 방지) */}
      <a href={webLink} target="_blank" rel="noreferrer" className="wp-kakao-btn">
        카카오맵에서 보기 →
      </a>
    </>
  );
}

// ── 메인 컴포넌트: WMS 레이어 클릭 팝업 ──────────────────────
export default function WmsPopup({ wmsPopup, landValue, onClose, onBack, hasDongPanel, chatOpen }) {
  if (!wmsPopup) return null;
  const meta = LAYER_META[wmsPopup.type] || LAYER_META.cadastral;

  return (
    <div
      className={`mv-wms-popup${hasDongPanel ? " mv-wms-popup--dong-open" : ""}${chatOpen ? " mv-wms-popup--chat-open" : ""}`}
    >
      <div style={{ height: 4, background: meta.color }} />
      <div className="wp-body">
        <div className="wp-top">
          <div className="wp-top-left">
            {onBack && (
              <button onClick={onBack} className="wp-back-btn">
                ←
              </button>
            )}
            <div
              className="wp-tag"
              style={{
                background: meta.bg,
                color: meta.color,
                border: `1px solid ${meta.color}`,
              }}
            >
              {meta.icon} {meta.label}
            </div>
          </div>
          <button onClick={onClose} className="wp-close-btn">
            ✕
          </button>
        </div>

        {wmsPopup.type === "cadastral" ? (
          <CadastralContent wmsPopup={wmsPopup} landValue={landValue} />
        ) : (
          <PlaceContent wmsPopup={wmsPopup} />
        )}
      </div>
    </div>
  );
}
