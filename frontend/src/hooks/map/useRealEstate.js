// 개발 프론트 위치: TERRY\p02_frontEnd_React\src\hooks\useRealEstate.js
// 공식 프론트 위치: frontend\src\hooks\map\useRealEstate.js

// 실거래가 + 공실 API 연동 훅

const REALESTATE_URL = "http://localhost:8682";

/**
 * 시군구명 + 시도명 추출 (popup 객체에서)
 * popup = { 시군구명: '강남구', 시도명: '서울특별시', ... }
 */
export async function fetchRealEstateAnalysis(sigungu, sido = null) {
   if (!sigungu) return null;
   try {
      const params = new URLSearchParams({ sigungu });
      if (sido) params.append("sido", sido);
      const res = await fetch(
         `${REALESTATE_URL}/realestate/analysis?${params}`,
      );
      return await res.json();
   } catch (e) {
      console.error("실거래가 조회 오류:", e);
      return null;
   }
}

export async function fetchCommercial(sigungu, yearmonth) {
   try {
      const res = await fetch(
         `${REALESTATE_URL}/realestate/commercial?sigungu=${sigungu}&yearmonth=${yearmonth}`,
      );
      return await res.json();
   } catch (e) {
      console.error("오류:", e);
      return null;
   }
}

export async function fetchVacancy(sigungu) {
   try {
      const res = await fetch(
         `${REALESTATE_URL}/realestate/vacancy?sigungu=${sigungu}`,
      );
      return await res.json();
   } catch (e) {
      console.error("오류:", e);
      return null;
   }
}
