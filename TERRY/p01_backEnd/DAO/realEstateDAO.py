# 위치: p01_backEnd/DAO/realEstateDAO.py
# 실거래가 · 유동인구 · 관광 · 상권 · 공시지가 외부 API 호출 로직
# Controller에서 import해서 사용

import os
import math
import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── API 키 ──────────────────────────────────────────────────────────
_DEFAULT_KEY = "b7906dd729da8d6d4f67bd6bed484f032f9f586abc7b382b41b93a003949385e"
_DEFAULT_POP = "537a7a50717773743131306a49616d76"

MOLIT_OP_KEY       = os.getenv("MOLIT_OP_API_KEY",       _DEFAULT_KEY)
MOLIT_NRG_KEY      = os.getenv("MOLIT_NRG_API_KEY",      _DEFAULT_KEY)
SEOUL_POP_KEY      = os.getenv("SEOUL_POP_API_KEY",       _DEFAULT_POP)
SEOUL_SANGKWON_KEY = os.getenv("SEOUL_SANGKWON_API_KEY",  _DEFAULT_POP)
TOUR_KOR_KEY       = os.getenv("TOUR_KOR_API_KEY",        _DEFAULT_KEY)
TOUR_PHOTO_KEY     = os.getenv("TOUR_PHOTO_API_KEY",      _DEFAULT_KEY)
VWORLD_KEY         = os.getenv("VWORLD_API_KEY",          "BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF")

print(f"[realEstateDAO] TOUR_KOR={TOUR_KOR_KEY[:8]}... / PHOTO={TOUR_PHOTO_KEY[:8]}...")

# ── 시군구 코드 매핑 ────────────────────────────────────────────────
SIGUNGU_CODE_MAP = {
    # 서울
    "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
    "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
    "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
    "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
    "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
    "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710",
    "강동구": "11740",
    # 경기
    "수원시": "41110", "성남시": "41130", "의정부시": "41150", "안양시": "41170",
    "부천시": "41190", "광명시": "41210", "평택시": "41220", "동두천시": "41250",
    "안산시": "41270", "고양시": "41280", "과천시": "41290", "구리시": "41310",
    "남양주시": "41360", "오산시": "41370", "시흥시": "41390", "군포시": "41410",
    "의왕시": "41430", "하남시": "41450", "용인시": "41460", "파주시": "41480",
    "이천시": "41500", "안성시": "41550", "김포시": "41570", "화성시": "41590",
    "광주시": "41610", "양주시": "41630", "포천시": "41650", "여주시": "41670",
    # 부산
    "중구": "26110", "서구": "26140", "동구": "26170", "영도구": "26200",
    "부산진구": "26230", "동래구": "26260", "남구": "26290", "북구": "26320",
    "해운대구": "26350", "사하구": "26380", "금정구": "26410", "강서구": "26440",
    "연제구": "26470", "수영구": "26500", "사상구": "26530", "기장군": "26710",
    # 인천
    "중구": "28110", "동구": "28140", "미추홀구": "28177", "연수구": "28185",
    "남동구": "28200", "부평구": "28237", "계양구": "28245", "서구": "28260",
    "강화군": "28710", "옹진군": "28720",
    # 대구
    "중구": "27110", "동구": "27140", "서구": "27170", "남구": "27200",
    "북구": "27230", "수성구": "27260", "달서구": "27290", "달성군": "27710",
    # 대전
    "동구": "30110", "중구": "30140", "서구": "30170", "유성구": "30200", "대덕구": "30230",
    # 광주
    "동구": "29110", "서구": "29140", "남구": "29155", "북구": "29170", "광산구": "29200",
    # 울산
    "중구": "31110", "남구": "31140", "동구": "31170", "북구": "31200", "울주군": "31710",
    # 세종
    "세종시": "36110",
    # 강원
    "춘천시": "42110", "원주시": "42130", "강릉시": "42150", "동해시": "42170",
    "태백시": "42190", "속초시": "42210", "삼척시": "42230",
    # 충북
    "청주시": "43110", "충주시": "43130", "제천시": "43150",
    # 충남
    "천안시": "44130", "공주시": "44150", "보령시": "44180", "아산시": "44200",
    "서산시": "44210", "논산시": "44230", "계룡시": "44250", "당진시": "44270",
    # 전북
    "전주시": "45110", "군산시": "45130", "익산시": "45140", "정읍시": "45180",
    "남원시": "45190", "김제시": "45210",
    # 전남
    "목포시": "46110", "여수시": "46130", "순천시": "46150", "나주시": "46170",
    "광양시": "46230",
    # 경북
    "포항시": "47110", "경주시": "47130", "김천시": "47150", "안동시": "47170",
    "구미시": "47190", "영주시": "47210", "영천시": "47230", "상주시": "47250",
    "문경시": "47280", "경산시": "47290",
    # 경남
    "창원시": "48120", "진주시": "48170", "통영시": "48220", "사천시": "48240",
    "김해시": "48250", "밀양시": "48270", "거제시": "48310", "양산시": "48330",
    "의령군": "48730", "함안군": "48740", "창녕군": "48750", "고성군": "48820",
    "남해군": "48840", "하동군": "48850", "산청군": "48860", "함양군": "48870",
    "거창군": "48880", "합천군": "48890",
    # 제주
    "제주시": "50110", "서귀포시": "50130",
}

# ── 서울 유동인구 주요 장소 ─────────────────────────────────────────
SEOUL_PLACES = {
    "POI001": {"name": "광화문·덕수궁",     "gu": "종로구",   "lat": 37.5710, "lng": 126.9769},
    "POI013": {"name": "북촌한옥마을",       "gu": "종로구",   "lat": 37.5829, "lng": 126.9837},
    "POI014": {"name": "인사동·익선동",      "gu": "종로구",   "lat": 37.5742, "lng": 126.9858},
    "POI015": {"name": "낙산공원·이화마을",  "gu": "종로구",   "lat": 37.5796, "lng": 127.0063},
    "POI021": {"name": "창덕궁·창경궁",     "gu": "종로구",   "lat": 37.5793, "lng": 126.9910},
    "POI022": {"name": "경복궁",             "gu": "종로구",   "lat": 37.5796, "lng": 126.9770},
    "POI003": {"name": "명동·남대문·북창",   "gu": "중구",     "lat": 37.5638, "lng": 126.9826},
    "POI023": {"name": "을지로·명동",        "gu": "중구",     "lat": 37.5660, "lng": 126.9837},
    "POI024": {"name": "남산공원",           "gu": "중구",     "lat": 37.5511, "lng": 126.9882},
    "POI002": {"name": "서울역 일대",        "gu": "중구",     "lat": 37.5549, "lng": 126.9708},
    "POI007": {"name": "이태원 관광특구",    "gu": "용산구",   "lat": 37.5348, "lng": 126.9944},
    "POI025": {"name": "용산역 일대",        "gu": "용산구",   "lat": 37.5298, "lng": 126.9647},
    "POI026": {"name": "한남동",             "gu": "용산구",   "lat": 37.5345, "lng": 127.0001},
    "POI011": {"name": "성수카페거리",       "gu": "성동구",   "lat": 37.5443, "lng": 127.0557},
    "POI027": {"name": "왕십리역 일대",      "gu": "성동구",   "lat": 37.5612, "lng": 127.0374},
    "POI018": {"name": "왕십리역",           "gu": "성동구",   "lat": 37.5612, "lng": 127.0374},
    "POI012": {"name": "건대입구역",         "gu": "광진구",   "lat": 37.5403, "lng": 127.0694},
    "POI028": {"name": "구의·자양",          "gu": "광진구",   "lat": 37.5374, "lng": 127.0836},
    "POI009": {"name": "동대문 관광특구",    "gu": "동대문구", "lat": 37.5663, "lng": 127.0098},
    "POI029": {"name": "회기역 일대",        "gu": "동대문구", "lat": 37.5895, "lng": 127.0567},
    "POI030": {"name": "성신여대입구역",     "gu": "성북구",   "lat": 37.5927, "lng": 127.0165},
    "POI031": {"name": "고려대 일대",        "gu": "성북구",   "lat": 37.5892, "lng": 127.0321},
    "POI019": {"name": "수유역",             "gu": "강북구",   "lat": 37.6388, "lng": 127.0255},
    "POI020": {"name": "미아사거리역",       "gu": "강북구",   "lat": 37.6130, "lng": 127.0303},
    "POI032": {"name": "노원역 일대",        "gu": "노원구",   "lat": 37.6549, "lng": 127.0561},
    "POI033": {"name": "중계동 학원가",      "gu": "노원구",   "lat": 37.6337, "lng": 127.0710},
    "POI034": {"name": "연신내역",           "gu": "은평구",   "lat": 37.6190, "lng": 126.9208},
    "POI035": {"name": "불광역 일대",        "gu": "은평구",   "lat": 37.6106, "lng": 126.9294},
    "POI006": {"name": "신촌·이대",          "gu": "서대문구", "lat": 37.5559, "lng": 126.9364},
    "POI036": {"name": "홍제역 일대",        "gu": "서대문구", "lat": 37.5880, "lng": 126.9342},
    "POI004": {"name": "홍대입구역 2번출구", "gu": "마포구",   "lat": 37.5573, "lng": 126.9245},
    "POI037": {"name": "합정·망원",          "gu": "마포구",   "lat": 37.5496, "lng": 126.9103},
    "POI038": {"name": "상암DMC",            "gu": "마포구",   "lat": 37.5793, "lng": 126.8892},
    "POI039": {"name": "목동 일대",          "gu": "양천구",   "lat": 37.5267, "lng": 126.8747},
    "POI040": {"name": "발산역 일대",        "gu": "강서구",   "lat": 37.5583, "lng": 126.8375},
    "POI041": {"name": "김포공항역 일대",    "gu": "강서구",   "lat": 37.5624, "lng": 126.8012},
    "POI042": {"name": "구로디지털단지역",   "gu": "구로구",   "lat": 37.4851, "lng": 126.9011},
    "POI043": {"name": "신도림역 일대",      "gu": "구로구",   "lat": 37.5087, "lng": 126.8912},
    "POI044": {"name": "가산디지털단지역",   "gu": "금천구",   "lat": 37.4810, "lng": 126.8822},
    "POI010": {"name": "여의도",             "gu": "영등포구", "lat": 37.5215, "lng": 126.9246},
    "POI045": {"name": "영등포역 일대",      "gu": "영등포구", "lat": 37.5157, "lng": 126.9072},
    "POI046": {"name": "타임스퀘어 일대",    "gu": "영등포구", "lat": 37.5177, "lng": 126.9043},
    "POI016": {"name": "노량진",             "gu": "동작구",   "lat": 37.5138, "lng": 126.9428},
    "POI047": {"name": "사당역 일대",        "gu": "동작구",   "lat": 37.4766, "lng": 126.9815},
    "POI017": {"name": "신림역",             "gu": "관악구",   "lat": 37.4843, "lng": 126.9296},
    "POI048": {"name": "서울대입구역",       "gu": "관악구",   "lat": 37.4812, "lng": 126.9527},
    "POI049": {"name": "강남터미널 일대",    "gu": "서초구",   "lat": 37.5050, "lng": 127.0047},
    "POI050": {"name": "교대역 일대",        "gu": "서초구",   "lat": 37.4934, "lng": 127.0143},
    "POI051": {"name": "양재역 일대",        "gu": "서초구",   "lat": 37.4843, "lng": 127.0341},
    "POI005": {"name": "강남역 2번출구",     "gu": "강남구",   "lat": 37.4981, "lng": 127.0276},
    "POI052": {"name": "선릉·삼성역",        "gu": "강남구",   "lat": 37.5045, "lng": 127.0490},
    "POI053": {"name": "압구정 로데오",      "gu": "강남구",   "lat": 37.5272, "lng": 127.0392},
    "POI054": {"name": "청담동",             "gu": "강남구",   "lat": 37.5238, "lng": 127.0502},
    "POI055": {"name": "코엑스 일대",        "gu": "강남구",   "lat": 37.5131, "lng": 127.0596},
    "POI008": {"name": "잠실 롯데월드",      "gu": "송파구",   "lat": 37.5109, "lng": 127.0985},
    "POI056": {"name": "가락시장역 일대",    "gu": "송파구",   "lat": 37.4924, "lng": 127.1177},
    "POI057": {"name": "문정역 일대",        "gu": "송파구",   "lat": 37.4879, "lng": 127.1231},
    "POI058": {"name": "천호역 일대",        "gu": "강동구",   "lat": 37.5387, "lng": 127.1237},
    "POI059": {"name": "강동구청역 일대",    "gu": "강동구",   "lat": 37.5303, "lng": 127.1240},
}

# 구별 그룹 인덱스
SEOUL_GU_GROUPS: dict = {}
for _code, _p in SEOUL_PLACES.items():
    SEOUL_GU_GROUPS.setdefault(_p["gu"], []).append(_code)

SEOUL_GU_LIST = [
    "강남구","서초구","송파구","강동구","마포구","용산구","종로구","중구",
    "성동구","광진구","동대문구","중랑구","성북구","강북구","도봉구","노원구",
    "은평구","서대문구","양천구","강서구","구로구","금천구","영등포구","동작구","관악구",
]

EXCLUDE_USES = {"창고", "공장", "발전시설", "묘지", "자동차", "주차장", "위험물", "쓰레기"}


# ════════════════════════════════════════════════════════════════════
# 공통 유틸
# ════════════════════════════════════════════════════════════════════

def parse_xml(xml_text: str, tag_map: dict) -> list:
    """XML 파싱 공통 함수"""
    try:
        root = ET.fromstring(xml_text)
        result = []
        for item in root.findall(".//item"):
            row = {}
            for key, tag in tag_map.items():
                el = item.find(tag)
                row[key] = el.text.strip() if el is not None and el.text else ""
            result.append(row)
        return result
    except Exception as e:
        print(f"[parse_xml] 오류: {e}")
        return []


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 거리 반환 (미터)"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_recent_months(n: int) -> list[str]:
    """최근 n개월 YYYYMM 목록 (최신순)"""
    now = datetime.now()
    return [
        (now.replace(day=1) - timedelta(days=i * 30)).strftime("%Y%m")
        for i in range(n)
    ]


# ════════════════════════════════════════════════════════════════════
# 1. 실거래가 (국토교통부)
# ════════════════════════════════════════════════════════════════════

async def fetchCommercialTrade(sigungu: str, yearmonth: str) -> dict:
    """상업업무용 부동산 매매 실거래가"""
    lawd_cd = SIGUNGU_CODE_MAP.get(sigungu)
    if not lawd_cd:
        return {"error": f"지원하지 않는 시군구: {sigungu}", "data": []}

    url = "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
    params = {
        "serviceKey": MOLIT_NRG_KEY, "LAWD_CD": lawd_cd,
        "DEAL_YMD": yearmonth, "numOfRows": 100, "pageNo": 1,
    }
    tag_map = {
        "거래금액": "dealAmount", "건물명": "bldNm", "건물주용도": "buildingUse",
        "건축년도": "buildYear",  "전용면적": "excluUseAr", "년": "dealYear",
        "월": "dealMonth",       "일": "dealDay",           "법정동": "umdNm",
        "시군구": "sggNm",       "연면적": "totalFloorAr",  "용도지역": "landUse",
        "지번": "jibun",         "지역코드": "regionalCd",  "층": "floor",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, params=params)
        items = parse_xml(res.text, tag_map)
        return {"sigungu": sigungu, "yearmonth": yearmonth, "count": len(items), "data": items}
    except Exception as e:
        return {"error": str(e), "data": []}


async def fetchOfficetelRent(sigungu: str, yearmonth: str) -> dict:
    """오피스텔 전월세 실거래가"""
    lawd_cd = SIGUNGU_CODE_MAP.get(sigungu)
    if not lawd_cd:
        return {"error": f"지원하지 않는 시군구: {sigungu}", "data": []}

    url = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
    params = {
        "serviceKey": MOLIT_OP_KEY, "LAWD_CD": lawd_cd,
        "DEAL_YMD": yearmonth, "numOfRows": 100, "pageNo": 1,
    }
    tag_map = {
        "보증금": "deposit", "월세": "monthlyRent", "건물명": "buildingName",
        "년": "dealYear",    "월": "dealMonth",     "법정동": "umdNm",
        "전용면적": "excluUseAr", "층": "floor",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, params=params)
        items = parse_xml(res.text, tag_map)
        return {"sigungu": sigungu, "yearmonth": yearmonth, "count": len(items), "data": items}
    except Exception as e:
        return {"error": str(e), "data": []}


async def fetchTradeAvg(sigungu: str, months: list) -> dict:
    """시군구 기준 최근 N개월 상업용 실거래가 평균"""
    prices = []
    for ym in months:
        r = await fetchCommercialTrade(sigungu=sigungu, yearmonth=ym)
        for item in r.get("data", []):
            try:
                prices.append(int(item["거래금액"].replace(",", "").strip()))
            except Exception:
                pass
    if not prices:
        return {"avg": None, "count": 0}
    return {"avg": int(sum(prices) / len(prices)), "count": len(prices)}


async def fetchAnalysis(
    sigungu: str,
    dong: Optional[str] = None,
    jibun: Optional[str] = None,
) -> dict:
    """
    통합 실거래가 분석
    - 동 단위 우선, 0건이면 시군구 fallback
    - 상업용 매매 + 오피스텔 전월세
    """
    months = get_recent_months(12)

    commercial_data, officetel_data = [], []
    for ym in months:
        r = await fetchCommercialTrade(sigungu=sigungu, yearmonth=ym)
        commercial_data.extend(r.get("data", []))
        o = await fetchOfficetelRent(sigungu=sigungu, yearmonth=ym)
        officetel_data.extend(o.get("data", []))

    # 용도 필터
    def is_valid(item):
        use = (item.get("건물주용도") or item.get("건물용도") or "").strip()
        return not use or not any(ex in use for ex in EXCLUDE_USES)

    commercial_data = [x for x in commercial_data if is_valid(x)]
    uses = list({x.get("건물주용도", "").strip() for x in commercial_data if x.get("건물주용도", "").strip()})
    print(f"[실거래 용도목록] {uses[:20]}")

    # 동 단위 필터
    used_scope   = sigungu
    is_fallback  = False
    jibun_matched = False

    if dong:
        dong_s = dong.strip()
        comm_f = [x for x in commercial_data if dong_s in x.get("법정동", "").strip()]
        offi_f = [x for x in officetel_data  if dong_s in x.get("법정동", "").strip()]
        if comm_f or offi_f:
            commercial_data, officetel_data = comm_f, offi_f
            used_scope = f"{sigungu} {dong}"
        else:
            is_fallback = True
            used_scope  = f"{sigungu} (동 데이터 없음→전체)"

    # 지번 매칭
    if jibun and not is_fallback:
        parts  = jibun.replace(" ", "").split("-")
        bonbun = parts[0] if parts else ""
        bld_f  = [
            x for x in commercial_data
            if x.get("건물명", "").strip()
            and str(x.get("지번", "")).strip().split("-")[0] == bonbun
        ]
        if bld_f:
            commercial_data = bld_f
            used_scope      = f"{sigungu} {dong} {jibun}번지"
            jibun_matched   = True
        else:
            bld_only = [x for x in commercial_data if x.get("건물명", "").strip()]
            if bld_only:
                commercial_data = bld_only
                used_scope      = f"{sigungu} {dong} (건물명 있는 건)"
                jibun_matched   = True

    def calc_stats(data, price_key="거래금액"):
        prices = []
        for item in data:
            try:
                prices.append(int(item[price_key].replace(",", "").strip()))
            except Exception:
                pass
        if not prices:
            return {"건수": 0, "평균가": None, "최저가": None, "최고가": None, "목록": []}
        sorted_data = sorted(
            data,
            key=lambda x: (x.get("년", ""), x.get("월", ""), x.get("일", "")),
            reverse=True,
        )
        return {
            "건수": len(data),
            "평균가": f"{int(sum(prices)/len(prices)):,}만원",
            "최저가": f"{min(prices):,}만원",
            "최고가": f"{max(prices):,}만원",
            "목록": sorted_data[:20],
            "is_fallback": is_fallback,
            "jibun_matched": jibun_matched,
        }

    deposits = []
    for item in officetel_data:
        try:
            deposits.append(int(item.get("보증금", "0").replace(",", "").strip()))
        except Exception:
            pass
    avg_dep = f"{int(sum(deposits)/len(deposits)):,}만원" if deposits else None

    all_years  = [x.get("년", "") for x in commercial_data + officetel_data if x.get("년")]
    all_months = [x.get("월", "") for x in commercial_data + officetel_data if x.get("월")]
    if all_years:
        period = (
            f"{min(all_years)}{str(min(int(m) for m in all_months if m)).zfill(2)}"
            f"~{max(all_years)}{str(max(int(m) for m in all_months if m)).zfill(2)}"
        )
    else:
        period = f"{months[-1]}~{months[0]}"

    return {
        "sigungu":  used_scope,
        "조회범위": used_scope,
        "분석기간": period,
        "상업용":   calc_stats(commercial_data, "거래금액"),
        "오피스텔": {"건수": len(officetel_data), "평균보증금": avg_dep, "목록": officetel_data[:10]},
    }


async def fetchPriceOverlay(level: str, sigungu: Optional[str], months_back: int) -> dict:
    """줌레벨별 구/동 평균 실거래가 오버레이"""
    months = get_recent_months(months_back)

    if level == "sigungu":
        tasks       = [fetchTradeAvg(gu, months) for gu in SEOUL_GU_LIST]
        results_raw = await asyncio.gather(*tasks, return_exceptions=True)
        result = []
        for gu, r in zip(SEOUL_GU_LIST, results_raw):
            if isinstance(r, Exception) or r.get("avg") is None:
                continue
            avg = r["avg"]
            result.append({
                "label":   gu,
                "avg":     avg,
                "avg_str": f"매 {avg//10000:.1f}억" if avg >= 10000 else f"매 {avg:,}만",
                "count":   r["count"],
            })
        return {"level": level, "period": f"{months[-1]}~{months[0]}", "data": result}

    elif level == "dong" and sigungu:
        all_items = []
        for ym in months:
            r = await fetchCommercialTrade(sigungu=sigungu, yearmonth=ym)
            all_items.extend(r.get("data", []))

        dong_prices: dict = {}
        for item in all_items:
            d = item.get("법정동", "")
            if not d:
                continue
            try:
                dong_prices.setdefault(d, []).append(
                    int(item["거래금액"].replace(",", "").strip())
                )
            except Exception:
                pass

        result = []
        for d, prices in dong_prices.items():
            avg = int(sum(prices) / len(prices))
            result.append({
                "label":   f"{sigungu} {d}",
                "dong":    d,
                "sigungu": sigungu,
                "avg":     avg,
                "avg_str": f"매 {avg//10000:.1f}억" if avg >= 10000 else f"매 {avg:,}만",
                "count":   len(prices),
            })
        result.sort(key=lambda x: -x["avg"])
        return {"level": level, "sigungu": sigungu, "period": f"{months[-1]}~{months[0]}", "data": result}

    return {"error": "level은 sigungu 또는 dong(+sigungu 필수)", "data": []}


# ════════════════════════════════════════════════════════════════════
# 2. 서울 실시간 유동인구
# ════════════════════════════════════════════════════════════════════

def getNearbyPlaces(lat: float, lng: float, radius_km: float = 1.0) -> list:
    """반경 내 서울 주요 장소 목록"""
    result = []
    for code, place in SEOUL_PLACES.items():
        dist = haversine_m(lat, lng, place["lat"], place["lng"]) / 1000
        if dist <= radius_km:
            result.append({**place, "code": code, "distance_m": int(dist * 1000)})
    return sorted(result, key=lambda x: x["distance_m"])


async def fetchPopulation(place_code: str) -> dict:
    """서울 실시간 유동인구 단일 장소"""
    place = SEOUL_PLACES.get(place_code)
    if not place:
        return {"error": "장소코드 없음"}

    if not SEOUL_POP_KEY:
        return {"status": "no_key", "message": "API키 미설정", "place": place}

    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_POP_KEY}/json/citydata_ppltn/1/5/{place_code}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url)
        ppltn = res.json().get("SeoulRtd.citydata_ppltn", [{}])[0]
        return {
            "place_code": place_code,
            "place_name": place["name"],
            "혼잡도":   ppltn.get("AREA_CONGEST_LVL", ""),
            "인구_최소": ppltn.get("AREA_PPLTN_MIN", ""),
            "인구_최대": ppltn.get("AREA_PPLTN_MAX", ""),
            "업데이트": ppltn.get("PPLTN_TIME", ""),
        }
    except Exception as e:
        return {"error": str(e)}


async def fetchPopulationByGu(gu: str) -> dict:
    """구 내 모든 주요 장소 유동인구"""
    codes = SEOUL_GU_GROUPS.get(gu, [])
    if not codes:
        return {"error": f"'{gu}'에 해당하는 장소 없음", "data": []}

    results = []
    for code in codes:
        pop = await fetchPopulation(place_code=code)
        p   = SEOUL_PLACES[code]
        results.append({
            "code": code, "name": p["name"], "gu": p["gu"],
            "lat": p["lat"], "lng": p["lng"],
            **{k: v for k, v in pop.items() if k not in ("place_code", "place_name")},
        })
    return {"gu": gu, "count": len(results), "data": results}


async def fetchNearbyPopulation(lat: float, lng: float, radius_km: float) -> dict:
    """반경 내 주요 장소 유동인구"""
    places = getNearbyPlaces(lat, lng, radius_km)
    if not places:
        return {"count": 0, "data": [], "message": "반경 내 주요 장소 없음"}

    results = []
    for p in places[:5]:
        pop = await fetchPopulation(place_code=p["code"])
        results.append({**p, **pop})
    return {"count": len(results), "data": results}


# ════════════════════════════════════════════════════════════════════
# 3. 한국관광공사 관광정보
# ════════════════════════════════════════════════════════════════════

async def fetchTourNearby(
    mapX: float, mapY: float,
    radius: int = 1000,
    contentTypeId: Optional[str] = None,
) -> dict:
    """관광정보 API (KorService2 locationBasedList2)"""
    url = (
        "https://apis.data.go.kr/B551011/KorService2/locationBasedList2"
        f"?serviceKey={TOUR_KOR_KEY}"
        f"&mapX={mapX}&mapY={mapY}&radius={radius}"
        "&arrange=E&MobileOS=ETC&MobileApp=VWorldMap&_type=json"
        "&numOfRows=30&pageNo=1"
    )
    if contentTypeId:
        url += f"&contentTypeId={contentTypeId}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url)

        raw = res.text
        print(f"[tour-nearby] status={res.status_code} preview={raw[:200]}")

        if not raw.strip() or raw.strip().startswith("<"):
            return {"error": f"API XML/빈응답: {raw[:300]}", "count": 0, "data": []}

        data        = res.json()
        result_code = data.get("response", {}).get("header", {}).get("resultCode", "")
        result_msg  = data.get("response", {}).get("header", {}).get("resultMsg", "")
        if result_code not in ("0000", "00"):
            return {"error": f"API 오류 [{result_code}] {result_msg}", "count": 0, "data": []}

        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]

        result = [
            {
                "contentId":     item.get("contentid", ""),
                "contentTypeId": item.get("contenttypeid", ""),
                "title":         item.get("title", ""),
                "addr":          item.get("addr1", "") + item.get("addr2", ""),
                "tel":           item.get("tel", ""),
                "firstImage":    item.get("firstimage", "") or item.get("firstimage2", ""),
                "mapX":          item.get("mapx", ""),
                "mapY":          item.get("mapy", ""),
                "dist":          item.get("dist", ""),
                "cat1":          item.get("cat1", ""),
                "cat2":          item.get("cat2", ""),
                "cat3":          item.get("cat3", ""),
            }
            for item in (items or [])
        ]
        return {"count": len(result), "data": result}
    except Exception as e:
        return {"error": str(e), "count": 0, "data": []}


async def fetchTourFromDB(
    mapX: float, mapY: float,
    radius: int = 1000,
    contentTypeId: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """TOUR_SEOUL Oracle DB에서 좌표 기반 반경 조회"""
    try:
        from fable.oracleDBConnect import OracleDBConnect

        lat_delta = radius / 111320
        lng_delta = radius / (111320 * math.cos(math.radians(mapY)))

        sql = """
            SELECT CONTENT_ID, CONTENT_TYPE_ID, TITLE, ADDR1, TEL,
                   FIRST_IMAGE, FIRST_IMAGE2, MAP_X, MAP_Y, GU_NAME,
                   CAT1, CAT2, CAT3
            FROM TOUR_SEOUL
            WHERE MAP_Y BETWEEN :lat_min AND :lat_max
              AND MAP_X BETWEEN :lng_min AND :lng_max
        """
        params = {
            "lat_min": mapY - lat_delta, "lat_max": mapY + lat_delta,
            "lng_min": mapX - lng_delta, "lng_max": mapX + lng_delta,
        }
        if contentTypeId:
            sql += " AND CONTENT_TYPE_ID = :ctype"
            params["ctype"] = contentTypeId

        con, cur = OracleDBConnect.makeConCur()
        try:
            cur.execute(sql, params)
            cols = [d[0].lower() for d in cur.description]
            rows = cur.fetchall()
        finally:
            OracleDBConnect.closeConCur(con, cur)

        result = []
        for row in rows:
            item = dict(zip(cols, row))
            mx, my = item.get("map_x") or 0, item.get("map_y") or 0
            dist   = haversine_m(mapY, mapX, float(my), float(mx))
            if dist <= radius:
                item["dist"]          = round(dist)
                item["map_x"]         = str(mx)
                item["map_y"]         = str(my)
                item["contentId"]     = item.pop("content_id", "")
                item["contentTypeId"] = item.pop("content_type_id", "")
                item["firstImage"]    = item.pop("first_image", "") or item.pop("first_image2", "") or ""
                item["addr"]          = item.pop("addr1", "")
                result.append(item)

        result.sort(key=lambda x: x["dist"])
        return {"count": len(result), "data": result[:limit], "source": "db"}

    except Exception as e:
        print(f"[tour-db] DB 오류 → API fallback: {e}")
        return {"error": str(e), "count": 0, "data": [], "source": "error"}


async def fetchTourPhotos(keyword: str, numOfRows: int = 5) -> dict:
    """관광지 사진 검색 (PhotoGalleryService1)"""
    params = {
        "serviceKey": TOUR_PHOTO_KEY, "keyword": keyword,
        "MobileOS": "ETC", "MobileApp": "VWorldMap",
        "_type": "json", "numOfRows": numOfRows, "pageNo": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                "https://apis.data.go.kr/B551011/PhotoGalleryService1/gallerySearchList1",
                params=params,
            )
        items = (
            res.json()
               .get("response", {})
               .get("body", {})
               .get("items", {})
               .get("item", [])
        )
        if isinstance(items, dict):
            items = [items]
        result = [
            {
                "galContentId":           item.get("galContentId", ""),
                "galTitle":               item.get("galTitle", ""),
                "galWebImageUrl":         item.get("galWebImageUrl", ""),
                "galPhotographyMonth":    item.get("galPhotographyMonth", ""),
                "galPhotographyLocation": item.get("galPhotographyLocation", ""),
                "galPhotographer":        item.get("galPhotographer", ""),
            }
            for item in items
            if item.get("galWebImageUrl")
        ]
        return {"count": len(result), "keyword": keyword, "data": result}
    except Exception as e:
        return {"error": str(e), "count": 0, "data": []}



# ════════════════════════════════════════════════════════════════════
# 5. 개별공시지가 (VWorld LP_PA_CBND_BUBUN)
# ════════════════════════════════════════════════════════════════════

async def fetchLandValue(pnu: str, years: int = 5) -> dict:
    """PNU 기반 최근 N년 공시지가 이력"""
    current_year = datetime.now().year
    results = []

    async with httpx.AsyncClient(timeout=15) as client:
        for i in range(years):
            year = str(current_year - i)
            try:
                url = (
                    f"https://api.vworld.kr/req/data"
                    f"?service=data&version=2.0&request=GetFeature"
                    f"&format=json&errorFormat=json&data=LP_PA_CBND_BUBUN"
                    f"&key={VWORLD_KEY}&attrFilter=pnu:=:{pnu}"
                    f"&columns=pnu,pblntfPclnd,stdrYear&size=1&page=1"
                )
                res = await client.get(url)
                raw = res.text.strip()
                if not raw or raw.startswith("<"):
                    continue
                d      = res.json()
                status = d.get("response", {}).get("status", "")
                if status != "OK":
                    print(f"[공시지가] {year} status={status}")
                    continue
                features = (
                    d.get("response", {})
                     .get("result", {})
                     .get("featureCollection", {})
                     .get("features", [])
                )
                for feat in (features or []):
                    props = feat.get("properties", {})
                    price = props.get("pblntfPclnd")
                    stdr  = props.get("stdrYear", year)
                    if price and str(price).strip() not in ("", "0", "null"):
                        results.append({
                            "year":      str(stdr),
                            "price":     int(str(price).replace(",", "")),
                            "price_str": f"{int(str(price).replace(',','')):,}원/㎡",
                        })
                        break
            except Exception as e:
                print(f"[공시지가] {year} error={e}")

    results.sort(key=lambda x: x["year"], reverse=True)
    return {"pnu": pnu, "count": len(results), "data": results, "unit": "원/㎡"}

# ════════════════════════════════════════════════════════════════════
# RealEstateDAO 클래스 (Controller에서 import)
# ════════════════════════════════════════════════════════════════════

class RealEstateDAO:
    """실거래가 · 관광 · 상권 · 공시지가 기능을 묶은 DAO 클래스"""

    async def fetchCommercialTrade(self, sigungu: str, yearmonth: str) -> dict:
        return await fetchCommercialTrade(sigungu, yearmonth)

    async def fetchOfficetelRent(self, sigungu: str, yearmonth: str) -> dict:
        return await fetchOfficetelRent(sigungu, yearmonth)

    async def fetchAnalysis(
        self,
        sigungu: str,
        dong: Optional[str] = None,
        jibun: Optional[str] = None,
    ) -> dict:
        return await fetchAnalysis(sigungu, dong, jibun)

    async def fetchPriceOverlay(
        self,
        level: str,
        sigungu: Optional[str],
        months_back: int,
    ) -> dict:
        return await fetchPriceOverlay(level, sigungu, months_back)

    def getNearbyPlaces(self, lat: float, lng: float, radius_km: float = 1.0) -> list:
        return getNearbyPlaces(lat, lng, radius_km)

    async def fetchTourNearby(
        self,
        mapX: float,
        mapY: float,
        radius: int = 1000,
        contentTypeId: Optional[str] = None,
    ) -> dict:
        return await fetchTourNearby(mapX, mapY, radius, contentTypeId)

    async def fetchTourFromDB(
        self,
        mapX: float,
        mapY: float,
        radius: int = 1000,
        contentTypeId: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        return await fetchTourFromDB(mapX, mapY, radius, contentTypeId, limit)

    async def fetchTourPhotos(self, keyword: str, numOfRows: int = 5) -> dict:
        return await fetchTourPhotos(keyword, numOfRows)

    async def fetchLandValue(self, pnu: str, years: int = 5) -> dict:
        return await fetchLandValue(pnu, years)