# =====================================================
# 국토부 실거래가 수집 → Oracle INSERT (서울 한정)
# 위치: p04_DataLoader/collector/collect_molit_rtms.py
#
# 사용법:
#   python collect_molit_rtms.py                        ← 서울 전체 최근 2년
#   python collect_molit_rtms.py --year=2024            ← 2024년 전체
#   python collect_molit_rtms.py --year=2024 --month=6  ← 2024년 6월만
#   python collect_molit_rtms.py --type=officetel       ← 오피스텔만
#   python collect_molit_rtms.py --type=commercial      ← 상업용만
# =====================================================

import os
import sys
import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
import oracledb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────────────
DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"
MOLIT_OP_KEY = os.getenv(
    "MOLIT_OP_API_KEY",
    "b7906dd729da8d6d4f67bd6bed484f032f9f586abc7b382b41b93a003949385e",
)
MOLIT_NRG_KEY = os.getenv(
    "MOLIT_NRG_API_KEY",
    "b7906dd729da8d6d4f67bd6bed484f032f9f586abc7b382b41b93a003949385e",
)
MOLIT_OP_URL = (
    "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
)
MOLIT_NRG_URL = (
    "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
)

# 서울 25개 구 시군구코드
SEOUL_SGG_CDS = [
    "11110",
    "11140",
    "11170",
    "11200",
    "11215",
    "11230",
    "11260",
    "11290",
    "11305",
    "11320",
    "11350",
    "11380",
    "11410",
    "11440",
    "11470",
    "11500",
    "11530",
    "11545",
    "11560",
    "11590",
    "11620",
    "11650",
    "11680",
    "11710",
    "11740",
]

# 단순 INSERT + ORA-00001(PK중복) 무시 방식
SQL_OFFICETEL = """
    INSERT INTO RTMS_OFFICETEL (
        DEAL_YMD,SGG_CD,UMD_NM,OFFI_NM,JIBUN,FLOOR,EXCLU_USE_AR,DEAL_DAY,
        DEPOSIT,MONTHLY_RENT,PRE_DEPOSIT,PRE_MONTHLY_RENT,
        CONTRACT_TERM,CONTRACT_TYPE,USE_RR_RIGHT,BUILD_YEAR,SGG_NM
    ) VALUES (
        :1,:2,:3,:4,:5,:6,:7,:8,
        :9,:10,:11,:12,:13,:14,:15,:16,:17
    )
"""

SQL_COMMERCIAL = """
    INSERT INTO RTMS_COMMERCIAL (
        DEAL_YMD,SGG_CD,UMD_NM,JIBUN,FLOOR,DEAL_DAY,
        DEAL_AMOUNT,DEALING_GBN,CDEAL_TYPE,CDEAL_DAY,
        BUILD_YEAR,BUILDING_AR,BUILDING_TYPE,BUILDING_USE,
        LAND_USE,PLOTGAGE_AR,BUYER_GBN,SLER_GBN,
        SHARE_DEALING_TYPE,ESTATE_AGENT_SGG_NM,SGG_NM
    ) VALUES (
        :1,:2,:3,:4,:5,:6,
        :7,:8,:9,:10,:11,:12,:13,:14,:15,:16,:17,:18,:19,:20,:21
    )
"""


def g(item, tag):
    return (item.findtext(tag) or "").strip()


def to_int(val):
    try:
        return int(str(val).replace(",", "").strip())
    except:
        return None


def to_float(val):
    try:
        return float(str(val).strip())
    except:
        return None


async def fetch_api(client, url, api_key, sgg_cd, deal_ymd):
    """단일 API 호출"""
    try:
        r = await client.get(
            url,
            params={
                "serviceKey": api_key,
                "LAWD_CD": sgg_cd,
                "DEAL_YMD": deal_ymd,
                "pageNo": 1,
                "numOfRows": 1000,
            },
            timeout=20,
        )
        if r.status_code != 200:
            logger.warning(f"HTTP {r.status_code}: {sgg_cd} {deal_ymd}")
            return []
        text = r.text.strip()
        if not text.startswith("<"):
            return []
        root = ET.fromstring(text)
        err = root.findtext(".//resultCode") or ""
        if err not in ("000", "00", "0000", "INFO-000", ""):
            return []
        return root.findall(".//item")
    except Exception as e:
        logger.error(f"fetch_api 오류: {sgg_cd} {deal_ymd} / {e}")
        return []


def parse_officetel(items, sgg_cd, deal_ymd):
    rows = []
    for item in items:
        year = g(item, "dealYear")
        month = g(item, "dealMonth").zfill(2)
        rows.append(
            (
                deal_ymd,  # DEAL_YMD
                sgg_cd,  # SGG_CD
                g(item, "umdNm"),  # UMD_NM
                g(item, "offiNm"),  # OFFI_NM
                g(item, "jibun"),  # JIBUN
                g(item, "floor"),  # FLOOR
                to_float(g(item, "excluUseAr")),  # EXCLU_USE_AR
                g(item, "dealDay"),  # DEAL_DAY
                to_int(g(item, "deposit")),  # DEPOSIT
                to_int(g(item, "monthlyRent")),  # MONTHLY_RENT
                to_int(g(item, "preDeposit")),  # PRE_DEPOSIT
                to_int(g(item, "preMonthlyRent")),  # PRE_MONTHLY_RENT
                g(item, "contractTerm"),  # CONTRACT_TERM
                g(item, "contractType"),  # CONTRACT_TYPE
                g(item, "useRRRight"),  # USE_RR_RIGHT
                g(item, "buildYear"),  # BUILD_YEAR
                g(item, "sggNm"),  # SGG_NM
            )
        )
    return rows


def parse_commercial(items, sgg_cd, deal_ymd):
    rows = []
    for item in items:
        rows.append(
            (
                deal_ymd,  # DEAL_YMD
                sgg_cd,  # SGG_CD
                g(item, "umdNm"),  # UMD_NM
                g(item, "jibun"),  # JIBUN
                g(item, "floor"),  # FLOOR
                g(item, "dealDay"),  # DEAL_DAY
                to_int(g(item, "dealAmount")),  # DEAL_AMOUNT
                g(item, "dealingGbn"),  # DEALING_GBN
                g(item, "cdealType"),  # CDEAL_TYPE
                g(item, "cdealDay"),  # CDEAL_DAY
                g(item, "buildYear"),  # BUILD_YEAR
                to_float(g(item, "buildingAr")),  # BUILDING_AR
                g(item, "buildingType"),  # BUILDING_TYPE
                g(item, "buildingUse"),  # BUILDING_USE
                g(item, "landUse"),  # LAND_USE
                to_float(g(item, "plottageAr")),  # PLOTGAGE_AR
                g(item, "buyerGbn"),  # BUYER_GBN
                g(item, "slerGbn"),  # SLER_GBN
                g(item, "shareDealingType"),  # SHARE_DEALING_TYPE
                g(item, "estateAgentSggNm"),  # ESTATE_AGENT_SGG_NM
                g(item, "sggNm"),  # SGG_NM
            )
        )
    return rows


async def collect(ymds, types, con, cur):
    """서울 25개 구 × 월 × API 타입 수집"""
    total_op = total_nrg = 0

    async with httpx.AsyncClient() as client:
        for ymd in ymds:
            logger.info(f"▶ {ymd} 수집 중...")

            if "officetel" in types:
                tasks = [
                    fetch_api(client, MOLIT_OP_URL, MOLIT_OP_KEY, cd, ymd)
                    for cd in SEOUL_SGG_CDS
                ]
                results = await asyncio.gather(*tasks)
                rows = []
                for i, items in enumerate(results):
                    rows.extend(parse_officetel(items, SEOUL_SGG_CDS[i], ymd))
                if rows:
                    ok = skip = 0
                    try:
                        cur.executemany(SQL_OFFICETEL, rows)
                        con.commit()
                        ok = len(rows)
                    except Exception:
                        con.rollback()
                        for r in rows:
                            try:
                                cur.execute(SQL_OFFICETEL, r)
                                con.commit()
                                ok += 1
                            except:
                                con.rollback()
                                skip += 1
                    total_op += ok
                    logger.info(f"  오피스텔 {ymd}: {ok}건 INSERT / {skip}건 스킵")

            if "commercial" in types:
                tasks = [
                    fetch_api(client, MOLIT_NRG_URL, MOLIT_NRG_KEY, cd, ymd)
                    for cd in SEOUL_SGG_CDS
                ]
                results = await asyncio.gather(*tasks)
                rows = []
                for i, items in enumerate(results):
                    rows.extend(parse_commercial(items, SEOUL_SGG_CDS[i], ymd))
                if rows:
                    ok = skip = 0
                    try:
                        cur.executemany(SQL_COMMERCIAL, rows)
                        con.commit()
                        ok = len(rows)
                    except Exception:
                        con.rollback()
                        for r in rows:
                            try:
                                cur.execute(SQL_COMMERCIAL, r)
                                con.commit()
                                ok += 1
                            except:
                                con.rollback()
                                skip += 1
                    total_nrg += ok
                    logger.info(f"  상업용 {ymd}: {ok}건 INSERT / {skip}건 스킵")

    logger.info(f"{'='*40}")
    logger.info(f"완료: 오피스텔 {total_op:,}건 / 상업용 {total_nrg:,}건")


def make_ymds(year_flt=None, month_flt=None, years_back=4):
    """수집할 YYYYMM 목록 생성"""
    now = datetime.now()
    ymds = []

    if year_flt and month_flt:
        return [f"{year_flt}{int(month_flt):02d}"]
    elif year_flt:
        for m in range(1, 13):
            ymd = f"{year_flt}{m:02d}"
            if ymd <= now.strftime("%Y%m"):
                ymds.append(ymd)
        return ymds
    else:
        # 최근 years_back년
        for y in range(now.year - years_back + 1, now.year + 1):
            for m in range(1, 13):
                ymd = f"{y}{m:02d}"
                if ymd <= now.strftime("%Y%m"):
                    ymds.append(ymd)
        return ymds


def main():
    year_flt = None
    month_flt = None
    types = ["officetel", "commercial"]

    for a in sys.argv[1:]:
        if a.startswith("--year="):
            year_flt = a.split("=")[1]
        elif a.startswith("--month="):
            month_flt = a.split("=")[1]
        elif a.startswith("--type="):
            t = a.split("=")[1]
            types = [t] if t in ("officetel", "commercial") else types

    ymds = make_ymds(year_flt, month_flt)
    logger.info(
        f"수집 대상: {len(ymds)}개월 × {len(SEOUL_SGG_CDS)}구 × {len(types)}타입"
    )
    logger.info(f"YYYYMM 범위: {ymds[0]} ~ {ymds[-1]}")

    con = oracledb.connect(DB_INFO)
    cur = con.cursor()

    asyncio.run(collect(ymds, types, con, cur))

    cur.close()
    con.close()


if __name__ == "__main__":
    main()
